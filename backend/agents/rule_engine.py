"""Universal contract clause fairness analyzer.

Checks EVERY clause for general indicators of unfairness by looking for
universal legal concepts — regardless of clause type, specific wording,
or counterparty role names.
"""
import re
from typing import List, Tuple

# Common counterparty roles — we match broadly to handle any naming
# _A = the "weaker" / receiving party, _B = the "stronger" / drafting party
_PARTY_A = r"(?:employee|client|customer|licensee|vendor|tenant|franchisee|distributee|licensee|subscriber)"
_PARTY_B = r"(?:owner|landlord|developer|employer|provider|company|licensor|franchisor|distributor)"

# Build patterns that reference party roles
_P_INDEMNIFY = rf"{_PARTY_A}.{{0,60}}(?:indemnif|defend|hold\s+harmless|absolv|protect).{{0,60}}{_PARTY_B}"
_P_NEGLIGENCE = r"(?:even\s+if|regardless\s+of|whether\s+or\s+not).{0,40}(?:caused\s+by|result(?:ing|s)\s+from|arising\s+from|due\s+to).{0,40}(?:negligence|fault|failure|breach|misconduct|defect).{0,50}(?:" + _PARTY_B[3:]  # remove "(?:" prefix
_P_TERMINATE = rf"{_PARTY_B}.{{0,20}}(?:may|can|reserves?|retains?|has\s+the\s+right).{{0,30}}(?:terminate|discharge|suspend|cancel|revok|compel|force).{{0,30}}(?:any\s+time|without\s+cause|no\s+reason|immediately|with\s+or\s+without)"
_P_FEECHANGE = r"(?:may|reserves?|retains?|can).{0,20}(?:adjust|change|modif|increas|reduc|alter|levy|assess).{0,20}(?:fee|price|rate|payment|pricing|surcharg|charge).{0,30}(?:at\s+any\s+time|without\s+notice)"
_P_PROPERTY = r"(?:improvement|enhancement|addition|modification|alteration|fixture|installation).{0,50}(?:become|shall\s+be|transfer|assign|vest).{0,30}(?:property|owner|title)"
_P_PERMANENT = r"(?:permanent|sole|exclusive).{0,20}(?:property|owner|title).{0,30}(?:of|to).{0,10}(?:" + _PARTY_B[3:]
_P_IP_OWNER = r"(?!.*(?:work.for.hire|within\s+the\s+scope\s+of\s+employment|during\s+working\s+hours))(?<!non[\s\-])(?:sole|exclusive).{0,20}(?:owner|property|title).{0,30}(?:" + _PARTY_B[3:]

_UNIVERSAL_CHECKS: List[Tuple[str, str]] = [

    # ── Power imbalance / unilateral discretion ──
    (r"(?<!non[\s\-])(?:sole|absolute|unilateral|exclusive).{0,20}(?:discretion|right(?!\s*of\s+first)|authority|decision)",
     "Unilateral discretion clause — one party has sole control"),
    (r"(?:at\s+its|in\s+its).{0,10}(?:sole|absolute|unilateral).{0,10}(?:discretion|opinion|judgment)",
     "One party may act at its sole discretion"),

    # ── Retroactive / unfair changes ──
    (r"retroactive(?:ly)?\s+(?:reduc|withhold|cancel|adjust|modif|chang|terminat|revok|surcharg|fee|charge|assess|levy)",
     "Retroactive changes to agreed terms"),
    (r"(?:reduce|withhold|cancel|adjust|surcharg|levy).{0,30}(?:salary|wage|bonus|compensation|fee|payment|charge|rate).{0,20}(?:discretion|retroactive|unannounced)",
     "Compensation or fees may be retroactively reduced at discretion"),

    # ── One-sided indemnification ──
    (_P_INDEMNIFY,
     "One-sided indemnification — you must indemnify the other party"),
    (rf"{_PARTY_A}.{{10,100}}(?:shall|must|agree).{{0,20}}(?:pay|reimburse).{{0,30}}(?:all|any).{{0,20}}(?:legal|attorney|lawyer|court|litigation).{{0,30}}(?:fee|cost|expense).{{0,40}}(?:regardless|whether|irrespective).{{0,30}}(?:prevail|win|outcome)",
     "You must pay all legal fees regardless of who wins"),

    # ── Responsibility for other party's negligence ──
    (_P_NEGLIGENCE,
     "You are responsible even for the other party's negligence or failures"),

    # ── Excessive penalties / liquidated damages ──
    (r"(?:liquidated\s+damage|penalt).{0,50}(?:\$[\d,]+|thousand|million|[\d,]+\s*dollars)",
     "Liquidated damages or penalty clause"),
    (r"(?:penalt|fine|forfeit).{0,30}(?:\$[\d,]+|thousand|million)",
     "Monetary penalty or forfeiture clause"),

    # ── Low liability caps ──
    (r"(?:capped\s+at|limited\s+to|maximum|not\s+(?:to\s+)?exceed).{0,30}(?:\$[\d,]{1,5})\s*(?:USD|dollars?)?",
     "Suspiciously low liability cap"),
    (r"(?:liability|damages).{0,20}(?:capped\s+at|limited\s+to|maximum).{0,20}(?:\$[\d,]{1,5})",
     "Liability capped at a low amount"),
    (r"aggregate\s+liability.{0,50}(?:\$[\d,]{1,5})",
     "Aggregate liability cap is unreasonably low"),

    # ── Waiving rights ──
    (r"waive[s]?\s+(?:any|all|its|their).{0,20}(?:right|claim|remedy|protection|recours)",
     "Waiver of legal rights or remedies"),
    (r"waive[s]?\s+(?:any|all|its|their).{0,50}(?:lost|damage|injur|revenue|profit)",
     "Waiver of claims for losses or damages"),
    (r"(?:as.is|as\s+is|with\s+all\s+faults).{0,50}(?:warrant|guarant)",
     "All warranties disclaimed — as-is basis"),
    (r"disclaim.{0,30}(?:all|any).{0,20}(?:warrant|guarant|liability)",
     "All warranties disclaimed"),

    # ── Overly broad scope ──
    (r"(?:anywhere|throughout|everywhere).{0,30}(?:world|country|nation|state|territory|united\s+states)",
     "Overly broad geographic scope"),
    (r"(?:any|every).{0,20}(?:business|sector|industry|field|activity).{0,30}(?:compete|operate|engage)",
     "Overly broad scope of restriction"),
    (r"(?:any|all).{0,20}(?:purpose|use|application|commercial).{0,20}(?:right|license|purpose)",
     "Extremely broad grant of rights"),

    # ── Excessive duration ──
    (r"(?:period\s+of|duration\s+of|for\s+).{0,5}(?:five|four|5|4|6|7|8|9|10)\s*(?:year|yr)",
     "Excessive duration of restriction"),
    (r"(?:surviv|contin).{0,30}(?:expiration|termination).{0,30}(?:\d+|ten|five).{0,5}(?:year|yr)",
     "Obligations survive termination for an extended period"),

    # ── Deemed acceptance by silence / trap deadlines ──
    (r"(?:constitutes|deemed|considered|taken\s+as).{0,30}(?:accept|approv).{0,20}(?:unless|if.{0,10}not|fail)",
     "Deemed acceptance by silence — if you don't object in time, you lose your rights"),
    (r"(?:irrevocab(?:ly|le)|permanently|finally).{0,20}(?:accept|approv)",
     "Irrevocable acceptance by default"),
    (r"not\s+(?:disput|reject|object|contest).{0,30}(?:day|business\s+day|hour|window|period).{0,30}(?:deemed|accept|waiv)",
     "Unreasonably short window to dispute or reject"),

    # ── No refund / no recourse ──
    (r"(?:no|without).{0,20}(?:refund|reimburs|restitution|recovery|recourse)",
     "No refund or reimbursement available"),
    (r"not.{0,20}(?:entitled|eligib).{0,20}(?:refund|reimburs|restitution|recovery)",
     "No entitlement to refund or reimbursement"),

    # ── Non-reciprocal rights ──
    (_P_TERMINATE,
     "One-sided right — the other party can terminate or compel action at will"),
    (rf"{_PARTY_B}.{{0,30}}(?:may|can|reserves?).{{0,30}}(?:assign|transfer).{{0,30}}(?:without.{{0,10}}(?:consent|notice|approv))",
     "One-sided assignment right — your agreement can be transferred without your consent"),

    # ── Unilateral changes / no-notice ──
    (r"(?:adjust|change|modif|increas|reduc|alter|levy|assess).{0,20}(?:fee|price|rate|payment|term|pricing|surcharg|charge).{0,30}(?:at\s+any\s+time|without\s+notice|sole\s+discretion|unannounced)",
     "Unilateral changes to fees or terms without meaningful notice"),
    (_P_FEECHANGE,
     "One party may unilaterally change fees at any time"),

    # ── Forced payment / compelled action at un-capped rates ──
    (r"(?:compel|force|require).{0,20}(?:pay|reimburse|cover|purchase).{0,30}(?:cost|fee|rate|expense|charge|removal|contractor)",
     "You may be compelled to pay for costs you did not agree to"),
    (r"(?:un.capped|any\s+rate|whichever\s+is\s+higher|at\s+its\s+sole\s+discretion|exclusively\s+select).{0,40}(?:rate|price|fee|cost|charge|contractor)",
     "Unilateral pricing — one party controls costs without negotiation"),

    # ── Unreasonable deadlines ──
    (r"(?:due|payable|required|notice).{0,20}(?:twenty|twenty-four|24|12|48|thirty|10|5|3|2|1).{0,10}(?:hour|day).{0,20}(?:notice|receipt|notification|electronic)",
     "Unreasonably short deadline for payment or action"),
    (r"(?:\d+).{0,5}(?:hour|day).{0,20}(?:to\s+pay|for\s+payment|deadline|cure|remedy)",
     "Very short deadline for payment or remedy"),

    # ── Self-help / seizure of property ──
    (r"(?:seize|confiscate|repossess|impound|withhold|attach).{0,40}(?:inventory|property|asset|equipment|good|product|collateral|belonging)",
     "Self-help remedy — the other party may seize your property without court order"),

    # ── Unjust enrichment / property transfer without compensation ──
    (_P_PROPERTY,
     "Improvements you pay for become the other party's property"),
    (_P_PERMANENT,
     "One party retains ownership of items you paid for"),

    # ── Unilateral data monetization ──
    (r"(?:perpetual|irrevocable|worldwide).{0,30}(?:license|right).{0,40}(?:data|information|content|material).{0,40}(?:commercial|monetize|sell|broker)",
     "Perpetual, irrevocable rights to your data for commercial purposes"),
    (r"(?:sell|broker|monetize|commercialize).{0,30}(?:data|information)",
     "Your data may be sold or commercialized"),

    # ── One-sided IP ownership (excludes standard employee work-for-hire) ──
    (_P_IP_OWNER,
     "One party retains sole ownership of work product — you paid but they own it"),

    # ── Automatic renewal with penalty ──
    (r"(?:increase|penalt|fee|charge|additional).{0,30}(?:upon|when|after|on).{0,20}(?:renew|auto)",
     "Financial penalty or price increase tied to renewal"),

    # ── Narrow windows / traps ──
    (r"(?:no\s+earlier\s+than|no\s+later\s+than|precisely|exactly).{0,30}(?:\d+).{0,20}(?:day|business\s+day)",
     "Unreasonably narrow cancellation window"),

    # ── No data export ──
    (r"delete\s+all\s+(?:your|the|client|customer|employee|vendor).{0,20}data.{0,50}(?:without.{0,20}(?:export|backup|cop|retriev))",
     "Data deleted without export or backup option"),

    # ── Pre-dispute binding arbitration with class waiver ──
    (r"binding\s+arbitration.{0,50}(?:waiv|give\s+up|forfeit).{0,30}(?:class|jury|appeal)",
     "Binding arbitration with waiver of class-action or jury trial rights"),
]


def detect_type(heading: str, text: str) -> str:
    """Detect clause type (for better explanations)."""
    combined = (heading + " " + text).lower()
    if re.search(r"\b(?:indemnif|hold\s+harmless|duty\s+to\s+defend)", combined, re.IGNORECASE):
        return "indemnification"
    if re.search(r"\b(?:limit(?:ation)?\s+of\s+liab|cap\s+on\s+liab|aggregate\s+liab)", combined, re.IGNORECASE):
        return "liability"
    if re.search(r"\b(?:payment\b|invoice|fee|pricing|compensation|salary|wage|bonus|surcharg)", combined, re.IGNORECASE):
        return "payment"
    if re.search(r"\b(?:renew|automatic(?:ally)?\s+renew)", combined, re.IGNORECASE):
        return "renewal"
    if re.search(r"\b(?:intellectual\s+prop|ip\s+right)", combined, re.IGNORECASE):
        return "intellectual_property"
    if re.search(r"data\s+(?:right|use|ownership|license)", combined, re.IGNORECASE):
        return "data_rights"
    if re.search(r"\b(?:terminat|non.compete|covenant\s+not\s+to\s+compete|restrictive\s+covenant)", combined, re.IGNORECASE):
        return "termination"
    if re.search(r"\b(?:delivery\b|acceptance\b|inspection)", combined, re.IGNORECASE):
        return "delivery"
    if re.search(r"\bconfident", combined, re.IGNORECASE):
        return "confidentiality"
    if re.search(r"\b(?:warrant|disclaimer)", combined, re.IGNORECASE):
        return "warranty"
    if re.search(r"\b(?:governing\s+law|choice\s+of\s+law|jurisdiction)", combined, re.IGNORECASE):
        return "governing_law"
    if re.search(r"\b(?:dispute|arbitration)", combined, re.IGNORECASE):
        return "dispute"
    if re.search(r"\bassign", combined, re.IGNORECASE):
        return "assignment"
    if re.search(r"force\s+majeure", combined, re.IGNORECASE):
        return "force_majeure"
    return "general"


def analyze_clause(heading: str, text: str) -> Tuple[bool, str]:
    """Analyze a clause for harmful patterns.

    Applies universal fairness checks to EVERY clause, regardless of type.
    Returns (is_harmful: bool, reason: str).
    """
    if not text.strip():
        return False, ""

    lowered = text.lower()
    reasons: List[str] = []

    for pattern, template in _UNIVERSAL_CHECKS:
        if re.search(pattern, lowered, re.IGNORECASE):
            reasons.append(template)

    # Remove property-ownership reasons if text describes standard work-for-hire
    # (regex lookbehinds can't handle "work-for-hire" appearing BEFORE "exclusive property of")
    if re.search(r"work.for.hire|during\s+working\s+hours|within\s+the\s+scope\s+of\s+employment", lowered, re.IGNORECASE):
        reasons = [r for r in reasons if "ownership of items you paid for" not in r
                   and "sole ownership of work product" not in r
                   and "Improvements you pay for become" not in r]

    if reasons:
        return True, "; ".join(dict.fromkeys(reasons))

    # ── Structural fallback: detect one-sidedness when no pattern matched ──
    is_harmful, reason = _structural_analyze(text)
    if is_harmful:
        return True, reason

    # ── Similarity fallback: classify using TF-IDF similarity to known examples ──
    # (generalizes to new clause types by measuring semantic similarity)
    try:
        from backend.agents.tfidf_classifier import similarity_classify
        sim_harmful, sim_conf, sim_reason = similarity_classify(text)
        if sim_harmful is True:
            return True, f"Similarity-based classification (confidence: {sim_conf}): {sim_reason}"
    except Exception:
        pass

    return False, ""


# ── Structural fairness analyzer ──────────────────────────────────────
# Works on ANY clause by analyzing WHO does WHAT to WHOM.
# Detects one-sidedness even with novel wording no pattern covers.

# All known role words — expanded as new contracts appear
_KNOWN_ROLES = [
    "provider", "client", "customer", "employee", "employer",
    "developer", "company", "licensor", "licensee",
    "vendor", "owner", "landlord", "tenant",
    "franchisor", "franchisee", "distributor", "distributee",
    "subscriber", "contractor", "consultant", "agent",
    "manager", "operator", "supplier", "seller", "buyer",
    "lessor", "lessee", "licensor", "licensee",
    "indemnitor", "indemnitee", "insurer", "insured",
]

# Multi-word role patterns (e.g., "Property Owner", "Service Provider")
_MULTI_WORD_ROLES = re.compile(
    r"(?:Property|Service|Platform|Software|Data|Technology|Network|System|Facility|Building|Premises|Space)"
    r"\s+"
    r"(?:Owner|Provider|Company|Operator|Manager|Supplier|Vendor|Licensor|Lessor)",
    re.IGNORECASE,
)

# Detect obligation vs right keywords
_RE_OBLIGATION = re.compile(
    r"(?:shall|must|will|agrees?\s+to|undertakes?\s+to|obligated?\s+to|"
    r"responsible\s+for|liable\s+for|required?\s+to|duty\s+to|"
    r"covenants?\s+to|warrants?\s+that)",
    re.IGNORECASE,
)
_RE_RIGHT = re.compile(
    r"(?:may(?!\s+not)|can|reserves?\s+(?:the\s+)?right|entitled?\s+to|"
    r"retains?\s+(?:the\s+)?right|has\s+the\s+(?:right|authority|option)|"
    r"right\s+to|option\s+to|at\s+its\s+(?:sole\s+)?discretion|"
    r"shall\s+be\s+entitled|shall\s+have\s+the\s+right|"
    r"grants?\s+\w+\s+a\s+(?:non.exclusive|perpetual|irrevocable))",
    re.IGNORECASE,
)
_RE_RESTRICTION = re.compile(
    r"(?:shall\s+not|must\s+not|may\s+not|is\s+not\s+(?:entitled|permitted|allowed)|"
    r"prohibited\s+from|no\s+(?:right|authority|option)|"
    r"shall\s+not\s+directly\s+or\s+indirectly)",
    re.IGNORECASE,
)
# "Each party" / "both parties" — mutual obligations
_RE_MUTUAL = re.compile(
    r"(?:each|both|either|neither)\s+(?:party|side|entity|person|individual)",
    re.IGNORECASE,
)


def _find_all_parties(text: str) -> List[str]:
    """Find all distinct party references in the text."""
    found: List[str] = []
    seen = set()

    # Multi-word roles (e.g. "Property Owner")
    for m in _MULTI_WORD_ROLES.finditer(text):
        name = m.group(0).strip().lower()
        if name not in seen:
            seen.add(name)
            found.append(m.group(0))

    # Single-word known roles
    lowered = text.lower()
    for role in _KNOWN_ROLES:
        for m in re.finditer(r"\b" + role + r"\b", lowered):
            # Get the original-cased text
            orig = text[m.start():m.end()]
            key = orig.lower()
            if key not in seen:
                seen.add(key)
                found.append(orig)

    return found


def _classify_sentence(
    sent: str,
    parties: List[str],
) -> List[Tuple[str, str]]:
    """Classify a sentence into (party, type) pairs.

    type is one of: 'obligation', 'right', 'restriction'.
    Returns empty list if no clear classification.
    """
    lowered = sent.lower()
    results: List[Tuple[str, str]] = []

    # Check if this is a mutual obligation ("Each party shall...")
    mutual = bool(_RE_MUTUAL.search(lowered))

    # Determine the predicate type
    is_obligation = bool(_RE_OBLIGATION.search(lowered))
    is_right = bool(_RE_RIGHT.search(lowered))
    is_restriction = bool(_RE_RESTRICTION.search(lowered))

    # Prefer restriction over obligation/right for "shall not" etc.
    if is_restriction:
        ptype = "restriction"
    elif is_obligation:
        ptype = "obligation"
    elif is_right:
        ptype = "right"
    else:
        return results

    if mutual:
        # "Each party shall..." → applies to all parties
        for p in parties:
            results.append((p, ptype))
        return results

    # Find which party is the subject of this sentence
    for p in parties:
        # Check if this party appears early in the sentence (likely the subject)
        p_lower = p.lower()
        idx = lowered.find(p_lower)
        if idx >= 0 and idx < len(sent) // 2:  # subject is usually in first half
            results.append((p, ptype))
            return results

    # Fallback: try to find an obligation/right keyword near a party name
    for p in parties:
        p_lower = p.lower()
        for pattern, ptype_pattern in [
            (_RE_OBLIGATION, "obligation"),
            (_RE_RIGHT, "right"),
            (_RE_RESTRICTION, "restriction"),
        ]:
            for m in pattern.finditer(lowered):
                # Check if party name is within 40 chars of the keyword
                p_idx = lowered.find(p_lower)
                m_idx = m.start()
                if abs(p_idx - m_idx) < 40:
                    results.append((p, ptype_pattern))
                    return results

    return results


def _structural_analyze(text: str) -> Tuple[bool, str]:
    """Fallback: detect one-sidedness by analyzing clause structure.

    Parses sentences to find who must do what vs who may do what.
    Returns False if balanced or unclear, True + reason if one-sided.
    """
    if not text.strip():
        return False, ""

    parties = _find_all_parties(text)
    if len(parties) < 1:
        return False, ""

    # Split into sentences (rough split on . ! ?)
    sentences = [s.strip() for s in re.split(r'[.?!]', text) if s.strip()]

    obligations: dict[str, int] = {}
    rights: dict[str, int] = {}
    restrictions: dict[str, int] = {}
    for p in parties:
        obligations[p] = 0
        rights[p] = 0
        restrictions[p] = 0

    for sent in sentences:
        for party, ptype in _classify_sentence(sent, parties):
            if ptype == "obligation":
                obligations[party] += 1
            elif ptype == "right":
                rights[party] += 1
            elif ptype == "restriction":
                restrictions[party] += 1

    # Identify which party bears obligations/restrictions and which has rights
    # Harmful signal: Party A has obligations/restrictions AND Party B has rights
    # (NOT: only one party has obligations — that's normal in clauses like "Developer shall do X")
    burdened_parties = [p for p in parties if obligations[p] + restrictions[p] > 0]
    entitled_parties = [p for p in parties if rights[p] > 0]

    # Must have at least one burdened party AND a DIFFERENT entitled party
    if not burdened_parties or not entitled_parties:
        return False, ""
    if burdened_parties == entitled_parties:
        return False, ""

    # Find the most burdened and the most entitled
    most_burdened = max(burdened_parties, key=lambda p: obligations[p] + restrictions[p])
    most_entitled = max(entitled_parties, key=lambda p: rights[p])

    # Skip if same party (mutual obligations/rights)
    if most_burdened.lower() == most_entitled.lower():
        return False, ""

    burden_count = obligations[most_burdened] + restrictions[most_burdened]
    right_count = rights[most_entitled]

    # Require significant imbalance: at least 2 obligations on one side
    # AND at least 1 right on the other
    if burden_count >= 2 and right_count >= 1:
        parts = []
        if obligations[most_burdened]:
            parts.append(f"{obligations[most_burdened]} obligation(s)")
        if restrictions[most_burdened]:
            parts.append(f"{restrictions[most_burdened]} restriction(s)")
        return True, (
            f"One-sided clause — {most_burdened} bears "
            f"{' and '.join(parts)} while "
            f"{most_entitled} has {rights[most_entitled]} right(s)"
        )

    return False, ""
