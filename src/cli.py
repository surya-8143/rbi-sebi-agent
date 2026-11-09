import argparse
import json

from src.agent.config import Config
from src.agent.graph import Agent
from src.retrieval.search import Searcher
from src.tracing import save_trace


def main():
    parser = argparse.ArgumentParser(description="Evidence-first RBI/SEBI circular research")
    parser.add_argument("question")
    parser.add_argument("--index", default="index")
    parser.add_argument("--fixture", action="store_true")
    parser.add_argument("--defense", type=int, default=5, choices=range(6))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    agent = Agent(Searcher(args.index), Config.from_env(fixture=args.fixture, defense=args.defense))
    state = agent.invoke(args.question)
    trace = save_trace(state)
    if args.json:
        print(json.dumps(state, indent=2, ensure_ascii=False))
    else:
        print(f"{state['status'].upper()} {state.get('reason', '')}\n{state['answer']['answer']}")
        for c in state["answer"]["citations"]:
            source = state["seen"][c["chunk_id"]]
            locator = f"p.{source['page']}" if source["page"] is not None else f"web section {source['section_path']}"
            print(f"  [{c['chunk_id']}] {locator}: {c['quote']}")
        for source in state["answer"].get("sources", []):
            print(f"  {source['issuer']} | {source['title']} | {source['date_issued']}")
            if source.get("version_date") and source["version_date"] != source["date_issued"]:
                print(f"  Revision: {source['version_date']}")
        print(state["answer"].get("notice", ""))
        print(f"{state['seconds']:.1f}s | {state['tokens']} tokens | trace {trace}")
        if state["status"] == "error":
            print(state.get("error", ""))
    if state["status"] == "error":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
