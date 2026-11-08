# Evaluation protocol

The official benchmark is pending source collection and human verification. The shipped fixture corpus tests software behavior and is explicitly synthetic. Do not report its accuracy as regulatory accuracy.

Official question allocation (dev / test): single fact 16/14; multi-section 10/10; numeric/date 8/7; cross-document 6/4; unanswerable 6/14; out-of-scope 2/8; version conflict 2/13. Total 50/70. The plan's prose says about 35 answerable test cases, but its category table actually has 48 answerable and 22 refusal test cases; this implementation follows the table.

Each answerable label needs a source document, one-based page, exact evidence of at most 12 words, a reference answer, acceptable key-fact variants, and forbidden facts where applicable. At least 15 test labels should be independently reviewed. Mark labels verified only after reading the source. Freeze the test file and record its hash before tuning. Label corrections require a dated log and re-scoring all saved runs.

Use dev only for retrieval settings, prompt changes, and threshold calibration. Evaluate test at predeclared milestones. The runner records the question and corpus hashes, prompt hash, configuration, model, Python version, Git SHA, timestamp, and trace IDs. Resume requires an identical fingerprint. A failed inference is an error and cannot improve refusal performance.

Strict key-fact accuracy requires every fact and no forbidden fact. Matching ignores case, commas, and repeated whitespace but enforces word boundaries; 130 days cannot satisfy 30 days. Partial accuracy is the fraction of facts matched. This deterministic measure can miss valid paraphrases and should be interpreted alongside manual review.

Citation validity means each answered claim has a citation to a retrieved chunk and an exact short quote from the delivered evidence. Citation support means at least one citation matches gold document, page, and evidence. Gold coverage separately measures how much multi-passage evidence is covered. Neither exact citation validation nor one gold hit establishes that every claim is entailed.

Correct refusal uses only designated refusal cases. False refusal uses only answerable cases. Operational errors are a separate metric. Every binary rate has its numerator, denominator, and 95% Wilson interval; zero denominators produce null, never 0% or 100%. Median and nearest-rank p95 latency, token counts, and tool calls are recorded separately. Token counts include the gate and finalization retries when calls succeed.

Retrieval ablation measures BM25, dense, fusion, and optional reranking independently. Recall means at least one gold passage retrieved; all-gold@5 is also reported to expose incomplete multi-document retrieval. Gold page numbers are enforced. Test fixture recall is not evidence of semantic retrieval quality on official PDFs.

LLM judging is optional and secondary. The judge prompt is provided, and Cohen kappa can be computed with evals.calibrate.cohen_kappa. No judge labels or calibration result are supplied. If used, collect 40 blinded human judgments, align IDs, calculate agreement, and report same-model-family bias. Do not invent a kappa value.

The regression gate recomputes recorded metrics from per-question rows. It refuses mismatched datasets, source corpora, IDs, missing denominators, or operational errors. Its default tolerance is three percentage points, including a check for increased false refusal. It trusts saved rows and does not prove that an LLM run occurred. Publish raw sanitized traces or audit samples to strengthen provenance.
