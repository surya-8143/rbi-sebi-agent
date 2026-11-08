# Corpus status

Official documents ingested: 0. The manifest is an empty, schema-complete CSV. No official PDF content is redistributed. The planned 60–80-document corpus, at least eight topics, and six amendment pairs remain to be collected and inspected.

The included software corpus has ten fictional FRA circulars, including a deposit-notice amendment. Each has a preamble and two numbered provisions on one page. It yields 30 source chunks. Twenty answerable questions and three refusal questions exercise the pipeline. Five separate fictional poisoned documents produce the attack corpus. These documents are not RBI or SEBI rules.

The parser removes repeated margin lines while retaining recurring obligations in the body. It dehyphenates lowercase line-break words and keeps one-based page numbers. The chunker flushes at sections and pages, preserves short provisions, and hard-splits oversized lines below 2,800 characters including metadata. These choices make citation pages unambiguous but can separate a provision that spans pages.

Ingestion writes per-document page JSONL, combined chunks, checksums, page counts, and a JSON quality report with short-page flags. Existing nonempty hashes must match. After adding real PDFs, inspect 30 random chunks and all flagged documents. Table extraction, multi-column reading order, and amendments require particular attention. OCR and automatic legal supersession are outside the current implementation.
