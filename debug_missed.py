"""Debug which patterns are missing for the Vendor contract."""
import sys
sys.path.insert(0, r"D:\ContractGuard")
from backend.agents.rule_engine import analyze_clause, _UNIVERSAL_CHECKS

clauses = [
    ("SECTION 2: ALTERATIONS AND IMPROVEMENTS",
     "Vendor may make cosmetic adjustments to the space with prior approval. However, any physical improvements, light fixtures, shelving installations, or structural enhancements made by Vendor shall instantly become the permanent property of Property Owner. Upon expiration of this Agreement, Property Owner may compel Vendor to pay for the professional removal of these items, using a contractor exclusively selected by Property Owner at un-capped commercial rates.",
     "ALTERATIONS"),
    ("SECTION 4: OPERATIONAL FEES AND UTILITY SURCHARGES",
     "Vendor shall pay a flat monthly utility fee of $200 USD. Vendor agrees that Property Owner retains the right to levy unannounced, retroactive operational surcharges at any time to cover building repairs, HVAC overages, or property tax increases incurred over the prior three years. These surcharges are due within twenty-four (24) hours of electronic notice, and failure to pay grants Property Owner the right to seize Vendor's physical inventory as collateral.",
     "FEES_SURCHARGES"),
    ("SECTION 6: INDEMNIFICATION AND LANDLORD LIABILITY",
     "Vendor agrees to indemnify, protect, and absolve Property Owner from any liability relating to roof leaks, electrical fires, flooding, or building structural collapses, even if caused directly by Property Owner's failure to maintain the facilities. Vendor explicitly waives all claims for lost retail revenue, damaged inventory, or physical injuries suffered by employees due to property defects or lack of facility maintenance.",
     "INDEMNIFICATION"),
]

for heading, text, label in clauses:
    harmful, reason = analyze_clause(heading, text)
    print(f"\n=== {label} ===")
    print(f"  Result: harmful={harmful}")
    if reason:
        print(f"  Reason: {reason}")
    else:
        print(f"  NO MATCH — checking each pattern:")
        lowered = text.lower()
        for i, (pattern, template) in enumerate(_UNIVERSAL_CHECKS):
            import re
            if re.search(pattern, lowered, re.IGNORECASE):
                print(f"    ✓ [{i}] {template}")
            else:
                pass  # no match
