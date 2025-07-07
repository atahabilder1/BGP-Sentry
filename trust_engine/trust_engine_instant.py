# --------------------------------------------------------------
# File: trust_engine_instant.py
# Purpose: Apply instant penalties to non-RPKI ASes for malicious behavior
# Used By:
#   - RPKI nodes when detecting clearly bad activity (e.g. hijack)
# Calls:
#   - trust_state.py to read/update trust scores
# --------------------------------------------------------------

from blockchain import trust_state

# --------------------------------------------------------------
# Function: penalize_for_hijack
# Applies immediate penalty (-30) to ASN for a given prefix
# Reason: malicious activity like hijacking or private IP leak
# --------------------------------------------------------------
def penalize_for_hijack(asn, prefix):
    current_score = trust_state.get_trust(asn, prefix)
    new_score = max(0, current_score - 30)
    
    print(f"🚨 Penalty applied to ASN {asn} for {prefix}. Old score: {current_score}, New score: {new_score}")
    
    trust_state.set_trust(asn, prefix, new_score, reason="confirmed hijack or invalid prefix")

# Example usage:
if __name__ == "__main__":
    # Simulated bad actor
    penalize_for_hijack(65011, "203.0.113.0/24")
