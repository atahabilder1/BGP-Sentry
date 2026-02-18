#!/usr/bin/env python3
"""
Real-time simulation monitoring dashboard.

Runs a Flask web server in a background daemon thread, exposing JSON API
endpoints and an auto-refreshing HTML dashboard so users can observe
per-node throughput, buffer usage, clock sync, and attack detection stats
while an experiment is running.
"""

import logging
import time
import threading
from collections import deque
from pathlib import Path

from flask import Flask, jsonify, render_template

logger = logging.getLogger(__name__)

# Keep enough history for a full 30-min run (1 sample/sec)
_TPS_HISTORY_LEN = 1800
# How often the background collector samples node stats (seconds)
_COLLECT_INTERVAL = 1.0


class SimulationDashboard:
    """Flask-based real-time monitoring dashboard for BGP-Sentry experiments.

    Parameters
    ----------
    node_manager : NodeManager
        The experiment's NodeManager instance (provides node stats).
    clock : SimulationClock
        The shared simulation clock.
    port : int
        HTTP port for the dashboard (default 5555).
    """

    def __init__(self, node_manager, clock, port=5555, system_info=None):
        self.node_manager = node_manager
        self.clock = clock
        self.port = port
        self.system_info = system_info or {}

        # TPS tracking: asn -> deque of (wall_time, processed_count)
        self._tps_snapshots: dict[int, deque] = {}
        # Global TPS history for the chart: deque of (wall_time, avg_tps)
        self._global_tps_history: deque = deque(maxlen=_TPS_HISTORY_LEN)
        # Lag history for the chart: deque of {t, lag}
        self._lag_history: deque = deque(maxlen=_TPS_HISTORY_LEN)
        # Comprehensive time-series for final report
        self._timeseries: list = []  # full log, not capped — written to results
        self._collector_running = False

        # Flask app
        template_dir = Path(__file__).resolve().parent / "templates"
        self._app = Flask(__name__, template_folder=str(template_dir))
        self._app.logger.setLevel(logging.WARNING)  # suppress request logs
        self._setup_routes()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self):
        """Start the dashboard and background collector in daemon threads."""
        # Start stat collector thread
        self._collector_running = True
        collector = threading.Thread(target=self._collect_loop, daemon=True,
                                     name="dashboard-collector")
        collector.start()

        # Start Flask server thread
        server = threading.Thread(target=self._run_server, daemon=True,
                                  name="dashboard-server")
        server.start()
        logger.info(f"Dashboard running at http://localhost:{self.port}")

    def stop(self):
        """Signal the collector to stop (server stops when process exits)."""
        self._collector_running = False

    def save_report(self, results_dir):
        """Save all collected monitoring data to the results directory."""
        import json
        results_dir = Path(results_dir)
        results_dir.mkdir(parents=True, exist_ok=True)

        data = {
            "timeseries": self._timeseries,
            "tps_history": list(self._global_tps_history),
            "lag_history": list(self._lag_history),
            "total_snapshots": len(self._timeseries),
            "collection_interval_sec": _COLLECT_INTERVAL,
        }
        path = results_dir / "monitoring_timeseries.json"
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Monitoring report saved: {path} ({len(self._timeseries)} snapshots)")

    # ------------------------------------------------------------------
    # Flask routes
    # ------------------------------------------------------------------

    def _setup_routes(self):
        app = self._app

        @app.route("/")
        def index():
            return render_template("dashboard.html")

        @app.route("/api/overview")
        def api_overview():
            return jsonify(self._build_overview())

        @app.route("/api/nodes")
        def api_nodes():
            return jsonify(self._build_nodes())

        @app.route("/api/nodes/<int:asn>")
        def api_node_detail(asn):
            node = self.node_manager.nodes.get(asn)
            if node is None:
                return jsonify({"error": "node not found"}), 404
            return jsonify(self._node_to_dict(node))

        @app.route("/api/clock")
        def api_clock():
            return jsonify(self._build_clock())

        @app.route("/api/blockchain")
        def api_blockchain():
            return jsonify(self._build_blockchain())

        @app.route("/api/buffer")
        def api_buffer():
            return jsonify(self._build_buffer())

        @app.route("/api/tps_history")
        def api_tps_history():
            return jsonify(list(self._global_tps_history))

        @app.route("/api/rpki_health")
        def api_rpki_health():
            return jsonify(self._build_rpki_health())

        @app.route("/api/lag_history")
        def api_lag_history():
            return jsonify(list(self._lag_history))

        @app.route("/api/timeseries")
        def api_timeseries():
            return jsonify(self._timeseries)

        @app.route("/api/system_info")
        def api_system_info():
            return jsonify(self.system_info)

    # ------------------------------------------------------------------
    # Data builders
    # ------------------------------------------------------------------

    def _build_overview(self) -> dict:
        summary = self.node_manager.get_summary()
        clock = self.clock

        wall_elapsed = time.time() - clock._anchor_wall_ts if clock._anchor_wall_ts else 0.0
        sim_elapsed = clock.sim_time()

        return {
            "total_nodes": summary["total_nodes"],
            "rpki_nodes": summary["rpki_nodes"],
            "non_rpki_nodes": summary["non_rpki_nodes"],
            "nodes_done": summary["nodes_done"],
            "total_processed": summary["total_observations_processed"],
            "attacks_detected": summary["attacks_detected"],
            "legitimate_processed": summary["legitimate_processed"],
            "sim_time": round(sim_elapsed, 1),
            "wall_time": round(wall_elapsed, 1),
            "speed_multiplier": clock.speed_multiplier,
        }

    def _build_nodes(self) -> list:
        nodes = []
        for node in sorted(self.node_manager.nodes.values(), key=lambda n: n.asn):
            nodes.append(self._node_to_dict(node))
        return nodes

    def _node_to_dict(self, node) -> dict:
        total = len(node.observations)
        processed = node.processed_count
        progress = (processed / total * 100) if total > 0 else 0.0
        buf = getattr(node, "_buffer", None)
        buf_queued = len(buf._queue) if buf is not None else 0
        buf_max = buf.max_size if buf is not None else 0
        return {
            "asn": node.asn,
            "is_rpki": node.is_rpki,
            "total_observations": total,
            "processed": processed,
            "progress_pct": round(progress, 1),
            "attacks_detected": len(node.attack_detections),
            "buffer_sampled": node.stats.get("buffer_sampled", 0),
            "buffer_queued": buf_queued,
            "buffer_max": buf_max,
            "last_bgp_timestamp": getattr(node, "_last_bgp_ts", None),
            "tps": self._compute_node_tps(node.asn),
            "running": node.running,
        }

    def _build_clock(self) -> dict:
        clock = self.clock
        nm = self.node_manager
        anchor_bgp = clock._anchor_bgp_ts or 0
        wall_elapsed = time.time() - clock._anchor_wall_ts if clock._anchor_wall_ts else 0.0
        sim_elapsed = clock.sim_time()
        current_bgp = anchor_bgp + sim_elapsed

        bgp_ts_min = getattr(nm, "bgp_ts_min", 0)
        bgp_ts_max = getattr(nm, "bgp_ts_max", 0)
        ts_range = bgp_ts_max - bgp_ts_min if bgp_ts_max > bgp_ts_min else 1

        # Per-node timestamp stats
        node_timestamps = []
        furthest_node_ts = 0
        for node in nm.nodes.values():
            nts = getattr(node, "_last_bgp_ts", 0) or 0
            if nts > 0:
                node_timestamps.append(nts)
            if nts > furthest_node_ts:
                furthest_node_ts = nts

        avg_node_ts = (sum(node_timestamps) / len(node_timestamps)) if node_timestamps else 0
        slowest_node_ts = min(node_timestamps) if node_timestamps else 0

        # Progress percentages
        clock_pct = min(100, max(0, (current_bgp - bgp_ts_min) / ts_range * 100))
        avg_pct = min(100, max(0, (avg_node_ts - bgp_ts_min) / ts_range * 100)) if avg_node_ts > 0 else 0
        furthest_pct = min(100, max(0, (furthest_node_ts - bgp_ts_min) / ts_range * 100)) if furthest_node_ts > 0 else 0
        slowest_pct = min(100, max(0, (slowest_node_ts - bgp_ts_min) / ts_range * 100)) if slowest_node_ts > 0 else 0

        # Lag: how far avg node is behind the clock (in seconds of BGP time)
        lag_seconds = round(current_bgp - avg_node_ts, 1) if avg_node_ts > 0 else 0

        return {
            "sim_time": round(sim_elapsed, 1),
            "wall_time": round(wall_elapsed, 1),
            "speed_multiplier": clock.speed_multiplier,
            "anchor_bgp_ts": anchor_bgp,
            "current_bgp_ts": round(current_bgp, 1),
            "bgp_ts_min": bgp_ts_min,
            "bgp_ts_max": bgp_ts_max,
            "furthest_node_ts": furthest_node_ts,
            "avg_node_ts": round(avg_node_ts, 1),
            "slowest_node_ts": slowest_node_ts,
            "clock_progress_pct": round(clock_pct, 1),
            "avg_progress_pct": round(avg_pct, 1),
            "furthest_progress_pct": round(furthest_pct, 1),
            "slowest_progress_pct": round(slowest_pct, 1),
            "lag_seconds": lag_seconds,
            "started": clock._started.is_set(),
        }

    def _build_blockchain(self) -> dict:
        bc = self.node_manager.primary_blockchain
        if bc is None:
            return {}
        info = bc.get_blockchain_info()
        return {
            "total_blocks": info.get("total_blocks", 0),
            "total_transactions": info.get("total_transactions", 0),
        }

    def _build_buffer(self) -> list:
        result = []
        for node in sorted(self.node_manager.nodes.values(), key=lambda n: n.asn):
            result.append({
                "asn": node.asn,
                "buffer_sampled": node.stats.get("buffer_sampled", 0),
            })
        return result

    def _build_rpki_health(self) -> list:
        """Per-RPKI-node health: lag from clock + buffer queue state."""
        clock = self.clock
        anchor_bgp = clock._anchor_bgp_ts or 0
        sim_elapsed = clock.sim_time()
        current_bgp = anchor_bgp + sim_elapsed

        result = []
        for node in sorted(self.node_manager.nodes.values(), key=lambda n: n.asn):
            if not node.is_rpki:
                continue
            node_ts = getattr(node, "_last_bgp_ts", 0) or 0
            lag = round(current_bgp - node_ts, 1) if node_ts > 0 else 0
            buf = getattr(node, "_buffer", None)
            buf_queued = len(buf._queue) if buf is not None else 0
            buf_max = buf.max_size if buf is not None else 0
            result.append({
                "asn": node.asn,
                "lag_seconds": lag,
                "buffer_queued": buf_queued,
                "buffer_max": buf_max,
                "buffer_pct": round(buf_queued / buf_max * 100, 1) if buf_max > 0 else 0,
                "tps": self._compute_node_tps(node.asn),
                "processed": node.processed_count,
                "total": len(node.observations),
                "running": node.running,
                "buffer_sampled": node.stats.get("buffer_sampled", 0),
                "txns_created": node.stats.get("transactions_created", 0),
            })
        return result

    # ------------------------------------------------------------------
    # TPS calculation
    # ------------------------------------------------------------------

    def _compute_node_tps(self, asn: int) -> float:
        """Compute TPS for a single node from its snapshot history."""
        snaps = self._tps_snapshots.get(asn)
        if not snaps or len(snaps) < 2:
            return 0.0
        oldest_time, oldest_count = snaps[0]
        newest_time, newest_count = snaps[-1]
        dt = newest_time - oldest_time
        if dt <= 0:
            return 0.0
        return round((newest_count - oldest_count) / dt, 2)

    # ------------------------------------------------------------------
    # Background collector
    # ------------------------------------------------------------------

    def _collect_loop(self):
        """Periodically sample processed counts for TPS calculation."""
        while self._collector_running:
            now = time.time()
            total_tps = 0.0
            node_count = 0
            for asn, node in self.node_manager.nodes.items():
                if asn not in self._tps_snapshots:
                    self._tps_snapshots[asn] = deque(maxlen=_TPS_HISTORY_LEN)
                self._tps_snapshots[asn].append((now, node.processed_count))
                tps = self._compute_node_tps(asn)
                total_tps += tps
                node_count += 1

            wall_t = round(now - (self.clock._anchor_wall_ts or now), 1)

            avg_tps = round(total_tps / max(node_count, 1), 2)
            self._global_tps_history.append({"t": wall_t, "tps": avg_tps})

            # Compute avg lag across all nodes for lag history
            clock = self.clock
            anchor_bgp = clock._anchor_bgp_ts or 0
            current_bgp = anchor_bgp + clock.sim_time()
            node_ts_list = []
            for node in self.node_manager.nodes.values():
                nts = getattr(node, "_last_bgp_ts", 0) or 0
                if nts > 0:
                    node_ts_list.append(nts)
            if node_ts_list:
                avg_node_ts = sum(node_ts_list) / len(node_ts_list)
                avg_lag = round(current_bgp - avg_node_ts, 1)
            else:
                avg_lag = 0
            self._lag_history.append({"t": wall_t, "lag": avg_lag})

            # Comprehensive snapshot for final report (every 5s to keep size down)
            if len(self._timeseries) == 0 or wall_t - self._timeseries[-1]["t"] >= 5:
                nm = self.node_manager
                total_processed = sum(n.processed_count for n in nm.nodes.values())
                total_attacks = sum(len(n.attack_detections) for n in nm.nodes.values())
                nodes_done = sum(1 for n in nm.nodes.values() if n.is_done())
                bc = nm.primary_blockchain
                bc_blocks = 0
                bc_txns = 0
                if bc is not None:
                    try:
                        info = bc.get_blockchain_info()
                        bc_blocks = info.get("total_blocks", 0)
                        bc_txns = info.get("total_transactions", 0)
                    except Exception:
                        pass
                self._timeseries.append({
                    "t": wall_t,
                    "avg_tps": avg_tps,
                    "avg_lag": avg_lag,
                    "total_processed": total_processed,
                    "total_attacks": total_attacks,
                    "nodes_done": nodes_done,
                    "blockchain_blocks": bc_blocks,
                    "blockchain_txns": bc_txns,
                    "clock_pct": round(min(100, max(0,
                        (current_bgp - (clock._anchor_bgp_ts or 0)) /
                        max(getattr(nm, 'bgp_ts_max', 1) - getattr(nm, 'bgp_ts_min', 0), 1) * 100
                    )), 1),
                })

            time.sleep(_COLLECT_INTERVAL)

    # ------------------------------------------------------------------
    # Flask server
    # ------------------------------------------------------------------

    def _run_server(self):
        """Run the Flask dev server (suitable for local monitoring)."""
        import werkzeug.serving
        # Suppress default Flask/Werkzeug startup banner
        import logging as _logging
        _logging.getLogger("werkzeug").setLevel(_logging.WARNING)

        self._app.run(
            host="0.0.0.0",
            port=self.port,
            debug=False,
            use_reloader=False,
        )
