# 🧱 BGPChain: A Custom Blockchain for Storing BGP Announcements

This project is a **lightweight blockchain prototype** designed to store **BGP announcements** in a decentralized and verifiable manner. It simulates BGP updates, collects them into blocks using round-robin consensus logic, and appends the blocks to a local blockchain file.

The system is now modularized into **three distinct components** to reflect a more realistic architecture:
- A **blockchain node** (`bgpchain_node/`)
- A **BGP announcement generator** (`bgp_feed/`)
- A **shared data interface** (`shared_data/`)

Future versions will support **multi-machine deployment** with REST/gRPC communication and BGP validation.

---

## 📦 Project Structure

```
BGP_Announcement_Recorder/
├── bgpchain_node/
│   ├── block.py           # Classes for BGPAnnouncement and Block
│   ├── blockchain.py      # Manages block validation and storage
│   ├── bgp_collector.py   # Reads BGP announcements from shared buffer
│   ├── node.py            # Main node logic (proposal and chain update)
│   ├── config.json        # Local ASN and validator list
│   ├── utils.py           # (Optional) Helper functions
│   └── network.py         # (Reserved for future multi-node communication)
│
├── bgp_feed/
│   └── bgp_generator.py   # Simulates BGP announcements and writes to shared buffer
│
├── shared_data/
│   ├── blockchain.json    # Local append-only blockchain file
│   └── bgp_stream.jsonl   # Live stream of BGP announcements (JSONL format)
```

---

## 🔁 System Workflow (Single Node)

```text
[1] bgp_generator.py (BGP Feed)
    → Simulates and streams BGP announcements to `shared_data/bgp_stream.jsonl`

[2] node.py (Blockchain Node)
    → Every N seconds, checks if it's the current proposer
    → Reads announcements from `bgp_stream.jsonl` using `bgp_collector.py`
    → Creates a new block with BGP updates
    → Hashes, validates, and appends it to `blockchain.json`
```

### 🧠 Information Flow (Detailed)

1. **BGP Simulation (`bgp_feed/`)**
   - The `bgp_generator.py` script runs continuously.
   - It generates random BGP announcements in JSON format.
   - These are appended to a file: `shared_data/bgp_stream.jsonl` (one announcement per line).

2. **Blockchain Node (`bgpchain_node/`)**
   - Each node has a unique ASN defined in `config.json`.
   - Every 10 seconds, `node.py` checks whether this node is the proposer based on round-robin logic.
   - If it's the proposer:
     - It reads the latest announcements from `bgp_stream.jsonl`
     - Wraps them into a block
     - Hashes and stores the block into `shared_data/blockchain.json`

---

## 🧩 File Descriptions

### `block.py`
Defines the two core data structures:
- `BGPAnnouncement`: A single routing update
- `Block`: A unit in the blockchain containing multiple announcements

### `blockchain.py`
Provides logic to:
- Load and save the blockchain
- Add new blocks
- Retrieve the latest block

### `bgp_collector.py`
Reads BGP announcements from `shared_data/bgp_stream.jsonl` (produced by `bgp_feed/`).

### `node.py`
Controls the node's behavior:
- Checks turn to propose
- Builds a block if allowed
- Appends to the chain

### `bgp_generator.py`
Simulates the behavior of a BGP speaker.
- Emits fake BGP announcements every few seconds
- Writes them to `shared_data/bgp_stream.jsonl`

---

## 🔧 How to Run

### 1. Run the BGP Generator (in one terminal)
```bash
cd bgp_feed
python3 bgp_generator.py
```

### 2. Run the Blockchain Node (in another terminal)
```bash
cd bgpchain_node
python3 node.py
```

---

## 🚀 Future Extensions

- 🔁 Support for multiple physical or virtual nodes
- 🌐 REST/gRPC-based communication between nodes
- 🧾 Integration with [ExaBGP](https://github.com/Exa-Networks/exabgp) or real MRT feeds
- 🔐 BGP origin validation using RPKI
- 🧠 Real-time hijack detection alerts
- 📦 Integration with IPFS or Arweave for block anchoring

---

## 📚 Technologies Used

- Python 3
- SHA-256 hashing for block integrity
- JSONL for streaming announcements
- Simple file-based chain storage (blockchain.json)

---

## 🤝 Credits

Developed by [Your Name]  
Inspired by academic research in BGP security and blockchain.

---

## 🛡️ Disclaimer

This is a **prototype for research and educational use** only.  
It is not designed for use in production networks and does not participate in live BGP routing.

---