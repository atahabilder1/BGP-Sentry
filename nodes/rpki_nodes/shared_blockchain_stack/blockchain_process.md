# RPKI Blockchain System

## Overview

This project implements a blockchain-based system for processing Border Gateway Protocol (BGP) announcements in a Resource Public Key Infrastructure (RPKI) context. Each RPKI node acts as a full blockchain node, capable of parsing BGP announcements, creating signed transactions, managing a transaction pool with a voting mechanism (requiring ≥3 votes for transaction validity), committing verified transactions to blocks, and verifying transactions while ensuring blockchain integrity. The system uses a file-based lock to prevent race conditions during block writing and includes detailed debug logging for traceability.

## Purpose

The system is designed to:

* Parse BGP announcements from `bgpd.json` and extract fields (`sender_asn`, `ip_prefix`, `timestamp`, `trust_score`, `prefix_length`).
* Create signed transactions with RSA signatures and store them in a transaction pool (`transaction_pool.json`).
* Require at least three peer node verifications (votes) before committing transactions to the blockchain (`blockchain.json`).
* Use a file-based lock (`blockchain_lock.json`) to ensure only one node writes to the blockchain at a time.
* Verify transactions in the pool or blockchain, skipping self-initiated transactions to maintain decentralization principles.
* Provide a modularized architecture with scripts in a `blockchain_node` folder for maintainability.

## Folder Structure

```
project_root/
├── blockchain_node/
│   ├── parse_bgp.py
│   ├── create_transaction.py
│   ├── transaction_pool.py
│   ├── commit_to_blockchain.py
│   ├── verify_transaction.py
│   ├── main.py
│   ├── *.log
├── shared_data/
│   ├── bgpd.json
│   ├── trust_state.json
│   ├── transaction_pool.json
│   ├── blockchain.json
│   ├── blockchain_lock.json
│   └── public_keys/
│       └── <sender_asn>.pem
└── README.md
```

* \`\`: Contains all Python scripts and log files.
* \`\`: Stores input files (`bgpd.json`, `trust_state.json`), transaction pool (`transaction_pool.json`), blockchain (`blockchain.json`), lock file (`blockchain_lock.json`), and public keys (`public_keys/<sender_asn>.pem`).
* **Logs**: Each script generates a `<module_name>.log` file in `blockchain_node/` with detailed debug information.

## File Descriptions

| **File Name**             | **Purpose**                                                                   | **Inputs**                                                        | **Outputs**                                | **Key Features**                             |
| ------------------------- | ----------------------------------------------------------------------------- | ----------------------------------------------------------------- | ------------------------------------------ | -------------------------------------------- |
| `parse_bgp.py`            | Parses `bgpd.json` and `trust_state.json` to extract BGP announcement fields. | `bgpd.json`, `trust_state.json`, user input (announcement index). | Parsed announcement dictionary, logs.      | Validates JSON/input, extracts fields.       |
| `create_transaction.py`   | Creates signed transaction, adds to pool, saves public key.                   | Parsed data, generates RSA key pair.                              | Transaction in pool, public key file, log. | Signs data, logs creation.                   |
| `transaction_pool.py`     | Manages transaction pool and voting.                                          | Transaction dict, voter ASN.                                      | Updates to `transaction_pool.json`, logs.  | Tracks votes, verifies 3+ rule.              |
| `commit_to_blockchain.py` | Commits verified transactions using lock.                                     | Node ASN, verified transactions.                                  | Block in `blockchain.json`, log.           | Locking mechanism, block builder.            |
| `verify_transaction.py`   | Verifies signatures and adds votes.                                           | Transaction ID, node ASN.                                         | Verification result, logs.                 | Skips self-verification, validates RSA sigs. |
| `main.py`                 | Orchestrates full workflow.                                                   | Node ASN, user interaction.                                       | Calls all modules, logs.                   | Simulates peer workflow.                     |

## Prerequisites

* **Python 3.8+**
* **cryptography library**

```bash
pip install cryptography
```

> OS: Unix-like (Linux/macOS). Windows users should adapt file commands manually.

## Setup Instructions

### Create the Folder Structure

```bash
mkdir -p blockchain_node
cd blockchain_node

touch parse_bgp.py create_transaction.py transaction_pool.py commit_to_blockchain.py verify_transaction.py main.py
chmod +x *.py

cd ..
touch README.md
mkdir -p shared_data/public_keys
```

### Populate Script Files

Use a text editor (e.g., `nano`) to paste the content from the corresponding artifact IDs:

* `parse_bgp.py`: ID 711137a7-babb-40c6-bb73-777e499e726b
* `create_transaction.py`: ID cd831939-5542-40d0-b2f6-033bfefd1369
* `transaction_pool.py`: ID 90ac416b-a468-4428-9034-f226468456bd
* `commit_to_blockchain.py`: ID 7bfb0f50-00b5-44a9-84b1-c3c6fa0cdc1f
* `verify_transaction.py`: ID 7f4f9dfb-eb96-4310-b873-d243233e43b8
* `main.py`: ID 90508807-e7a7-4850-962a-61801bac4cbb

### Set Up Shared Data

**bgpd.json**

```json
{
  "bgp_announcements": [
    {
      "sender_asn": 2,
      "announced_prefixes": ["203.0.113.0/24"],
      "timestamp": "2025-07-24T14:00:00Z"
    }
  ]
}
```

**trust\_state.json**

```json
{
  "1": 85.5,
  "3": 90.0
}
```

## Run the Workflow

```bash
cd blockchain_node
python main.py
```

Follow prompts to:

* Input this node's ASN
* Choose a BGP announcement
* Simulate peer verifications

## Example Workflow Output

```text
Enter this node's ASN: 2

Enter the announcement number to process (1-1): 1
Announcement 1:
  sender_asn: 2
  prefix: 203.0.113.0/24
  timestamp: 2025-07-24T14:00:00Z

Transaction 550e8400-... created and added to transaction_pool.json

Simulate verification by entering 3 peer ASNs:
  Peer ASN 3: Vote added ✅
  Peer ASN 4: Vote added ✅
  Peer ASN 5: Vote added ✅

Block a1b2c3d4-... written to blockchain.json
Transaction removed from transaction_pool.json

Skipping verification of self-initiated transaction
```

## Resulting Files

### `transaction_pool.json`

```json
{
  "transactions": []
}
```

### `blockchain.json`

```json
{
  "blocks": [
    {
      "block_id": "a1b2c3d4-...",
      "block_timestamp": "2025-07-26T03:53:00.123456Z",
      "transactions": [
        {
          "transaction_id": "550e8400-...",
          "sender_asn": 2,
          "ip_prefix": "203.0.113.0/24",
          "timestamp": "2025-07-24T14:00:00Z",
          "trust_score": "N/A",
          "transaction_timestamp": "2025-07-26T03:53:00.123456Z",
          "previous_hash": "000...",
          "signature": "4a5b...",
          "votes": [3, 4, 5]
        }
      ],
      "previous_block_hash": "000...",
      "block_hash": "7c4a8d09..."
    }
  ]
}
```

### `public_keys/2.pem`

Contains the public key for ASN 2

---

## Additional Notes

* **Race Conditions**: Prevented using `blockchain_lock.json`.
* **Peer Verification**: Simulated via prompts. In production, peers run `verify_transaction.py` independently.
* **Public Key Management**: Uses per-transaction RSA keys. For production, use persistent per-ASN keys.
* **Shared Data Sync**: Assumes shared folder (e.g., via NFS). Consider P2P + consensus for decentralization.
* **Timestamps**: UTC-based (e.g., 2025-07-26T03:53:00Z).
* **Logging**: Each script logs to its respective `.log` file with debug details.

## Troubleshooting

| Issue                 | Solution                                           |
| --------------------- | -------------------------------------------------- |
| `FileNotFoundError`   | Ensure shared\_data/ exists and contains all files |
| Invalid JSON          | Validate `bgpd.json`, `trust_state.json`           |
| Permission denied     | Run `chmod +w shared_data/*`                       |
| Dependency missing    | Run `pip install cryptography`                     |
| Race condition errors | Confirm lock file access is consistent             |

## Future Enhancements

* Add P2P network layer for transaction propagation
* Implement consensus (e.g., PBFT, Raft)
* Use public key infrastructure (PKI) or CA for key management
* Replace `transaction_pool.json` with a distributed DB
* Add on-chain validation for BGP prefix ownership
