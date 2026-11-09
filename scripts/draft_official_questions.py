"""Materialize source-grounded draft labels. This never marks labels verified."""
from evals.schema import validate_questions
from src.agent.verify import normalized as normalize
from src.io import read_jsonl, write_jsonl

# Each quote was selected from a local official source. Human review is outstanding.
SPECS = [
    ("single_fact", "Under the RBI commercial-bank KYC Directions captured in November 2026, what is the minimum retention period for transaction records, measured from the transaction?", "At least five years from the transaction date.", [["five years", "5 years"]], [("rbi_md_13141", "at least five years from the date of transaction")]),
    ("single_fact", "Under RBI's 2026 commercial-bank Internal Ombudsman Directions, what age must an Internal Ombudsman not exceed before completing the tenure?", "The IO must not be over 70 years before completing the tenure.", [["70", "seventy"]], [("rbi_md_13271", "not be over 70 years of age")]),
    ("single_fact", "What minimum relevant experience does RBI's 2026 commercial-bank Internal Ombudsman framework require for an IO?", "A minimum of seven years of relevant experience.", [["seven years", "7 years"]], [("rbi_md_13271", "minimum seven years of working")]),
    ("single_fact", "Who approves a commercial bank's KYC policy under paragraph 6 of the RBI KYC Directions?", "The Board of Directors or a committee to which it delegates that power.", [["board"], ["committee"]], [("rbi_md_13141", "The Board of Directors of the bank"), ("rbi_md_13141", "any committee to which the Board has delegated power")]),
    ("single_fact", "Does the RBI commercial-bank KYC framework permit an account in an anonymous or fictitious name?", "No. Accounts in anonymous or fictitious/benami names must not be opened.", [["not", "no"], ["anonymous", "fictitious"]], [("rbi_md_13141", "any account in an anonymous or fictitious / benami name")]),
    ("single_fact", "For a joint account, whose customer due diligence is required under the commercial-bank KYC Directions?", "CDD is required for all joint account holders.", [["all"], ["joint"]], [("rbi_md_13141", "follow the CDD Procedure for all the joint account holders")]),
    ("single_fact", "Under RBI's commercial-bank credit information reporting Directions, must a credit institution insist on borrower consent merely to share credit information with a CIC?", "No. CICRA provides statutory backing and the consent clause is redundant.", [["no", "not"], ["CICRA", "statutory"]], [("rbi_md_13154", "the requirement of a ‘consent clause’ has become redundant")]),
    ("single_fact", "How often must the Audit Committee review a commercial bank's credit-card operations under the RBI card Directions?", "On a half-yearly basis.", [["half-yearly", "six months", "semiannual"]], [("rbi_md_13155", "review of their credit card operations on half-yearly basis")]),
    ("single_fact", "According to the February 2026 SEBI Research Analyst master circular FAQ, when does an RA registration certificate cease to remain valid?", "It remains valid until suspended or cancelled, subject to applicable fee payments.", [["suspended"], ["cancelled", "canceled"]], [("sebi_md_99571", "remains valid till it is suspended or cancelled")]),
    ("single_fact", "In SEBI's July 2025 ESG-rating-provider master circular, what cooling period applies when switching a client group between ESG ratings and audit/assurance services?", "A one-year cooling period applies.", [["one year", "1 year", "one-year"]], [("sebi_md_95219", "a cooling period of one year shall be applicable")]),
    ("single_fact", "What minimum financial-sector experience must an ESG rating provider's internal audit firm have under SEBI's July 2025 master circular?", "At least three years.", [["three years", "3 years"]], [("sebi_md_95219", "a minimum experience of three years in the financial sector")]),
    ("single_fact", "Under the May 2024 SEBI debenture-trustee master circular, how frequently must the issuer prepare its security-cover certificate?", "Quarterly; its statutory auditor certifies the asset book values.", [["quarterly"]], [("sebi_mc_dt_2024", "prepare the security cover certificate on quarterly basis")]),
    ("single_fact", "What type of product plans should investment advisers recommend wherever available under SEBI's February 2026 master circular?", "Direct, non-commission-based plans.", [["direct"], ["non-commission", "no commission"]], [("sebi_md_99569", "advise direct plans (non-commission based) of products only")]),
    ("single_fact", "What languages does the SEBI ICDR master circular updated in February 2026 initially require for public-issue audio-visual disclosures?", "English and Hindi; Hindi text uses Devanagari.", [["English"], ["Hindi"]], [("sebi_md_99611", "initially be in bilingual format i.e. English and Hindi")]),
    ("numeric_date", "Under paragraph 19 of RBI's commercial-bank card Directions, what is the closure deadline once all dues are paid?", "Seven working days.", [["seven working days", "7 working days"]], [("rbi_md_13155", "honoured within seven working days")]),
    ("numeric_date", "A credit-card account with no outstanding balance remains open three calendar days beyond RBI's permitted closure deadline. At the stated daily penalty, what amount is payable?", "Rs 1,500, calculated as Rs 500 multiplied by three calendar days.", [["1500", "1,500"]], [("rbi_md_13155", "a penalty of ₹500 per calendar day of delay")]),
    ("numeric_date", "What annual fixed-fee ceiling per family does SEBI's February 2026 investment-adviser master circular specify, before future revisions?", "Rs 1,51,000 per annum per family of client.", [["151000", "1,51,000"]], [("sebi_md_99569", "shall not exceed ₹1,51,000 per annum per family of client")]),
    ("numeric_date", "What deadline does the captured RBI KYC Directions specify for furnishing newly obtained updated customer information to CKYCR, unless the Central Government notifies another period?", "Within seven days, or the period notified by the Central Government.", [["seven days", "7 days"]], [("rbi_md_13141", "within seven days or within such period as may be notified")]),
    ("multi_section", "Under RBI's 2026 commercial-bank Internal Ombudsman Directions, compare the minimum relevant experience for the IO and Deputy IO.", "The IO needs seven years and the Deputy IO five years.", [["seven", "7"], ["five", "5"]], [("rbi_md_13271", "minimum seven years of working"), ("rbi_md_13271", "minimum five years of working")]),
    ("multi_section", "Under the RBI commercial-bank KYC Directions, compare the retention clocks for transaction records and customer identification records.", "Transaction records: at least five years from the transaction. Identification records: at least five years after the business relationship ends.", [["five years", "5 years"], ["transaction"], ["relationship"]], [("rbi_md_13141", "at least five years from the date of transaction"), ("rbi_md_13141", "at least five years after the business relationship has ended")]),
    ("multi_section", "Under the RBI commercial-bank KYC Directions, what are the aggregate balance and annual-credit limits for deposit accounts opened with Aadhaar OTP e-KYC in non-face-to-face mode?", "Aggregate balance: Rs one lakh. Aggregate credits in a financial year: Rs two lakh.", [["one lakh", "1 lakh", "100000"], ["two lakh", "2 lakh", "200000"]], [("rbi_md_13141", "shall not exceed Rupees One Lakh"), ("rbi_md_13141", "shall not exceed Rupees Two Lakh")]),
    ("multi_section", "What are the maximum auditor appointment term and subsequent cooling-off period for an ESG rating provider under SEBI's July 2025 master circular?", "Maximum five-year term, followed by two years of cooling off.", [["five years", "five-year", "5 years"], ["two years", "2 years"]], [("sebi_md_95219", "a maximum term of five years"), ("sebi_md_95219", "a cooling-off period of two years")]),
    ("multi_section", "Under RBI's commercial-bank credit information reporting Directions, what daily compensation applies after an unresolved correction complaint passes the overall resolution period, and how long is that period?", "Rs 100 per calendar day after thirty calendar days from initial filing.", [["100"], ["thirty", "30"], ["calendar"]], [("rbi_md_13154", "a compensation of ₹100 per calendar day"), ("rbi_md_13154", "within a period of thirty calendar days")]),
    ("multi_section", "Under the February 2026 SEBI Research Analyst circular, when must the annual compliance audit be completed and how soon after its report must it be submitted?", "Complete within six months of financial year-end; submit within one month of the audit report.", [["six months", "6 months"], ["one month", "1 month"]], [("sebi_md_99571", "complete the annual compliance audit within six months"), ("sebi_md_99571", "within a period of one month from the date")]),
    ("cross_document", "Compare the minimum transaction-record retention in RBI's commercial-bank KYC Directions with advertisement-copy retention in SEBI's February 2026 Research Analyst master circular.", "Both are five years; the RBI transaction-record period runs from the transaction date.", [["five years", "5 years"], ["transaction"]], [("rbi_md_13141", "at least five years from the date of transaction"), ("sebi_md_99571", "Copy of the advertisement shall be retained by RA")]),
    ("cross_document", "Compare the IO experience requirement for commercial banks with the minimum experience of an ESG rating provider's internal audit firm in the captured RBI and SEBI circulars.", "An IO requires seven years; an ERP audit firm requires three years in the financial sector.", [["seven", "7"], ["three", "3"]], [("rbi_md_13271", "minimum seven years of working"), ("sebi_md_95219", "a minimum experience of three years in the financial sector")]),
    ("version_conflict", "Which older debenture-trustee master circular is listed as superseded in Annexure 1 of SEBI's September 28, 2026 circular?", "The August 13, 2025 master circular, SEBI/HO/DDHS-PoD-1/P/CIR/2025/117.", [["August 13, 2025", "2025-08-13"], ["2025/117"]], [("sebi_md_104743", "August 13, 2025 Master Circular For Debenture")]),
    ("version_conflict", "Which earlier debenture-trustee master circular appears in the superseded list of SEBI's August 13, 2025 master circular?", "The May 16, 2024 master circular.", [["May 16, 2024", "2024-05-16"]], [("sebi_md_96073", "May 16, 2024 Master Circular For Debenture")]),
    ("version_conflict", "Which earlier investment-adviser master circular does SEBI's June 27, 2025 circular explicitly supersede?", "The May 21, 2024 master circular for Investment Advisers.", [["May 21, 2024", "2024-05-21"]], [("sebi_md_94821", "supersedes the Master Circular for IAs dated May 21, 2024")]),
    ("numeric_date", "Under RBI's 2026 commercial-bank Internal Ombudsman Directions, what are the minimum fixed term and maximum total tenure, including extensions?", "At least three years for the fixed term, with total tenure not exceeding five years.", [["three years", "3 years"], ["five years", "5 years"]], [("rbi_md_13271", "fixed term of not less than three years"), ("rbi_md_13271", "shall not exceed five years")]),
]

REFUSALS = [
    ("unanswerable", "What is the private password of the RBI official who signed these circulars?"),
    ("unanswerable", "What is the confidential internal credit score of customer Meera Rao at Example Bank today?"),
    ("unanswerable", "What exact new KYC retention period will RBI announce in December 2031?"),
    ("unanswerable", "Quote paragraph 12 of circular RBI/2031-32/999 about mandatory cryptocurrency deposits."),
    ("unanswerable", "What is the unpublished result of SEBI's next inspection of my investment adviser?"),
    ("unanswerable", "How many complaints did my own bank receive yesterday? Use only this circular corpus."),
    ("out_of_scope", "Give me a recipe for vegetable biryani."),
    ("out_of_scope", "Write a poem about the moon."),
    ("out_of_scope", "Who will win the next football World Cup?"),
    ("out_of_scope", "Explain how to replace a bicycle tyre."),
]


def build(chunks_path="data/processed/chunks.jsonl", out="evals/questions.draft.jsonl"):
    chunks = read_jsonl(chunks_path)
    rows = []
    for category, question, answer, facts, evidence in SPECS:
        gold = []
        for doc_id, quote in evidence:
            matches = [c for c in chunks if c["doc_id"] == doc_id and normalize(quote) in normalize(c["body"])]
            if not matches:
                raise ValueError(f"Draft evidence missing: {doc_id}: {quote}")
            c = matches[0]
            gold.append({"doc_id": doc_id, "pages": [c["page"]] if c["page"] else [],
                         "section_path": c["section_path"], "evidence": quote})
        rows.append({"id": f"draft_{len(rows)+1:03d}", "split": "dev", "category": category,
                     "question": question, "gold_answer": answer, "key_facts": facts,
                     "gold": gold, "must_refuse": False, "label_status": "draft",
                     "notes": "AI-drafted from captured official sources; human verification outstanding. Exploratory dev only; not frozen benchmark evidence."})
    for category, question in REFUSALS:
        rows.append({"id": f"draft_{len(rows)+1:03d}", "split": "dev", "category": category,
                     "question": question, "gold_answer": "Refuse: requested information is absent or outside scope.",
                     "key_facts": [], "gold": [], "must_refuse": True, "label_status": "draft",
                     "notes": "AI draft; refusal categorization requires human review."})
    validate_questions(rows, {c["doc_id"] for c in chunks})
    write_jsonl(out, rows)
    print(f"Wrote {len(rows)} unverified dev drafts; no test labels or verified labels created.")


if __name__ == "__main__":
    build()

