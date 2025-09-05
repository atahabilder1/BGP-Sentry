# BGP-Sentry: Distributed BGP Security Framework

<div style="color: red; font-weight: bold; font-size: 18px; text-align: center; margin: 20px 0; padding: 15px; border: 2px solid red; background-color: #ffe6e6;">
⚠️ Use Python 3.10 with a Virtual Environment ⚠️
</div>

A distributed BGP security monitoring system that simulates blockchain consensus behavior through RPKI-enabled nodes analyzing pre-recorded BGP announcements and maintaining synchronized blockchain storage via peer-to-peer communication.

---

## 📖 Overview

BGP-Sentry creates a realistic distributed blockchain simulation where RPKI-enabled autonomous systems act as independent blockchain nodes. Each node analyzes BGP announcements, participates in consensus voting, and maintains its own blockchain copy through socket-based peer-to-peer communication.

### Core Architecture

- **Distributed Node Network**: 9 independent RPKI nodes running as separate processes  
- **Socket-Based Communication**: Nodes communicate via TCP sockets mimicking real blockchain networks  
- **Individual Blockchain Storage**: Each node maintains its own blockchain file and state  
- **Consensus Mechanism**: Proof-of-reputation consensus requiring 6/9 majority for decisions  
- **BGP Analysis Pipeline**: Real-time processing of pre-recorded BGP announcements  

---

## 🚀 Quick Start

### Prerequisites
- Python **3.10** (required)  
- 8GB RAM minimum  
- Network ports **8001–8017** available  
- 50GB free disk space  

### Installation
```bash
# Clone repository
git clone https://github.com/your-org/BGP-Sentry.git
cd BGP-Sentry

# Create virtual environment
python3.10 -m venv venv310
source venv310/bin/activate   # Windows: venv310\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Verify readiness
cd tests
python3 pre_simulation_check.py
```

### Run Simulation
```bash
python3 main_experiment.py
```

---

## 📊 Monitoring

```bash
# Live dashboard
python3 bgp_dashboard.py

# Check node status
curl http://localhost:8001/status
```

---

## 🤝 Contributing

```bash
pip install -r requirements-dev.txt
flake8 nodes/ --max-line-length=100
pytest tests/ -v
```

---

## 📜 License
MIT License – see LICENSE file.

---

**BGP-Sentry: Realistic Distributed Blockchain Simulation for Internet Security Research**