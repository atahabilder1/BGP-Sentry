# 🛡️ BGP TrustChain: Blockchain-Based BGP Announcement Auditor

## 📚 Overview

**BGP TrustChain** is a simulation framework designed to secure and audit BGP (Border Gateway Protocol) announcements using a dual-blockchain architecture and trust management. It represents real-world Autonomous Systems (ASes) as nodes in a Mininet-based topology. These nodes are split into two types:

- **RPKI-enabled nodes**: Trusted ASes allowed to write to the blockchain.
- **non-RPKI nodes**: Less trusted ASes that must maintain a minimum trust score and may stake USDC tokens on a public blockchain to boost credibility.

The simulation aims to log all BGP announcements (including hijacks and withdrawals), penalize malicious ASes, and reward good behavior over time. It combines real-time enforcement with historical trend-based scoring.

---

## 📁 Folder & File Structure

```
BGP_ANNOUNCEMENT_RECORDER/
│
├── bgp_feed/
│   └── bgp_simulator.py              # Simulates BGP announcements and withdrawals
│
├── blockchain/
│   ├── block.py                      # BGPAnnouncement and Block classes
│   ├── blockchain.py                 # Blockchain A: append/read chain
│   ├── staking_interface.py         # Checks stake amount on Blockchain B
│   ├── trust_state.py               # Tracks trust scores for (ASN, prefix)
│   └── utils.py                     # Utility functions (hashing, validation)
│
├── nodes/
│   ├── rpki_nodes/
│   │   ├── rpki_65001.py             # Example RPKI node logic
│   │   └── config_65001.json         # Config for RPKI node ASN 65001
│   └── non_rpki_nodes/
│       ├── nonrpki_65010.py         # Example non-RPKI node logic
│       └── config_65010.json         # Config for non-RPKI node ASN 65010
│
├── shared_data/
│   ├── bgp_stream.jsonl             # Shared buffer for incoming BGP data
│   ├── blockchain.json              # Chain of accepted BGP blocks
│   ├── trust_log.jsonl              # Append-only log of trust score events
│   └── trust_state.json             # Current trust scores by (ASN, prefix)
│
├── smart_contract/
│   ├── StakingContract.sol          # Solidity contract for staking (Blockchain B)
│   └── deploy_and_test.py           # Deploy/interact using Web3
│
├── trust_engine/
│   ├── trust_engine_instant.py      # Real-time penalty system for hijacks
│   └── trust_engine_periodic.py     # Monthly trust adjustment from behavior logs
│
├── node.py                          # RPKI node loop for proposing and endorsing blocks
├── requirements.txt                 # Python package dependencies
├── LICENSE
├── .gitignore
└── README.md
```

---

## 🔁 Data Flow Summary

```text
[Mininet] → bgp_simulator.py
              ↓
     shared_data/bgp_stream.jsonl
              ↓
        [RPKI Node: node.py]
          ├── validates prefix
          ├── checks trust (trust_state.json)
          ├── checks stake (staking_interface.py)
          ├── logs announcement (blockchain.json)
          └── adjusts trust (trust_engine_instant.py or periodic.py)
```

---

## 🔐 Trust Architecture

### ✅ Trust Score Design

- Trust score is maintained for each (ASN, prefix) pair.
- Initial score for non-RPKI = 70
- Minimum to be accepted = 70
- Real-time penalty for confirmed hijack = -30
- Periodic reward = +5 or penalty = -10
- Stake boost if trust ≥ 50 but < 70 → +20 (temporary)
- Required stake: 100 USDC on Blockchain B

### ✅ Trust Engine

- `trust_engine_instant.py`: Triggered by malicious behavior (real-time).
- `trust_engine_periodic.py`: Runs monthly, analyzes behavior from blockchain logs.

---

## ⛓️ Blockchain Models

### Blockchain A (Local TrustChain)

- Private/permissioned
- Only RPKI nodes can write
- Stores full BGP announcements (announce/withdraw)
- Logs who endorsed it (`endorsed_by`)
- Tracks AS-path, prefix, timestamp, type, digital signature

### Blockchain B (Public, USDC Staking)

- Holds a smart contract deployed manually (Ethereum/Solana)
- Used by non-RPKI nodes to boost trust
- Smart contract supports:
  - `stake(asn, amount)`
  - `getStake(asn)` → Used in `staking_interface.py`

---

## 🧪 How to Run

### 1. Set up virtual environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Simulate BGP feed
```bash
python bgp_feed/bgp_simulator.py
```

### 3. Launch a RPKI node
```bash
python node.py --asn 65001
```

### 4. Run trust engine (instant check)
```bash
python trust_engine/trust_engine_instant.py
```

### 5. Run trust engine (periodic analysis)
```bash
python trust_engine/trust_engine_periodic.py
```

### 6. Deploy smart contract and stake
```bash
cd smart_contract/
python deploy_and_test.py
```

---

## 🔐 Announcement Format Example

```json
{
  "asn": 65010,
  "prefix": "203.0.113.0/24",
  "as_path": [65010, 65001],
  "next_hop": "10.0.0.1",
  "timestamp": 1723455678,
  "type": "announce",
  "endorsed_by": 65001,
  "signature": "base64sig"
}
```

---

## 💼 Responsibilities

### Major Components

| File/Folder                     | Description |
|--------------------------------|-------------|
| `blockchain/block.py`          | Defines BGPAnnouncement and Block structures |
| `blockchain/blockchain.py`     | Blockchain A logic (append, read chain) |
| `blockchain/trust_state.py`    | Maintains and updates trust scores |
| `blockchain/staking_interface.py` | Reads stake from public chain (Blockchain B) |
| `node.py`                      | Main RPKI node logic: validate and propose blocks |
| `bgp_feed/bgp_simulator.py`    | Generates test BGP data to mimic Mininet stack |
| `trust_engine/*.py`            | Real-time or periodic trust logic |
| `shared_data/*.json`           | Intermediate storage, logs, and buffers |

---

## 🧠 Realism Assumptions

- Each node (RPKI or non-RPKI) represents an actual AS + router stack.
- Mininet runs the routing daemons; Python agents simulate validation and logging.
- Only **first-hop RPKI node** writes a BGP update to the blockchain.
- Withdrawals and hijack attempts are handled and logged the same way.

---

## 📘 For Research Paper / Report

- Emphasize dual-blockchain architecture.
- Two-level trust: Instant (real-time) and Periodic (monthly behavior).
- Blockchain A is internal, Blockchain B is external public.
- Smart contract incentivizes good routing behavior.

---

## 👨‍💻 Author

**Anik Tahabilder**  
Blockchain Researcher | PhD Student | Smart Contract Security Architect  
Project Lead and System Architect of BGP TrustChain