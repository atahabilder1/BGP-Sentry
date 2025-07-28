# Trust Engine System Parameters

## Overview

The BGP-Sentry Trust Engine System implements a dual-engine architecture for behavioral assessment of non-RPKI Autonomous Systems. This document provides comprehensive parameter specifications for both the Reactive Trust Engine (RTE) and Adaptive Trust Engine (ATE).

## System Architecture

### Dual-Engine Design
- **Reactive Trust Engine (RTE)**: Immediate penalty enforcement
- **Adaptive Trust Engine (ATE)**: Periodic comprehensive assessment
- **Trust Score Range**: 0-100 points
- **Evaluation Frequency**: RTE (real-time), ATE (monthly)

---

## Reactive Trust Engine (RTE) Parameters

### Attack Type Classifications

| Attack Type         | Base Penalty | Severity Weight | Description                                      |
|---------------------|--------------|------------------|--------------------------------------------------|
| Prefix Hijacking    | 15 points    | 1.0              | Complete unauthorized prefix announcement        |
| Subprefix Hijacking | 10 points    | 0.8              | More-specific prefix announcement within legit   |
| Route Leak          | 5 points     | 0.6              | Policy violation in route propagation            |

### Recency Factor (Time-based Penalty Adjustment)

| Time Since Last Violation | Recency Factor | Purpose                          |
|---------------------------|----------------|----------------------------------|
| 0-24 hours                | 1.0            | Full penalty for recent violations |
| 24-72 hours               | 0.7            | Reduced penalty for older violations |
| >72 hours                 | 0.4            | Minimal penalty for distant violations |

### Instant Penalty Calculation Formula

```
T_instant = T_current - (P_base × S_weight × R_factor)
```

**Parameters:**
- `T_instant`: New trust score after penalty  
- `T_current`: Current trust score before violation  
- `P_base`: Base penalty points for attack type  
- `S_weight`: Severity weight (0.6–1.0)  
- `R_factor`: Recency factor (0.4–1.0)  

### Example Penalty Calculations

| Scenario                  | Calculation          | Points Deducted |
|--------------------------|----------------------|-----------------|
| Fresh prefix hijacking   | 15 × 1.0 × 1.0        | 15 points       |
| Route leak after 48h     | 5 × 0.6 × 0.7         | 2.1 points      |
| Subprefix hijack < 24h   | 10 × 0.8 × 1.0        | 8 points        |

---

## Adaptive Trust Engine (ATE) Parameters

### Evaluation Cycle
- **Frequency**: Monthly (30-day windows)
- **Historical Weight (β)**: 0.4
- **Recent Behavior Weight**: 0.6
- **Maximum Bonus Points**: 10

### Behavioral Metrics and Weights

| Metric                        | Weight (w_i) | Score Range | Description                         |
|------------------------------|--------------|-------------|-------------------------------------|
| Attack Frequency & Patterns  | 0.30         | 0–100       | Violation frequency in 30-day window|
| Announcement Stability       | 0.25         | 0–100       | Consistency of BGP announcements    |
| Prefix Ownership Consistency | 0.20         | 0–100       | Registry alignment percentage       |
| Response to Detection        | 0.15         | 0–100       | Speed of violation correction       |
| Participation Consistency    | 0.10         | 0–100       | Network activity regularity         |

### Detailed Metric Calculations

#### 1. Attack Frequency & Patterns (f₁)

```
f₁ = max(0, 100 - (V_count × 20))
```

- **V_count**: Total violations in 30-day window  
- **Escalation Penalty**: -10 points for increasing frequency trends  
- **Data Source**: Blockchain violation logs  

#### 2. Announcement Stability (f₂)

```
f₂ = (A_total / (A_total + W_total)) × 100
```

- **A_total**: Total announcements  
- **W_total**: Total withdrawals  
- **Flapping Penalty**: -5 points per prefix with >10 updates/day  
- **Data Source**: BGP update logs  

#### 3. Prefix Ownership Consistency (f₃)

```
f₃ = (A_valid / A_total) × 100
```

- **A_valid**: Registry-validated announcements  
- **Registry Hierarchy**: RPKI (1.0), IRR (0.7), WHOIS (0.3)  
- **Data Source**: RPKI/IRR cross-validation  

#### 4. Response to Detection (f₄)

```
f₄ = max(0, 100 - (T_avg_response / 60))
```

- **T_avg_response**: Average withdrawal time (seconds)  
- **Fast Response Bonus**: +5 points if <300 seconds  
- **Data Source**: Blockchain timestamps  

#### 5. Participation Consistency (f₅)

```
f₅ = (D_active / D_total) × 100
```

- **D_active**: Active days in evaluation  
- **D_total**: Total days  
- **Long-term Bonus**: +10 points for >6 months active  
- **Data Source**: BGP activity logs  

### Periodic Trust Score Formula

```
T_periodic = β × T_historical + (1-β) × Σ(w_i × f_i) + γ × B_bonus
```

**Parameters:**
- `β`: Historical Weight = 0.4  
- `γ`: Bonus Weight = 0.1  
- `B_bonus`: Sustained good behavior bonus (max 10)  
- `w_i`: Metric weights  
- `f_i`: Normalized scores  

---

## Trust Tier Classification

### Tier Thresholds and Consequences

| Trust Tier          | Score Range | Stake Required (ETH) | Stake Required (Wei)     | Validation Level |
|---------------------|-------------|-----------------------|---------------------------|------------------|
| **Trusted (Green)** | 80–100      | 0.04–0.1              | 4×10¹⁶ – 10¹⁷            | Minimal          |
| **Monitor (Yellow)**| 30–79       | 0.1–0.5               | 10¹⁷ – 5×10¹⁷            | Standard         |
| **Distrusted (Red)**| 0–29        | 0.5–1.0               | 5×10¹⁷ – 10¹⁸            | Maximum          |

### Stake Requirement Calculation

```
S_required = S_base × ((101 - T_score)² / 1000)
```

- `S_base`: 0.1 ETH (10¹⁷ Wei)  
- `T_score`: Current trust score (0–100)  

---

## Economic Integration Parameters

### Smart Contract Staking Features

| Feature                | Parameter               | Description                               |
|------------------------|--------------------------|-------------------------------------------|
| Minimum Stake Adjustment | Within tier minimums   | ASes can configure above minimum          |
| Automatic Slashing     | Immediate upon detection | No manual intervention                    |
| Stake Recovery         | Score-dependent          | Adjusts dynamically                       |
| Emergency Withdrawal   | 7-day cooldown           | Prevents stake abuse                      |
| Violation Multiplier   | 0.2 → 2.0 escalation     | Scales with severity and frequency        |

### Penalty Enforcement Formulas

#### Penalty Amount

```
P_amount = S_balance × P_percentage
```

#### New Stake Requirement

```
S_new_required = S_required × (1 + M_violation)
```

**Violation Multiplier Scale:**
- First Offense: `M_violation = 0.2`  
- Repeat Violations: `0.5–1.0`  
- Systematic Abuse: `2.0`  

---

## System Performance Parameters

### Response Time Requirements

| Component               | Target Response Time | Purpose                        |
|-------------------------|----------------------|--------------------------------|
| RTE Processing          | <1 second            | Immediate penalty application  |
| Trust Score Cache       | <100ms               | Real-time queries              |
| ATE Evaluation          | Monthly batch        | Comprehensive scoring          |
| Stake Adjustment        | <5 seconds           | Economic enforcement           |

### Data Sources and Interfaces

| Data Type         | Source               | Update Frequency | Storage Location         |
|-------------------|----------------------|------------------|---------------------------|
| BGP Violations    | RPKI Observer Nodes  | Real-time        | Blockchain                |
| BGP Updates       | Router Logs          | Continuous       | BGP Update Logs           |
| Trust Scores      | Trust Engine Cache   | Real-time        | Distributed Cache         |
| Stake Balances    | Smart Contracts      | Real-time        | Ethereum Blockchain       |

---

## Configuration Parameters

### System Constants

```python
# RTE Parameters
RTE_BASE_PENALTIES = {
    'prefix_hijacking': 15,
    'subprefix_hijacking': 10,
    'route_leak': 5
}

RTE_SEVERITY_WEIGHTS = {
    'prefix_hijacking': 1.0,
    'subprefix_hijacking': 0.8,
    'route_leak': 0.6
}

RTE_RECENCY_FACTORS = {
    'recent': 1.0,     # 0-24 hours
    'medium': 0.7,     # 24-72 hours
    'old': 0.4         # >72 hours
}

# ATE Parameters
ATE_METRIC_WEIGHTS = {
    'attack_frequency': 0.30,
    'announcement_stability': 0.25,
    'prefix_consistency': 0.20,
    'response_time': 0.15,
    'participation': 0.10
}

ATE_HISTORICAL_WEIGHT = 0.4
ATE_BONUS_WEIGHT = 0.1
ATE_MAX_BONUS = 10

# Staking Parameters
STAKE_BASE = 0.1  # ETH
TRUST_TIER_THRESHOLDS = {
    'green': 80,
    'yellow': 30,
    'red': 0
}

# Economic Parameters
VIOLATION_MULTIPLIERS = {
    'first': 0.2,
    'repeat': 0.5,
    'systematic': 2.0
}
```

---

*End of Document*