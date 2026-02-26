#!/usr/bin/env python3
"""
Real-time simulation monitoring dashboard.

Runs a Flask web server in a background daemon thread, exposing JSON API
endpoints and an auto-refreshing HTML dashboard so users can observe
per-node throughput, buffer usage, clock sync, and attack detection stats
while an experiment is running.
"""

import json as _json
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
# Time-series history length for manuscript charts (sampled every 5s)
_TS_HISTORY_LEN = 360


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

        # ── NEW: Manuscript figure time-series ──
        self._trust_coverage_history: deque = deque(maxlen=_TS_HISTORY_LEN)
        self._consensus_breakdown_history: deque = deque(maxlen=_TS_HISTORY_LEN)
        self._data_flow_history: deque = deque(maxlen=_TS_HISTORY_LEN)
        self._attack_timeline_history: list = []  # attack events (unbounded, small)
        self._seen_attack_keys: set = set()  # dedup attack events

        # ── NEW: Cached expensive data ──
        self._cached_verification: dict = {}
        self._cached_verification_t: float = 0
        self._cached_detection_accuracy: dict = {}
        self._cached_detection_accuracy_t: float = 0

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
            "trust_coverage_history": list(self._trust_coverage_history),
            "consensus_breakdown_history": list(self._consensus_breakdown_history),
            "data_flow_history": list(self._data_flow_history),
            "attack_timeline": self._attack_timeline_history,
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

        # ── Existing endpoints ──
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

        # ── NEW: Manuscript figure/table endpoints ──

        @app.route("/api/trust_coverage")
        def api_trust_coverage():
            return jsonify(self._build_trust_coverage())

        @app.route("/api/consensus_breakdown")
        def api_consensus_breakdown():
            return jsonify(self._build_consensus_breakdown())

        @app.route("/api/data_flow")
        def api_data_flow():
            return jsonify(self._build_data_flow())

        @app.route("/api/detection_accuracy")
        def api_detection_accuracy():
            return jsonify(self._build_detection_accuracy())

        @app.route("/api/throughput_latency")
        def api_throughput_latency():
            return jsonify(self._build_throughput_latency())

        @app.route("/api/forensic_audit")
        def api_forensic_audit():
            return jsonify(self._build_forensic_audit())

        @app.route("/api/verification")
        def api_verification():
            return jsonify(self._build_verification())

        @app.route("/api/trust_distribution")
        def api_trust_distribution():
            return jsonify(self._build_trust_distribution())

        @app.route("/api/buffer_breakdown")
        def api_buffer_breakdown():
            return jsonify(self._build_buffer_breakdown())

        @app.route("/api/bgpcoin")
        def api_bgpcoin():
            return jsonify(self._build_bgpcoin())

        @app.route("/api/attack_timeline")
        def api_attack_timeline():
            return jsonify(self._attack_timeline_history)

        @app.route("/api/step_latency")
        def api_step_latency():
            return jsonify(self._build_step_latency())

        @app.route("/api/node_activity/<int:asn>")
        def api_node_activity(asn):
            return jsonify(self._build_node_activity(asn))

        @app.route("/api/blockchain_detail")
        def api_blockchain_detail():
            return jsonify(self._build_blockchain_detail())

        # ── Cross-dataset comparison ──

        @app.route("/compare")
        def compare_page():
            return render_template("compare.html")

        @app.route("/api/compare")
        def api_compare():
            return jsonify(self._build_cross_dataset_comparison())

    # ------------------------------------------------------------------
    # Data builders — existing
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
    # Data builders — NEW manuscript endpoints
    # ------------------------------------------------------------------

    def _build_trust_coverage(self) -> dict:
        """Fig 4a: Trust coverage convergence — % of non-RPKI ASes with ratings."""
        nm = self.node_manager
        rs = nm.rating_system
        if rs is None:
            return {"coverage_pct": 0, "rated_ases": 0, "total_nonrpki": 0,
                    "history": list(self._trust_coverage_history)}

        all_ratings = rs.get_all_ratings()
        rated = sum(1 for r in all_ratings.values()
                    if r.get("legitimate_announcements", 0) > 0 or r.get("attacks_detected", 0) > 0)
        non_rpki = sum(1 for n in nm.nodes.values() if not n.is_rpki)
        total_nonrpki = max(non_rpki, len(all_ratings), 1)
        coverage = round(rated / total_nonrpki * 100, 1)

        return {
            "coverage_pct": coverage,
            "rated_ases": rated,
            "total_nonrpki": total_nonrpki,
            "history": list(self._trust_coverage_history),
        }

    def _build_consensus_breakdown(self) -> dict:
        """Fig 4b: Consensus status — confirmed vs pending vs single-witness."""
        nm = self.node_manager
        consensus = nm.get_consensus_log()
        total_created = consensus.get("total_transactions_created", 0)
        committed = consensus.get("total_committed", 0)
        pending = consensus.get("total_pending", 0)
        single_witness = max(0, total_created - committed - pending)

        return {
            "confirmed": committed,
            "pending": pending,
            "single_witness": single_witness,
            "total_created": total_created,
            "history": list(self._consensus_breakdown_history),
        }

    def _build_data_flow(self) -> dict:
        """Fig 5a: Data flow pipeline — received vs committed + buffer depth."""
        nm = self.node_manager
        total_received = sum(n.processed_count for n in nm.nodes.values())
        bc = nm.primary_blockchain
        committed = 0
        if bc is not None:
            try:
                info = bc.get_blockchain_info()
                committed = info.get("total_transactions", 0)
            except Exception:
                pass

        # Total buffer depth across all RPKI nodes
        buffer_depth = 0
        for node in nm.nodes.values():
            if node.is_rpki:
                buf = getattr(node, "_buffer", None)
                if buf is not None:
                    buffer_depth += len(buf._queue)

        return {
            "received": total_received,
            "committed": committed,
            "buffer_depth": buffer_depth,
            "history": list(self._data_flow_history),
        }

    def _build_detection_accuracy(self) -> dict:
        """Table 3: Detection accuracy — precision, recall, F1."""
        now = time.time()
        if now - self._cached_detection_accuracy_t < 5 and self._cached_detection_accuracy:
            return self._cached_detection_accuracy

        nm = self.node_manager
        tp = fp = fn = tn = 0

        for node in nm.nodes.values():
            for r in node.detection_results:
                is_attack = r.get("is_attack", False)
                detected = r.get("detected", False)
                if is_attack and detected:
                    tp += 1
                elif not is_attack and detected:
                    fp += 1
                elif is_attack and not detected:
                    fn += 1
                else:
                    tn += 1

        precision = round(tp / max(tp + fp, 1) * 100, 2)
        recall = round(tp / max(tp + fn, 1) * 100, 2)
        f1 = round(2 * precision * recall / max(precision + recall, 0.01), 2)

        # Blockchain + P2P metrics
        consensus = nm.get_consensus_log()
        bc_info = self._build_blockchain()

        result = {
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "true_negatives": tn,
            "precision": precision,
            "recall": recall,
            "f1_score": f1,
            "blockchain_blocks": bc_info.get("total_blocks", 0),
            "blockchain_txns": bc_info.get("total_transactions", 0),
            "consensus_committed": consensus.get("total_committed", 0),
            "consensus_pending": consensus.get("total_pending", 0),
        }
        self._cached_detection_accuracy = result
        self._cached_detection_accuracy_t = now
        return result

    def _build_throughput_latency(self) -> dict:
        """Table 4: Throughput & latency metrics."""
        nm = self.node_manager
        clock = self.clock
        wall_elapsed = time.time() - clock._anchor_wall_ts if clock._anchor_wall_ts else 0.0
        total_processed = sum(n.processed_count for n in nm.nodes.values())

        # Per-node TPS
        node_tps_list = []
        for node in nm.nodes.values():
            if node.is_rpki:
                tps = self._compute_node_tps(node.asn)
                node_tps_list.append({"asn": node.asn, "tps": tps})

        avg_tps = round(sum(n["tps"] for n in node_tps_list) / max(len(node_tps_list), 1), 2)

        # Phase lag
        clock_data = self._build_clock()

        return {
            "wall_time_s": round(wall_elapsed, 1),
            "total_processed": total_processed,
            "avg_tps": avg_tps,
            "node_tps": node_tps_list,
            "lag_seconds": clock_data.get("lag_seconds", 0),
            "clock_progress_pct": clock_data.get("clock_progress_pct", 0),
            "speed_multiplier": clock.speed_multiplier,
        }

    def _build_forensic_audit(self) -> list:
        """Table 5: Forensic audit — attacker ASes with scores and types."""
        nm = self.node_manager
        # Collect attack detections from all nodes, group by attacker AS
        attacker_map = {}
        for node in nm.nodes.values():
            for det in node.attack_detections:
                origin = det.get("origin_asn", 0)
                if origin not in attacker_map:
                    attacker_map[origin] = {
                        "asn": origin,
                        "attack_count": 0,
                        "attack_types": set(),
                        "prefixes": set(),
                    }
                attacker_map[origin]["attack_count"] += 1
                atype = det.get("detection_type") or det.get("label", "UNKNOWN")
                attacker_map[origin]["attack_types"].add(atype)
                attacker_map[origin]["prefixes"].add(det.get("prefix", ""))

        # Get trust scores from rating system
        rs = nm.rating_system
        result = []
        for asn, info in sorted(attacker_map.items(), key=lambda x: -x[1]["attack_count"]):
            score = 50.0
            if rs is not None:
                try:
                    rating = rs.get_or_create_rating(asn)
                    score = rating.get("trust_score", 50.0)
                except Exception:
                    pass
            result.append({
                "asn": asn,
                "attack_count": info["attack_count"],
                "attack_types": sorted(info["attack_types"]),
                "prefixes_affected": len(info["prefixes"]),
                "trust_score": round(score, 1),
            })
        return result

    def _build_verification(self) -> dict:
        """Table 9: Verification — hash/Merkle/Ed25519 integrity checks."""
        now = time.time()
        if now - self._cached_verification_t < 10 and self._cached_verification:
            return self._cached_verification

        nm = self.node_manager
        bc = nm.primary_blockchain
        if bc is None:
            return {"chain_valid": False, "total_blocks": 0, "errors": ["No blockchain"]}

        try:
            integrity = bc.verify_blockchain_integrity()
        except Exception as e:
            integrity = {"valid": False, "total_blocks": 0, "errors": [str(e)]}

        # Replica verification
        replicas_valid = 0
        replicas_total = len(nm.node_blockchains)
        for chain in nm.node_blockchains.values():
            try:
                if chain.verify_blockchain_integrity().get("valid", False):
                    replicas_valid += 1
            except Exception:
                pass

        # Crypto summary
        crypto = nm.get_crypto_summary()

        result = {
            "chain_valid": integrity.get("valid", False),
            "total_blocks": integrity.get("total_blocks", 0),
            "errors": integrity.get("errors", []),
            "replicas_total": replicas_total,
            "replicas_valid": replicas_valid,
            "key_algorithm": crypto.get("key_algorithm", "Ed25519"),
            "total_key_pairs": crypto.get("total_key_pairs", 0),
        }
        self._cached_verification = result
        self._cached_verification_t = now
        return result

    def _build_trust_distribution(self) -> dict:
        """Trust score histogram — 10 buckets (0-10, 10-20, ..., 90-100)."""
        nm = self.node_manager
        rs = nm.rating_system
        buckets = [0] * 10  # 0-10, 10-20, ..., 90-100
        labels = [f"{i*10}-{i*10+10}" for i in range(10)]

        if rs is not None:
            for rating in rs.get_all_ratings().values():
                score = rating.get("trust_score", 50.0)
                idx = min(int(score / 10), 9)
                buckets[idx] += 1

        # Also include RPKI node trust scores
        for node in nm.nodes.values():
            if node.is_rpki:
                score = getattr(node, "trust_score", 100.0)
                idx = min(int(score / 10), 9)
                buckets[idx] += 1

        return {"labels": labels, "counts": buckets}

    def _build_buffer_breakdown(self) -> list:
        """Per-node buffer breakdown — 6 buffer types."""
        result = []
        for node in sorted(self.node_manager.nodes.values(), key=lambda n: n.asn):
            if not node.is_rpki:
                continue

            buf = getattr(node, "_buffer", None)
            ingestion = len(buf._queue) if buf is not None else 0

            pool = node.p2p_pool
            pending_votes = len(pool.pending_votes) if pool is not None else 0
            committed = len(pool.committed_transactions) if pool is not None else 0

            # Knowledge base size — count observations in the pool
            kb_size = 0
            if pool is not None:
                kb = getattr(pool, "knowledge_base", None)
                if kb is not None:
                    kb_size = len(kb) if hasattr(kb, '__len__') else 0

            last_seen = len(node.dedup_state)
            dedup_state = len(node.dedup_state)

            result.append({
                "asn": node.asn,
                "ingestion_buffer": ingestion,
                "pending_votes": pending_votes,
                "committed_txs": committed,
                "knowledge_base": kb_size,
                "last_seen_cache": last_seen,
                "dedup_state": dedup_state,
            })
        return result

    def _build_bgpcoin(self) -> dict:
        """BGPCoin economy — per-node balances + summary."""
        nm = self.node_manager
        ledger = nm.shared_ledger
        if ledger is None:
            return {"balances": [], "summary": {}}

        balances = []
        for node in sorted(nm.nodes.values(), key=lambda n: n.asn):
            if not node.is_rpki:
                continue
            bal = ledger.get_balance(node.asn)
            balances.append({"asn": node.asn, "balance": round(bal, 2)})

        summary = ledger.get_ledger_summary()
        return {"balances": balances, "summary": summary}

    def _build_step_latency(self) -> list:
        """Per-step timing averages per node — KEY for distributed claim."""
        result = []
        for node in sorted(self.node_manager.nodes.values(), key=lambda n: n.asn):
            if not node.is_rpki:
                continue

            timings = getattr(node, "step_timings", None)
            if timings is None:
                continue

            entry = {"asn": node.asn}
            total_obs = 0
            for step_name, step_deque in timings.items():
                vals = list(step_deque)
                if vals:
                    avg_ms = round(sum(vals) / len(vals) * 1000, 3)
                    if step_name == "total_pipeline":
                        total_obs = len(vals)
                else:
                    avg_ms = 0.0
                entry[f"{step_name}_ms"] = avg_ms

            entry["observations_timed"] = total_obs
            result.append(entry)
        return result

    # ------------------------------------------------------------------
    # Blockchain detail (transactions + vote counts)
    # ------------------------------------------------------------------

    def _build_blockchain_detail(self) -> dict:
        """Blockchain transactions written with vote signature counts."""
        nm = self.node_manager
        bc = nm.primary_blockchain
        bc_info = {}
        if bc is not None:
            try:
                bc_info = bc.get_blockchain_info()
            except Exception:
                pass

        # Aggregate vote statistics from all RPKI nodes' P2P pools
        vote_distribution = {}  # vote_count -> how many txns got that many votes
        total_committed = 0
        total_pending = 0
        total_created = 0
        total_single_witness = 0
        total_timed_out = 0

        # Sample recent pending transactions for vote count breakdown
        recent_txns = []

        for node in nm.nodes.values():
            if not node.is_rpki or node.p2p_pool is None:
                continue
            pool = node.p2p_pool

            total_committed += len(pool.committed_transactions)
            total_pending += len(pool.pending_votes)
            total_created += node.stats.get("transactions_created", 0)

            # Inspect pending_votes for vote counts
            try:
                for tx_id, vote_data in list(pool.pending_votes.items()):
                    votes = vote_data.get("votes", [])
                    n_votes = len(votes)
                    approve = sum(1 for v in votes if v.get("vote") == "approve")
                    reject = sum(1 for v in votes if v.get("vote") == "reject")
                    no_knowledge = sum(1 for v in votes if v.get("vote") == "no_knowledge")

                    bucket = str(n_votes)
                    vote_distribution[bucket] = vote_distribution.get(bucket, 0) + 1

                    tx = vote_data.get("transaction", {})
                    if len(recent_txns) < 20:
                        recent_txns.append({
                            "tx_id": tx_id[:30],
                            "observer_as": tx.get("observer_as", 0),
                            "prefix": tx.get("ip_prefix", ""),
                            "is_attack": tx.get("is_attack", False),
                            "total_votes": n_votes,
                            "approve": approve,
                            "reject": reject,
                            "no_knowledge": no_knowledge,
                            "needed": vote_data.get("needed", 0),
                            "status": "committed" if tx_id in pool.committed_transactions else "pending",
                        })
            except Exception:
                pass

        consensus_threshold = 3  # default PoP threshold
        for node in nm.nodes.values():
            if node.is_rpki and node.p2p_pool is not None:
                consensus_threshold = getattr(node.p2p_pool, "consensus_threshold", 3)
                break

        return {
            "total_blocks": bc_info.get("total_blocks", 0),
            "total_blockchain_txns": bc_info.get("total_transactions", 0),
            "total_committed": total_committed,
            "total_pending": total_pending,
            "total_created": total_created,
            "consensus_threshold": consensus_threshold,
            "vote_distribution": vote_distribution,
            "recent_transactions": recent_txns,
        }

    # ------------------------------------------------------------------
    # Node activity log
    # ------------------------------------------------------------------

    def _build_node_activity(self, asn: int) -> dict:
        """Return the last 50 detection results + stats for a single node."""
        node = self.node_manager.nodes.get(asn)
        if node is None:
            return {"error": "node not found", "events": []}

        # Last 50 detection results (most recent first)
        results = list(reversed(node.detection_results[-50:]))
        events = []
        for r in results:
            events.append({
                "prefix": r.get("prefix", ""),
                "origin_asn": r.get("origin_asn", 0),
                "is_attack": r.get("is_attack", False),
                "detected": r.get("detected", False),
                "detection_type": r.get("detection_type"),
                "action": r.get("action", ""),
                "label": r.get("label", ""),
                "timestamp": r.get("timestamp"),
            })

        # Node stats
        buf = getattr(node, "_buffer", None)
        buf_queued = len(buf._queue) if buf is not None else 0
        buf_max = buf.max_size if buf is not None else 0

        # Step timings summary
        timings = {}
        st = getattr(node, "step_timings", None)
        if st:
            for step_name, step_deque in st.items():
                vals = list(step_deque)
                timings[step_name + "_ms"] = round(sum(vals) / max(len(vals), 1) * 1000, 3) if vals else 0

        return {
            "asn": asn,
            "is_rpki": node.is_rpki,
            "processed": node.processed_count,
            "total": len(node.observations),
            "attacks_detected": len(node.attack_detections),
            "legitimate_count": node.legitimate_count,
            "running": node.running,
            "buffer_queued": buf_queued,
            "buffer_max": buf_max,
            "stats": dict(node.stats),
            "step_timings": timings,
            "tps": self._compute_node_tps(asn),
            "events": events,
        }

    # ------------------------------------------------------------------
    # Cross-dataset comparison (reads saved results from disk)
    # ------------------------------------------------------------------

    def _build_cross_dataset_comparison(self) -> dict:
        """Scan all results directories and build cross-dataset comparison data."""
        results_root = Path(__file__).resolve().parent.parent / "results"
        if not results_root.exists():
            return {"datasets": [], "error": "No results directory found"}

        datasets = []
        for dataset_dir in sorted(results_root.iterdir()):
            if not dataset_dir.is_dir() or not dataset_dir.name.startswith("caida_"):
                continue

            # Find most recent run (latest timestamped subdirectory)
            run_dirs = sorted(
                [d for d in dataset_dir.iterdir() if d.is_dir()],
                key=lambda d: d.name,
                reverse=True,
            )
            if not run_dirs:
                continue

            latest_run = run_dirs[0]
            entry = {"dataset": dataset_dir.name, "run_dir": latest_run.name}

            # Load summary.json
            summary_path = latest_run / "summary.json"
            if summary_path.exists():
                try:
                    with open(summary_path) as f:
                        summary = _json.load(f)
                    ds = summary.get("dataset", {})
                    ns = summary.get("node_summary", {})
                    perf = summary.get("performance", {})
                    entry.update({
                        "total_ases": ds.get("total_ases", 0),
                        "rpki_count": ds.get("rpki_count", 0),
                        "non_rpki_count": ds.get("non_rpki_count", 0),
                        "total_observations": ds.get("total_observations", 0),
                        "attack_observations": ds.get("attack_observations", 0),
                        "total_processed": ns.get("total_observations_processed", 0),
                        "attacks_detected": ns.get("attacks_detected", 0),
                        "nodes_done": ns.get("nodes_done", 0),
                        "precision": perf.get("precision", 0),
                        "recall": perf.get("recall", 0),
                        "f1_score": perf.get("f1_score", 0),
                        "true_positives": perf.get("true_positives", 0),
                        "false_positives": perf.get("false_positives", 0),
                        "false_negatives": perf.get("false_negatives", 0),
                        "elapsed_seconds": summary.get("elapsed_seconds", 0),
                    })
                except Exception as e:
                    entry["summary_error"] = str(e)

            # Load consensus_log.json
            consensus_path = latest_run / "consensus_log.json"
            if consensus_path.exists():
                try:
                    with open(consensus_path) as f:
                        cl = _json.load(f)
                    entry.update({
                        "txns_created": cl.get("total_transactions_created", 0),
                        "txns_committed": cl.get("total_committed", 0),
                        "txns_pending": cl.get("total_pending", 0),
                    })
                    created = entry["txns_created"]
                    entry["commit_rate"] = round(
                        entry["txns_committed"] / max(created, 1) * 100, 1
                    )
                except Exception:
                    pass

            # Load blockchain_stats.json
            bc_path = latest_run / "blockchain_stats.json"
            if bc_path.exists():
                try:
                    with open(bc_path) as f:
                        bc = _json.load(f)
                    bc_info = bc.get("blockchain_info", {})
                    integrity = bc.get("integrity", {})
                    entry.update({
                        "total_blocks": bc_info.get("total_blocks", 0),
                        "total_blockchain_txns": bc_info.get("total_transactions", 0),
                        "chain_valid": integrity.get("valid", False),
                    })
                except Exception:
                    pass

            # Load bgpcoin_economy.json
            econ_path = latest_run / "bgpcoin_economy.json"
            if econ_path.exists():
                try:
                    with open(econ_path) as f:
                        econ = _json.load(f)
                    entry.update({
                        "total_supply": econ.get("total_supply", 0),
                        "treasury_balance": econ.get("treasury_balance", 0),
                        "total_distributed": econ.get("total_distributed", 0),
                        "total_burned": econ.get("total_burned", 0),
                    })
                except Exception:
                    pass

            # Load dedup_stats.json
            dedup_path = latest_run / "dedup_stats.json"
            if dedup_path.exists():
                try:
                    with open(dedup_path) as f:
                        dd = _json.load(f)
                    entry.update({
                        "rpki_deduped": dd.get("rpki_deduped", 0),
                        "nonrpki_throttled": dd.get("nonrpki_throttled", 0),
                        "total_skipped": dd.get("total_skipped", 0),
                    })
                except Exception:
                    pass

            # Load message_bus_stats.json
            msg_path = latest_run / "message_bus_stats.json"
            if msg_path.exists():
                try:
                    with open(msg_path) as f:
                        mb = _json.load(f)
                    entry.update({
                        "p2p_sent": mb.get("sent", 0),
                        "p2p_delivered": mb.get("delivered", 0),
                        "p2p_dropped": mb.get("dropped", 0),
                    })
                except Exception:
                    pass

            # Load nonrpki_ratings.json summary
            rating_path = latest_run / "nonrpki_ratings.json"
            if rating_path.exists():
                try:
                    with open(rating_path) as f:
                        ratings = _json.load(f)
                    rs = ratings.get("summary", {})
                    entry.update({
                        "avg_trust_score": rs.get("average_score", 0),
                        "malicious_ases": rs.get("by_level", {}).get("malicious", 0),
                        "suspicious_ases": rs.get("by_level", {}).get("suspicious", 0),
                    })
                except Exception:
                    pass

            # Load monitoring_timeseries.json (TPS over time for line chart)
            ts_path = latest_run / "monitoring_timeseries.json"
            if ts_path.exists():
                try:
                    with open(ts_path) as f:
                        ts = _json.load(f)
                    tps_hist = ts.get("tps_history", [])
                    if tps_hist:
                        tps_vals = [p.get("tps", 0) for p in tps_hist if p.get("tps", 0) > 0]
                        entry["avg_tps"] = round(sum(tps_vals) / max(len(tps_vals), 1), 2)
                        entry["peak_tps"] = round(max(tps_vals) if tps_vals else 0, 2)
                    # Compute throughput: observations/second
                    entry["throughput"] = round(
                        entry.get("total_processed", 0) / max(entry.get("elapsed_seconds", 1), 1), 2
                    )
                except Exception:
                    pass

            datasets.append(entry)

        # Sort by total_ases
        datasets.sort(key=lambda d: d.get("total_ases", 0))

        return {"datasets": datasets}

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

            # ── Manuscript time-series (every 5s) ──
            should_sample_ts = (
                len(self._timeseries) == 0 or
                wall_t - self._timeseries[-1]["t"] >= 5
            )

            if should_sample_ts:
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

                # ── Trust coverage history (Fig 4a) ──
                rs = nm.rating_system
                if rs is not None:
                    try:
                        all_ratings = rs.get_all_ratings()
                        rated = sum(1 for r in all_ratings.values()
                                    if r.get("legitimate_announcements", 0) > 0
                                    or r.get("attacks_detected", 0) > 0)
                        non_rpki = sum(1 for n in nm.nodes.values() if not n.is_rpki)
                        total_nr = max(non_rpki, len(all_ratings), 1)
                        cov = round(rated / total_nr * 100, 1)
                    except Exception:
                        cov = 0
                else:
                    cov = 0
                self._trust_coverage_history.append({"t": wall_t, "coverage": cov})

                # ── Consensus breakdown history (Fig 4b) ──
                try:
                    consensus = nm.get_consensus_log()
                    committed = consensus.get("total_committed", 0)
                    pending = consensus.get("total_pending", 0)
                    created = consensus.get("total_transactions_created", 0)
                    single = max(0, created - committed - pending)
                except Exception:
                    committed = pending = single = 0
                self._consensus_breakdown_history.append({
                    "t": wall_t, "confirmed": committed,
                    "pending": pending, "single_witness": single,
                })

                # ── Data flow history (Fig 5a) ──
                self._data_flow_history.append({
                    "t": wall_t,
                    "received": total_processed,
                    "committed": bc_txns,
                    "buffer_depth": sum(
                        len(getattr(n, "_buffer", None)._queue)
                        for n in nm.nodes.values()
                        if n.is_rpki and getattr(n, "_buffer", None) is not None
                    ),
                })

                # ── Attack timeline events ──
                for node in nm.nodes.values():
                    for det in node.attack_detections:
                        key = (det.get("origin_asn"), det.get("prefix"),
                               det.get("detection_type"), det.get("timestamp"))
                        if key not in self._seen_attack_keys:
                            self._seen_attack_keys.add(key)
                            self._attack_timeline_history.append({
                                "t": wall_t,
                                "asn": det.get("origin_asn", 0),
                                "prefix": det.get("prefix", ""),
                                "type": det.get("detection_type") or det.get("label", "UNKNOWN"),
                                "observer": det.get("asn", 0),
                                "bgp_ts": det.get("timestamp"),
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
