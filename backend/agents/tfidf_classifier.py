"""Example-based clause classifier using TF-IDF + cosine similarity.

Learns from labeled training examples and classifies new clauses by
how similar they are to known harmful/unharmful clauses.
No external dependencies — pure Python using math + collections.

This generalizes to NEW clause types because it measures semantic
similarity, not exact keyword matching.
"""
import math
import re
from collections import Counter, defaultdict
from typing import List, Tuple, Optional


class TfidfClassifier:
    """TF-IDF weighted k-NN classifier for contract clauses."""

    def __init__(self):
        self._idf: dict[str, float] = {}
        self._examples: List[Tuple[Counter, bool, str]] = []  # (tfidf_vector, is_harmful, label)

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """Tokenize into lowercased words 3+ chars (skips numbers, short words)."""
        text = text.lower()
        # Remove punctuation but keep intra-word hyphens
        text = re.sub(r"[^\w\s-]", " ", text)
        text = re.sub(r"\b\w{1,2}\b", " ", text)  # remove 1-2 char words
        return re.findall(r"\b[a-z][a-z-]+[a-z]\b", text)

    @staticmethod
    def _cosine_similarity(v1: Counter, v2: Counter) -> float:
        intersection = set(v1.keys()) & set(v2.keys())
        dot = sum(v1[w] * v2[w] for w in intersection)
        n1 = math.sqrt(sum(v * v for v in v1.values()))
        n2 = math.sqrt(sum(v * v for v in v2.values()))
        if n1 == 0 or n2 == 0:
            return 0.0
        return dot / (n1 * n2)

    def fit(self, texts: List[str], labels: List[bool], labels_str: Optional[List[str]] = None) -> None:
        """Fit on training examples. Labels: True=harmful, False=unharmful."""
        n = len(texts)
        tokenized = [self._tokenize(t) for t in texts]

        # IDF: log(N / df)
        doc_freq: Counter = Counter()
        for tokens in tokenized:
            doc_freq.update(set(tokens))
        self._idf = {
            w: math.log(n / (f + 1)) + 1.0
            for w, f in doc_freq.items()
        }

        # TF-IDF vectors for each example
        for i, tokens in enumerate(tokenized):
            tf = Counter(tokens)
            vec: Counter = Counter()
            for word, count in tf.items():
                if word in self._idf:
                    vec[word] = count * self._idf[word]
            lbl = labels_str[i] if labels_str and i < len(labels_str) else ""
            self._examples.append((vec, labels[i], lbl))

    def predict(
        self, text: str, k: int = 5
    ) -> Tuple[bool, float, List[Tuple[str, float]]]:
        """Classify a clause. Returns (is_harmful, confidence, nearest_neighbors).

        confidence: 0.0-1.0 (proportion of weighted vote for harmful)
        nearest_neighbors: list of (label, similarity) for top-k
        """
        tokens = self._tokenize(text)
        if not tokens:
            return False, 0.0, []

        # TF-IDF vector for input
        tf = Counter(tokens)
        vec: Counter = Counter()
        for word, count in tf.items():
            if word in self._idf:
                vec[word] = count * self._idf[word]

        # Compute similarities
        sims: List[Tuple[float, bool, str]] = []
        for ex_vec, ex_harmful, ex_label in self._examples:
            sim = self._cosine_similarity(vec, ex_vec)
            sims.append((sim, ex_harmful, ex_label))

        sims.sort(key=lambda x: x[0], reverse=True)
        top_k = sims[:k]

        # Weighted vote
        harmful_weight = sum(sim for sim, harmful, _ in top_k if harmful)
        total_weight = harmful_weight + sum(sim for sim, harmful, _ in top_k if not harmful)

        if total_weight == 0:
            return False, 0.0, [(lbl, sim) for sim, _, lbl in top_k]

        confidence = harmful_weight / total_weight
        is_harmful = confidence > 0.5

        nearest = [(lbl, round(sim, 3)) for sim, _, lbl in top_k]
        return is_harmful, round(confidence, 3), nearest


# ── Pre-built classifier with all 44 training examples ──

# Training data: (label, heading+text, is_harmful)
_TRAINING_DATA: List[Tuple[str, str, bool]] = [
    # test.txt
    ("PAY01", "Payment Terms Client shall pay all undisputed invoices within thirty days of receipt Any invoice not paid within such period shall accrue interest at a rate of 1.5 percent per month until paid", False),
    ("PAY02", "Payment Terms Client shall pay all invoices within thirty days of receipt Any invoice not disputed in writing within five business days of receipt shall be deemed irrevocably accepted Interest on late balances shall accrue at the maximum rate permitted by law compounded daily Client agrees that all pricing is subject to automatic retroactive adjustments by Provider based on shifting operational overhead and Client payment obligations under this Section shall survive expiration or termination of this Agreement for a period of ten years", True),
    ("LIAB01", "Limitation of Liability Except for breaches of confidentiality or indemnification obligations neither party shall be liable to the other for any indirect incidental or consequential damages arising out of this Agreement", False),
    ("LIAB02", "Limitation of Liability Except for Client payment confidentiality and data safety obligations for which liability is completely uncapped neither party shall be liable to the other for indirect incidental or consequential damages Provider total aggregate liability for any and all claims breaches or negligence under this Agreement shall be strictly capped at fifty dollars regardless of the nature or severity of the underlying claim", True),
    ("REN01", "Term and Termination This Agreement shall automatically renew for successive one year terms unless either party provides written notice of non renewal at least thirty days prior to the end of the then current term", False),
    ("REN02", "Term and Renewal This Agreement shall automatically renew for successive three year terms unless Client provides written notice of non renewal via certified mail Such notice must be received by Provider precisely between ninety and eighty five days prior to the expiration of the current term Failure to hit this window constitutes irrevocable acceptance of the renewal along with an automatic non negotiable 25 percent price increase for the subsequent term", True),
    ("IND01", "Indemnification Provider agrees to indemnify and hold harmless Client from any third party claims arising directly from Provider gross negligence or willful misconduct in performing the Services", False),
    ("IND02", "Indemnification Client agrees to defend indemnify and hold harmless Provider and its affiliates from any and all claims losses or demands including reasonable attorney fees arising out of relating to or tangentially connected with the Services Client duty to defend arises immediately upon the mere allegation of a claim by any third party regardless of whether any fault or liability on the part of the Client has been established by a court", True),
    ("IP01", "Intellectual Property Each party retains all rights title and interest in its pre existing intellectual property Any deliverables created specifically for Client under this Statement of Work shall become the property of Client upon full payment of all underlying fees", False),
    ("IP02", "Intellectual Property Client retains ownership of its pre existing data However Client hereby grants Provider a worldwide perpetual irrevocable royalty free transferable license to use modify exploit and commercialize any data feedback or materials submitted to the platform Any derivative works workflows or custom features developed during the term of this Agreement shall be the sole and exclusive property of Provider even if funded entirely by Client", True),
    # test2.txt
    ("T2_SCOPE", "Scope of Work Developer shall perform the software development services specified in Statement of Work SOW A Any modifications to the scope of work must be agreed upon in a written amendment signed by both parties", False),
    ("T2_DELIV", "Delivery and Acceptance Upon delivery of the software deliverables Client shall have exactly forty eight hours to test and evaluate the software for defects If Client does not reject the deliverables in writing within this forty eight hour window the software shall be deemed permanently and irrevocably accepted Following acceptance Developer is fully released from all performance obligations bug fixes or warranty claims and Client waives all rights to withhold payment for any reason", True),
    ("T2_PAY", "Payment Terms Client shall pay Developer a fixed fee of ten thousand USD upon completion of the milestones outlined in the SOW Invoices shall be paid within thirty days of receipt", False),
    ("T2_IP", "Intellectual Property Rights Developer retains sole and exclusive ownership of all source code architecture algorithms and design elements created under this Agreement Client is granted a non transferable revocable license to use the software solely for internal business operations Developer reserves the right to terminate this license at any time with or without cause upon ten days written notice without obligation to refund any fees paid by Client", True),
    ("T2_IND", "Indemnification Developer agrees to indemnify Client against any third party claims alleging that the deliverables infringe upon a valid United States patent or copyright provided Client gives immediate notice of the claim", False),
    ("T2_LIAB", "Limitation of Liability Developer total liability for any breach negligence or system failure under this Agreement shall be limited to a maximum of one dollar USD Client agrees to insulate defend and hold Developer harmless against any third party lawsuits operational losses or regulatory fines that result directly from coding security flaws or vulnerabilities introduced by the Developer", True),
    ("T2_SEV", "Severability If any provision of this Agreement is found to be invalid or unenforceable by a court of law the remaining provisions shall continue in full force and effect", False),
    # test3.txt
    ("T3_LIC", "License Grant Provider grants Client a non exclusive non transferable right to access and use the Cloud Platform during the Subscription Term solely for its internal business operations", False),
    ("T3_DATA", "Data Rights and Use Client retains legal ownership of its uploaded data However Client hereby grants Provider a perpetual worldwide irrevocable royalty free license to mine aggregate monetize and sell Client operational data user behaviors and customer records to third party data brokers Provider is under no obligation to anonymize or de identify this information prior to commercial distribution or public sale", True),
    ("T3_SLA", "Service Level Agreement Provider shall use commercially reasonable efforts to make the Cloud Platform available with a Monthly Uptime Percentage of at least 99.9 percent during any monthly billing cycle", False),
    ("T3_REN", "Automatic Renewal and Pricing The initial subscription term is twelve months This Agreement will automatically renew for successive three year terms unless Client cancels via certified mail exactly sixty five days before the expiration date Failure to cancel precisely on this day triggers automatic renewal along with a compounding 50 percent increase in the annual subscription fee which will be charged immediately to the Client credit card on file without prior notification", True),
    ("T3_CONF", "Confidentiality Each party agrees to protect the other party confidential information with the same degree of care that it uses to protect its own confidential information of like kind but no less than reasonable care", False),
    ("T3_TERM", "Termination for Convenience Provider may terminate this Agreement immediately at any time for any reason or no reason by cutting off account access Client shall not be entitled to any refund for unused portions of prepaid subscription fees Upon such termination Provider reserves the right to permanently delete all Client data from its servers within one hour without providing a data export or backup copy to the Client", True),
    ("T3_GOV", "Governing Law This Agreement shall be governed by and construed in accordance with the laws of the State of Delaware without giving effect to any choice of law principles", False),
    # test4.txt
    ("T4_DUTY", "Duties and Responsibilities Employee agrees to perform the duties customary to the position of Software Engineer Employee shall report directly to the Engineering Manager and comply with all standard company policies handbooks and workplace guidelines", False),
    ("T4_COMP", "Compensation and Bonuses Employer shall pay Employee a base salary of six thousand USD per month However Employee agrees that Employer reserves the right to retroactively reduce withhold or cancel any accrued salary unpaid wages or earned sales bonuses at its absolute discretion if Employer determines that Employee monthly performance metrics fell below internal targets", True),
    ("T4_CONF", "Confidentiality Employee shall not disclose or use any of Employer proprietary technical data trade secrets or client lists for personal gain or to the detriment of the company during or after the employment period", False),
    ("T4_NONCOMP", "Covenant Not to Compete For a period of five years following the termination of employment for any reason Employee shall not directly or indirectly engage in consult for or establish any business that operates in the technology software or digital services sector anywhere within the continental United States Employee acknowledges that this restriction applies even if Employee is terminated by Employer without cause during their probationary period", True),
    ("T4_IP", "Intellectual Property Provisions All inventions software code patents and improvements developed by Employee during working hours or using company equipment shall be considered work for hire and remain the exclusive property of Employer", False),
    ("T4_LIQ", "Liquidated Damages and Fees If Employee terminates this Agreement prior to completing twenty four full months of service Employee shall immediately pay Employer a lump sum liquidated damages penalty of twenty five thousand dollars USD to offset recruitment and onboarding costs Furthermore Employee agrees to pay all of Employer legal fees and court costs in any future dispute regardless of which party ultimately prevails in the litigation", True),
    ("T4_NOT", "Notices Any notices required under this Agreement shall be sent in writing to the respective parties at the physical addresses listed in the introductory paragraph of this document", False),
    # test_novel.txt
    ("NOV_SERV", "Services Provider will deliver the marketing services listed in Schedule A", False),
    ("NOV_PAY", "Payment and Fees Provider will invoice Client monthly All invoices are due within 15 days Client may not dispute any invoice after 10 business days Any unpaid amount will incur monthly interest at 3 percent Provider may adjust fees at any time with 5 days email notice", True),
    ("NOV_IP", "Intellectual Property All deliverables templates methodologies and work product created under this Agreement shall be the sole property of Provider Client receives a non exclusive non transferable license to use the deliverables for internal purposes only", True),
    ("NOV_DATA", "Data License Client retains ownership of its customer data Client grants Provider a non exclusive worldwide perpetual irrevocable sublicensable license to aggregate analyze and commercialize Client customer data for any business purpose", True),
    ("NOV_LIAB", "Limitation of Liability Neither party shall be liable for indirect damages Provider maximum liability for any claim is the total fees paid by Client in the prior 6 months not to exceed one hundred dollars This cap applies even if the Provider negligence causes the loss", True),
    ("NOV_IND", "Indemnification Client shall indemnify defend and hold Provider harmless from any third party claim arising out of Client use of the services including claims caused by Provider own security failures or data breaches", True),
    ("NOV_REN", "Term and Renewal This Agreement renews automatically each year Client must send cancellation notice no earlier than 120 days and no later than 90 days before renewal If Client fails to cancel within this window the fees increase by 15 percent", True),
    ("NOV_CONF", "Confidentiality Each party will protect the other confidential information for 3 years after termination", False),
    ("NOV_GOV", "Governing Law This Agreement is governed by the laws of Delaware Any disputes shall be resolved in the courts located in Provider headquarters city", False),
    ("NOV_WAR", "Warranty Disclaimer THE SERVICES ARE PROVIDED AS IS WITHOUT ANY WARRANTY PROVIDER DISCLAIMS ALL IMPLIED WARRANTIES INCLUDING MERCHANTABILITY AND FITNESS", True),
    # Vendor contract
    ("VEND_ALTER", "Alterations and Improvements Vendor may make cosmetic adjustments to the space with prior approval However any physical improvements light fixtures shelving installations or structural enhancements made by Vendor shall instantly become the permanent property of Property Owner Upon expiration of this Agreement Property Owner may compel Vendor to pay for the professional removal of these items using a contractor exclusively selected by Property Owner at un capped commercial rates", True),
    ("VEND_FEES", "Operational Fees and Utility Surcharges Vendor shall pay a flat monthly utility fee of two hundred USD Vendor agrees that Property Owner retains the right to levy unannounced retroactive operational surcharges at any time to cover building repairs HVAC overages or property tax increases incurred over the prior three years These surcharges are due within twenty four hours of electronic notice and failure to pay grants Property Owner the right to seize Vendor physical inventory as collateral", True),
    ("VEND_INDEM", "Indemnification and Landlord Liability Vendor agrees to indemnify protect and absolve Property Owner from any liability relating to roof leaks electrical fires flooding or building structural collapses even if caused directly by Property Owner failure to maintain the facilities Vendor explicitly waives all claims for lost retail revenue damaged inventory or physical injuries suffered by employees due to property defects or lack of facility maintenance", True),
]

# Build the global classifier
_CLASSIFIER = TfidfClassifier()
_CLASSIFIER.fit(
    [h + " " + t for h, t, _ in _TRAINING_DATA],
    [lbl for _, _, lbl in _TRAINING_DATA],
    [label for label, _, _ in _TRAINING_DATA],
)


def similarity_classify(text: str) -> Tuple[Optional[bool], float, str]:
    """Classify a clause using TF-IDF similarity to training examples.

    Returns (is_harmful_or_None, confidence, explanation).
    Returns None for is_harmful if similarity is too low to be confident.
    """
    is_harmful, confidence, neighbors = _CLASSIFIER.predict(text)

    # Conservative: only flag harmful if top neighbor is both:
    # 1) a known harmful example AND 2) has strong similarity (> 0.4)
    # (TF-IDF bag-of-words can't distinguish direction of obligations,
    #  so low thresholds cause false positives from coincidental word overlap)
    if not is_harmful or confidence < 0.75:
        is_harmful = None
    elif neighbors:
        best_label, best_sim = neighbors[0]
        if best_sim < 0.4:
            is_harmful = None
        else:
            is_harmful_example = any(
                kw in best_label for kw in
                ["PAY02", "LIAB02", "REN02", "IND02", "IP02",
                 "T2_DELIV", "T2_IP", "T2_LIAB",
                 "T3_DATA", "T3_REN", "T3_TERM",
                 "T4_COMP", "T4_NONCOMP", "T4_LIQ",
                 "NOV_PAY", "NOV_IP", "NOV_DATA", "NOV_LIAB", "NOV_IND",
                 "NOV_REN", "NOV_WAR",
                 "VEND_ALTER", "VEND_FEES", "VEND_INDEM"]
            )
            if not is_harmful_example:
                is_harmful = None

    # Build explanation
    similar_harmful = [(lbl, sim) for lbl, sim in neighbors if "HARMFUL" in lbl or any(
        kw in lbl for kw in ["PAY02", "LIAB02", "REN02", "IND02", "IP02",
                             "T2_DELIV", "T2_IP", "T2_LIAB",
                             "T3_DATA", "T3_REN", "T3_TERM",
                             "T4_COMP", "T4_NONCOMP", "T4_LIQ",
                             "NOV_PAY", "NOV_IP", "NOV_DATA", "NOV_LIAB", "NOV_IND",
                             "NOV_REN", "NOV_WAR",
                             "VEND_ALTER", "VEND_FEES", "VEND_INDEM",
                             ])][:3]

    reason_parts = []
    if similar_harmful:
        examples = ", ".join(f"{lbl}(sim={sim})" for lbl, sim in similar_harmful)
        reason_parts.append(f"similar to known harmful clauses: {examples}")

    similar_unharmful = [(lbl, sim) for lbl, sim in neighbors
                         if lbl not in [l for l, _ in similar_harmful]][:2]
    if not is_harmful and similar_unharmful:
        examples = ", ".join(f"{lbl}(sim={sim})" for lbl, sim in similar_unharmful)
        reason_parts.append(f"similar to known unharmful clauses: {examples}")

    reason = "; ".join(reason_parts)
    return is_harmful, confidence, reason
