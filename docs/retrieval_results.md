# Fictional retrieval experiment

Measured on the 20 answerable dev questions from the ten-document fictional FRA corpus. These results do not estimate performance on RBI/SEBI PDFs.

| Setup | Recall@5 | MRR | Median retrieval seconds |
| --- | --- | --- | --- |
| BM25 | 19/20 (95%) | 0.6350 | 0.00046 |
| BGE dense | 20/20 (100%) | 0.7767 | 0.0549 |
| BM25 + BGE fusion | 20/20 (100%) | 0.7458 | 0.0619 |
| Fusion + BGE reranker | 20/20 (100%) | 0.6375 | 2.8382 |

The reranker did not improve recall on this small fixture set. Its MRR was lower than dense retrieval and plain fusion, and it added CPU latency. It therefore remains optional. This is a measured engineering observation about synthetic inputs, not evidence that reranking is generally harmful.

The complete per-question ranks, all-gold@5 values, and source hash are saved in results/fixture_hybrid_retrieval.json. BM25's top-5 miss remains in that result; the dataset was not rewritten to erase it. Real-source ablations and error analysis remain pending.
