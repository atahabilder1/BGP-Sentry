# BGP-Sentry: Distributed Blockchain Simulation for BGP Security

BGP-Sentry simulates a blockchain-secured BGP (Border Gateway Protocol) network.  
It orchestrates multiple autonomous system (AS) nodes, synchronizes them with a shared simulation clock, and validates routing announcements through blockchain consensus.  

Think of it like a distributed lab experiment where one **conductor** script (the orchestrator) coordinates many **musicians** (the RPKI blockchain nodes).

---

## 🚀 How It Works

### 1. Preparation
Run the experiment with:

```bash
python3 main_experiment.py
```

- The orchestrator (`main_experiment.py`) loads configuration, initializes a simulation clock, and prepares output directories.

---

### 2. Node Startup
- The **SimulationOrchestrator** starts RPKI node processes (AS01, AS03, …).  
- Each node runs its own `node.py`, which:
  - Imports blockchain logic (`blockchain/`) and services (`services/`).
  - Sets up a local blockchain ledger.
  - Waits to exchange BGP announcements.

The orchestrator checks if nodes launch successfully and if the **network converges** (all nodes connect).

---

### 3. Shared Time Synchronization
- The **SharedClockManager** provides a simulation clock (instead of real system time).  
- Every node uses this shared reference so that:
  - Announcements
  - Consensus
  - Validation  
  all happen **in lockstep**.

---

### 4. Running the Simulation
Once nodes are up and the clock is ticking:

- **Nodes**:
  - Generate, send, and receive BGP announcements.
  - Validate announcements via blockchain consensus rules.
  - Detect and penalize invalid/hijacked prefixes.
  - Create blocks containing logs of routing events.

- **Monitoring**:
  - **NodeHealthMonitor** checks node processes with `psutil`.
  - **HealthDashboard** (optional) prints colored alerts & summaries.
  - The orchestrator enforces simulation duration, monitors node status, and can stop early if too many nodes fail.

---

### 5. Shutdown
At the end of the experiment (time limit reached, crash, or Ctrl+C):

- The orchestrator stops the clock.
- All node processes are terminated.
- Health monitoring stops.

---

### 6. Results Export
The orchestrator collects results and saves them in `results/`:

- **Experiment metadata** (ID, duration, config).
- **Timing results** (simulation clock details).
- **Simulation summary** (node stats, events).
- **Health summary** (running vs. failed nodes).
- **Blockchain status** (how many blocks mined).

A final summary is printed to the console.

---

## 📝 In Plain English
1. **You**: Start the experiment.  
2. **Orchestrator**: Sets up environment, time, and health checks.  
3. **Nodes**: Act like mini-ASes with blockchain validation.  
4. **Simulation**: Nodes exchange BGP announcements, detect attacks, and record them in blocks.  
5. **Monitor**: Orchestrator watches node health and progress.  
6. **Shutdown**: Data is saved, and a final report is printed.  

---

## 📂 Outputs
After a run, check the `results/` directory for:
- `bgp_sentry_results_<timestamp>.json`
- `health_report_<timestamp>.json`
- `simulation_summary_<timestamp>.json`

Each file captures different aspects of the experiment for later analysis.

---

## ⚙️ Requirements
- Python 3.8+  
- Virtual environment recommended (`venv/`)  
- Install dependencies via:

```bash
pip install -r requirements.txt
```

---

## 📜 License
MIT License (or specify your project’s license here)
