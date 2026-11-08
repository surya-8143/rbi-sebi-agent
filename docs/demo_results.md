# Executed local model smoke test

Model: qwen3:4b. Runtime: local Ollama, 100% CPU. Sources: fictional FRA fixture corpus. There are three cases, with only one answerable case. This sample is far too small for a model-quality claim.

The KYC record-retention question was answered correctly with a valid exact source quote and gold-evidence support. It took 237.7 seconds end to end. The unrelated cooking request was blocked as out_of_scope in 2.57 seconds. A request about an unknown circular was refused as unknown_reference without a model call.

The initial run incorrectly rejected an in-scope question. A later structured-gate run hit a 120-second local request timeout on the answer case; its result is preserved in results/fixture_model_smoke.json. After bounding response lengths and allowing 240 seconds per CPU request, the next three-case run completed without operational errors and is saved in results/fixture_model_smoke_v2.json.

The median over this mixed three-case set is dominated by easy refusals and must not be presented as typical answer-generation latency. The answer case itself took almost four minutes. GPU performance has not been measured.
