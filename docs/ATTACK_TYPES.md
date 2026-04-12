# BGP-Sentry Attack Types Reference

Complete reference of all BGP attack types in the dataset, how each is detected, and which detection module handles it.

---

## 1. PREFIX_HIJACK

**What it is:** An AS announces a prefix it does NOT own, stealing traffic meant for the legitimate owner.

**Real-world example:**
```
Legitimate: AS15169 (Google) owns 8.8.8.0/24
Attack:     AS_evil announces 8.8.8.0/24 as its own
Result:     Traffic meant for Google goes to AS_evil
```

**How it's detected:**
- Detector 1 (ROA): Check VRP — is this AS authorized for this prefix? If mismatch → hijack
- Detector 6 (Blockchain State): Check prefix_ownership — is there an established owner that's different? → hijack

**Severity:** HIGH — complete traffic interception

---

## 2. SUBPREFIX_HIJACK

**What it is:** An AS announces a MORE SPECIFIC prefix to steal a subset of traffic. In BGP, longer prefixes always win (most specific route wins).

**Real-world example:**
```
Legitimate: AS15169 owns 8.8.0.0/16
Attack:     AS_evil announces 8.8.8.0/24 (more specific)
Result:     Traffic to 8.8.8.0/24 goes to AS_evil
            Traffic to rest of 8.8.0.0/16 still goes to Google
```

**How it's detected:**
- Detector 2 (ROA): Check if announced prefix is a more-specific of a ROA entry with different origin
- Detector 6 (Blockchain State): Parent prefix has established owner → more-specific from different AS is suspicious

**Severity:** HIGH — targeted traffic interception, harder to detect than full hijack

---

## 3. FORGED_ORIGIN_PREFIX_HIJACK

**What it is:** An AS announces a prefix with a FORGED AS path, making it look like the announcement came from the legitimate owner. The attacker prepends the victim's ASN to the path.

**Real-world example:**
```
Legitimate: AS15169 owns 8.8.8.0/24
Attack:     AS_evil announces 8.8.8.0/24 with path [AS_evil, AS15169]
            Makes it look like AS15169 is the origin
            But AS_evil is intercepting traffic in transit
```

**How it's detected:**
- Detector 1 (ROA): May PASS because origin ASN matches ROA (it's forged to look legitimate)
- Detector 6 (Blockchain State): May catch if the AS path structure is unusual
- Detector 7 (Post-hoc): Cross-chain analysis can detect inconsistent paths for same prefix

**Severity:** CRITICAL — bypasses ROA/RPKI validation, hardest attack to detect

**Note:** This is a "post-ROV" attack — specifically designed to evade RPKI protection

---

## 4. BOGON_INJECTION

**What it is:** An AS announces a RESERVED/PRIVATE IP range that should never appear in the global BGP routing table.

**Real-world example:**
```
Attack: AS_evil announces 10.0.0.0/8 (RFC 1918 private range)
        or 192.168.0.0/16 (private range)
        or 224.0.0.0/4 (multicast range)
Result: Can cause routing loops, black holes, or traffic interception
```

**Reserved (bogon) ranges:**
```
0.0.0.0/8         — "this" network
10.0.0.0/8         — RFC 1918 private
127.0.0.0/8        — loopback
169.254.0.0/16     — link-local
172.16.0.0/12      — RFC 1918 private
192.0.2.0/24       — TEST-NET-1 (documentation)
192.168.0.0/16     — RFC 1918 private
198.51.100.0/24    — TEST-NET-2 (documentation)
203.0.113.0/24     — TEST-NET-3 (documentation)
224.0.0.0/4        — multicast
240.0.0.0/4        — reserved (future use)
```

**How it's detected:**
- Detector 3 (Bogon): Match against hardcoded bogon range list
- Detector 6 (Blockchain State): Unknown prefix with no established owner

**Severity:** MEDIUM — usually filtered by well-configured networks, but can cause widespread disruption if not

**Dataset note:** Some attacks labeled BOGON_INJECTION in the dataset use synthetic 44.x.x.x prefixes (not real bogons). These represent "unauthorized prefix injection" and are caught by the blockchain state detector instead.

---

## 5. ROUTE_LEAK

**What it is:** An AS accidentally or maliciously re-announces routes in violation of valley-free routing policy. Leaking provider/peer routes to other providers/peers.

**Real-world example:**
```
Normal BGP valley-free routing:
  Customer → Provider: announce anything (paying for transit)
  Provider → Customer: announce everything (providing transit)
  Peer → Peer: announce only own + customer routes

Attack/Accident:
  AS_leaker receives route from Provider_A
  AS_leaker re-announces it to Provider_B (VIOLATION)
  Result: Provider_B thinks AS_leaker is a transit path
          Traffic takes wrong route, congestion, outages
```

**How it's detected:**
- Detector 4 (Route Leak): Check AS path for valley-free violations using CAIDA customer/provider/peer relationships
- Requires: AS relationships data (auto-built from dataset)

**Severity:** MEDIUM-HIGH — caused major real-world outages (e.g., Google 2017, Cloudflare 2019)

---

## 6. ACCIDENTAL_ROUTE_LEAK

**What it is:** Same as ROUTE_LEAK but unintentional — caused by misconfiguration rather than malice.

**Real-world example:**
```
AS_small_isp misconfigures BGP filters
  → Accidentally re-announces full routing table to peer
  → Peer's customers see AS_small_isp as transit path
  → Traffic overloads AS_small_isp, causes global outage
```

**How it's detected:**
- Same as ROUTE_LEAK (Detector 4) — the detector cannot distinguish intentional from accidental
- Detector 7 (Post-hoc): Behavioral analysis can distinguish — accidental leaks are one-time, intentional leaks are repeated

**Severity:** MEDIUM — same impact as intentional leak, but usually resolved quickly

---

## 7. ROUTE_FLAPPING

**What it is:** An AS repeatedly announces and withdraws a prefix, causing constant BGP UPDATE messages and route recalculation across the network.

**Real-world example:**
```
AS_unstable announces 10.0.0.0/8
  → 30 seconds later: withdraws it
  → 30 seconds later: announces it again
  → 30 seconds later: withdraws it again
  → Repeat 50 times

Result: Every router in the path must recalculate routes each time
        CPU exhaustion on routers, convergence delays, packet loss
```

**How it's detected:**
- Detector 5 (Flapping): Track (prefix, origin) announcement frequency in a sliding window. If count > threshold (default 5) within window (default 60s) → flapping
- Detector 7 (Post-hoc): Temporal analysis detects announcement bursts

**Severity:** MEDIUM — causes instability but doesn't directly intercept traffic

---

## Detection Coverage Matrix

| Attack Type | Det 1 ROA | Det 2 Subprefix | Det 3 Bogon | Det 4 Leak | Det 5 Flap | Det 6 Blockchain State | Det 7 Post-hoc |
|---|---|---|---|---|---|---|---|
| PREFIX_HIJACK | **PRIMARY** | - | - | - | - | **BACKUP** | Corroboration |
| SUBPREFIX_HIJACK | - | **PRIMARY** | - | - | - | **BACKUP** | Corroboration |
| FORGED_ORIGIN_PREFIX_HIJACK | Evaded | - | - | - | - | Partial | **PRIMARY** |
| BOGON_INJECTION | - | - | **PRIMARY** | - | - | **BACKUP** | - |
| ROUTE_LEAK | - | - | - | **PRIMARY** | - | - | Behavioral |
| ACCIDENTAL_ROUTE_LEAK | - | - | - | **PRIMARY** | - | - | Behavioral |
| ROUTE_FLAPPING | - | - | - | - | **PRIMARY** | - | Temporal |

**Key insight:** FORGED_ORIGIN_PREFIX_HIJACK is the hardest attack — it evades RPKI/ROA validation. Only the blockchain state detector and post-hoc cross-chain analysis can catch it. This is the strongest argument for why blockchain-based security is needed beyond RPKI.

---

## Detection Pipeline Summary

```
BGP Announcement arrives at RPKI validator
│
├── Trusted Path Filter (skip if untrusted relay in path)
├── Dedup Filter (skip if seen within 15s/10s)
│
├── Detector 1: PREFIX_HIJACK      (static ROA lookup)
├── Detector 2: SUBPREFIX_HIJACK   (static ROA lookup)
├── Detector 3: BOGON_INJECTION    (hardcoded bogon ranges)
├── Detector 4: ROUTE_LEAK         (CAIDA AS relationships)
├── Detector 5: ROUTE_FLAPPING     (sliding window counter)
├── Detector 6: BLOCKCHAIN_STATE   (dynamic prefix ownership from consensus)
│
├── Consensus voting → blockchain write
│
└── Detector 7: POST-HOC           (cross-chain longitudinal analysis)
    ├── SINGLE_WITNESS accumulation
    ├── Cross-chain corroboration
    ├── Temporal pattern detection
    └── Longitudinal trust scoring
```
