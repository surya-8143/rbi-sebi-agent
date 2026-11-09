# Local runtime profiles

`Modelfile` reuses the installed `qwen3:4b` weights and changes only the legacy chat template's final thinking prefix. It creates the separate name `rbi-sebi-qwen3:4b`; it does not overwrite the base model. The template is derived from the Qwen3 template distributed by Ollama. Qwen3 model/template terms remain applicable; the project's MIT license does not relicense third-party model assets.

The development experiments exposed runtime-specific problems: thinking text appeared despite the API flag, some nested schemas failed grammar compilation, and other responses contained text after a valid JSON object. Native JSON mode now validates responses locally and records when trailing text is discarded. The custom profile is experimental; consult the committed run configuration for the model actually used in any benchmark.

The optional Qwen2.5 3B fallback has its own Qwen Research License. No model weights are distributed in this repository.

References: https://docs.ollama.com/api/chat ; https://qwenlm.github.io/blog/qwen3/ ; https://ollama.com/library/qwen2.5:3b
