# 🧪 # 🛡️ BGP-Sentry: Test Suite

A structured test suite for validating core and integrated functionalities of the TrustChain system, including staking, trust score mechanisms, BGP attack detection, and blockchain integrity.

---

## 📚 Table of Contents

### 📖 Introduction
- [About This Test Suite](#about-this-test-suite)

### 🧩 Module-Level Tests
- [1. Staking Mechanism](#1-staking-mechanism)
- [2. Trust Engine](#2-trust-engine)
- [3. RPKI Verification](#3-rpki-verification)
- [4. Trust Score Interface](#4-trust-score-interface)
- [5. Smart Contract Interface](#5-smart-contract-interface)
- [6. BGP Attack Detection](#6-bgp-attack-detection)
- [7. Blockchain Functionality](#7-blockchain-functionality)

### 🔗 Integration & Full Project Tests
- [8. Full System Integration](#8-full-system-integration)

### 🧰 Other Relevant Tests
- [Network Fault Injection Tests](#network-fault-injection-tests)
- [Performance & Stress Tests](#performance--stress-tests)
- [Replay & Log Consistency Tests](#replay--log-consistency-tests)

---

## 📖 Introduction

<details>
<summary><strong>📘 About This Test Suite</strong></summary>

This suite is designed to thoroughly test both **individual components** and **integrated behavior** of the TrustChain system. Modules are tested independently and together to ensure correctness, reliability, and resilience.

Each test file uses `pytest` and can be run individually or as part of the entire suite.

</details>

---

## 🧩 Module-Level Tests

<details>
<summary><strong>📘 1. Staking Mechanism</strong></summary>

**Folder**: `01_staking/`  
**Test File**: `test_staking_mechanism.py`

Tests include:
- Token staking and locking
- Slashing for invalid activity
- Reward distribution

</details>

<details>
<summary><strong>📗 2. Trust Engine</strong></summary>

**Folder**: `02_trust_engine/`  
**Test File**: `test_trust_engine_logic.py`

Tests include:
- Trust score computation
- Penalty logic
- History-based trust decay

</details>

<details>
<summary><strong>📕 3. RPKI Verification</strong></summary>

**Folder**: `03_rpki_verification/`  
**Test File**: `test_rpki_signature_validation.py`

Tests include:
- Prefix validation using ROAs
- Digital signature checks
- Invalid prefix rejection

</details>

<details>
<summary><strong>📙 4. Trust Score Interface</strong></summary>

**Folder**: `04_trust_score_interface/`  
**Test File**: `test_trust_score_updates.py`

Tests include:
- API for trust score read/write
- DB or blockchain consistency
- Sync with trust engine

</details>

<details>
<summary><strong>📒 5. Smart Contract Interface</strong></summary>

**Folder**: `05_sc_interface/`  
**Test File**: `test_smart_contract_calls.py`

Tests include:
- Smart contract function calls (stake, reward, slash)
- Edge cases and revert handling
- Gas usage checks

</details>

<details>
<summary><strong>📓 6. BGP Attack Detection</strong></summary>

**Folder**: `06_bgp_attack_detection/`  
**Test File**: `test_bgp_hijack_detection.py`

Tests include:
- Simulated prefix hijacks
- Leak detection
- Alert and mitigation mechanisms

</details>

<details>
<summary><strong>🧱 7. Blockchain Functionality</strong></summary>

**Folder**: `07_blockchain_functionality/`  
**Test File**: `test_blockchain_core.py`

Tests include:
- Block appending and sync
- Consensus validation
- Fork resolution

</details>

---

## 🔗 Integration & Full Project Tests

<details>
<summary><strong>🚀 8. Full System Integration</strong></summary>

**Folder**: `08_full_integration/`  
**Test File**: `test_end_to_end_workflow.py`

Tests include:
- Full lifecycle: BGP announce → validation → trust update → smart contract reward
- Stake + RPKI + Trust + Blockchain combo validation
- Integration failures and fallback mechanisms

</details>

---

## 🧰 Other Relevant Tests

<details>
<summary><strong>🌐 Network Fault Injection Tests</strong></summary>

Tests include:
- Network latency simulation
- Packet drops or malformed updates
- Consensus failure during network split

</details>

<details>
<summary><strong>⚙️ Performance & Stress Tests</strong></summary>

Tests include:
- High frequency BGP updates
- Concurrent smart contract calls
- Trust score recalculation under load

</details>

<details>
<summary><strong>📁 Replay & Log Consistency Tests</strong></summary>

Tests include:
- Blockchain replay after crash
- Trust recalculation from event logs
- Log hash match across nodes

</details>

---

## ✅ How to Run

Run the full test suite:

```bash
pytest tests/
```

Or run an individual module:

```bash
pytest tests/01_staking/test_staking_mechanism.py
```

---

## 📌 License

MIT License

---