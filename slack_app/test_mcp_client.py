"""Tests for the MCP CallToolResult parser."""
from slack_app.mcp_client import _parse_tool_result


class _Res:
    def __init__(self, structured=None, content=None):
        self.structuredContent = structured
        self.content = content or []


class _Text:
    def __init__(self, text):
        self.text = text


def test_prefers_structured_content():
    assert _parse_tool_result(_Res(structured={"success": True, "x": 1})) == {"success": True, "x": 1}


def test_falls_back_to_json_text():
    r = _Res(content=[_Text('{"success": false, "error": "nope"}')])
    assert _parse_tool_result(r) == {"success": False, "error": "nope"}


def test_non_json_text_becomes_error():
    out = _parse_tool_result(_Res(content=[_Text("not json")]))
    assert out["success"] is False
    assert out["error"] == "not json"


def test_empty_result_is_graceful():
    out = _parse_tool_result(_Res())
    assert out["success"] is False
    assert "empty" in out["error"]
