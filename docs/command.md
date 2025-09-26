 

🔹 How Your Project Runs

Think of it like a distributed lab experiment where one “conductor” script (the orchestrator) coordinates many “musicians” (the RPKI blockchain nodes).

1. Preparation

You run:

python3 main_experiment.py


The orchestrator (main_experiment.py) loads config, initializes time, and prepares output folders.

2. Node Startup

The SimulationOrchestrator starts RPKI node processes:

Nodes = simulated Autonomous Systems (AS01, AS03, …).

Each node runs its own node.py process, which:

Imports blockchain logic (blockchain/) and services (services/).

Sets up a local blockchain ledger.

Waits to exchange BGP announcements.

The orchestrator checks if all nodes launch successfully and if the “network converges” (all nodes connect to each other).

3. Shared Time Synchronization

The SharedClockManager creates a simulation clock (instead of real system time).

Every node uses this shared time reference → so announcements, consensus, and validation happen in lockstep.

4. Running the Simulation

Once nodes are up and the clock is ticking:

Nodes generate, send, and receive BGP announcements.

Nodes validate announcements via blockchain consensus rules.

Invalid/hijacked prefixes can be detected and penalized.

Blocks are created, containing logs of routing events.

Meanwhile:

NodeHealthMonitor checks if node processes are alive (via psutil) and if they respond.

HealthDashboard (optional) prints colored alerts & summaries to your terminal.

The orchestrator loop enforces duration, monitors status, and can stop early if too many nodes fail.

5. Shutdown

When the time limit is reached (or nodes crash / you press Ctrl+C):

The orchestrator stops the clock.

All node processes are killed.

Health monitoring ends.

6. Results Export

The orchestrator collects results into JSON files:

Experiment metadata (ID, duration, config).

Timing results (simulation clock details).

Simulation summary (node stats, events).

Health summary (how many nodes stayed alive).

Blockchain status (how many blocks mined).

Everything is saved under results/.

A final summary is printed to the console.

🔹 In Plain English

You: Start the experiment.

Orchestrator: Sets up environment, time, and health checks.

Nodes: Each acts like a mini-AS with blockchain validation.

Simulation: Nodes exchange BGP announcements, detect attacks, and record them in blocks.

Monitor: Orchestrator watches node health and progress.

Shutdown: At the end, all data is saved, and the experiment report is printed.