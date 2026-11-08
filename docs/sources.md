# Reference documentation checked during implementation

- Ollama's local chat-completion endpoint supports tool calls, structured output, and reasoning controls: https://docs.ollama.com/api/openai-compatibility
- LangGraph's explicit graph API: https://docs.langchain.com/oss/python/langgraph/graph-api
- Colab runtime and usage rules: https://research.google.com/colaboratory/faq.html
- SEBI master-circular discovery listing: https://www.sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes&sid=1&smid=0&ssid=6
- RBI disclaimer and linking policy (plain text reference): https://www.rbi.org.in/commonman/english/Scripts/Disclaimer.aspx

Official corpus selection must check supersession, not just a recent update date. For example, an RBI KYC master direction updated in August 2025 still appears in search results, while a later November 2025 circular says the old direction was repealed. This is a concrete reason not to seed a purported current regulatory corpus automatically from search snippets.

Discovery evidence, requiring source inspection before labels are created:

RBI Compliance with Know Your Customer norms, 28 November 2025, RBI/2025-26/101:
https://www.rbi.org.in/Scripts/BS_CircularIndexDisplay.aspx?Id=13171

RBI KYC historical Master Direction, updated 14 August 2025:
https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx?id=11566

These references are not imported documents or verified gold labels. No current legal conclusion should be inferred from this engineering note.
