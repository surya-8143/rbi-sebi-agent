import json

import pytest

from src.agent.tools import ToolSet, calculate


@pytest.mark.parametrize("expression,value", [("100*.25", 25), ('days_between("2025-01-01","2025-03-31")', 89),
                                              ("round(10/3,2)", 3.33), ("max(3,8)", 8), ("-4+2", -2)])
def test_calculate(expression, value):
    assert calculate(expression) == {"result": value}


@pytest.mark.parametrize("expression", ["__import__('os').system('id')", "9**9**9", "1/0", "[1]*9999999", "1e309", "True", '"a"*100', "round(1,999999999)", "1+" * 200])
def test_calculator_rejects_unsafe_expressions(expression):
    assert "error" in calculate(expression)


@pytest.mark.parametrize("name,args", [("get_section", {"doc_id": "../../etc/passwd", "section": "1"}),
                                       ("get_section", {"doc_id": "fra_kyc", "section": "../"}),
                                       ("search_circulars", {"query": "KYC", "top_k": 100}),
                                       ("search_circulars", {"query": "KYC", "issuer": "BAD"}),
                                       ("calculate", {"expression": "1", "extra": 1})])
def test_invalid_tool_args(searcher, name, args):
    result, _ = ToolSet(searcher).run(name, json.dumps(args))
    assert "error" in result


def test_unknown_and_malformed_tools(searcher):
    tools = ToolSet(searcher)
    assert "error" in tools.run("shell", "{}")[0]
    assert "error" in tools.run("calculate", "{")[0]
    result, _ = tools.run("search_circulars", '{"query":"KYC","top_k":2}')
    assert len(result) <= 2


def test_section_metadata_and_no_global_state(searcher):
    tools = ToolSet(searcher)
    result, _ = tools.run("get_section", '{"doc_id":"fra_kyc","section":"1"}')
    assert result[0]["doc_id"] == "fra_kyc"
    assert result[0]["page"] == 1
