"""Hermetic tests for the Slack Block Kit builders."""
from slack_app import blocks


def _sample(diff: str = "- old\n+ new") -> dict:
    return {
        "session_id": "sess123", "repo": "o/r",
        "changed_files": ["a.py", "b.py"], "commit_message": "fix: thing",
        "diff": diff, "elapsed_s": 3.2, "tool_calls": 7,
    }


def _actions(blocks_list: list) -> list:
    return [e for b in blocks_list if b["type"] == "actions" for e in b["elements"]]


def test_preview_has_open_pr_and_discard_buttons_with_session_value():
    out = blocks.preview_blocks(_sample())
    actions = _actions(out)
    by_id = {e["action_id"]: e for e in actions}
    assert set(by_id) == {"open_pr", "discard"}
    assert by_id["open_pr"]["value"] == "sess123"
    assert by_id["discard"]["value"] == "sess123"


def test_preview_includes_commit_and_changed_files():
    text = str(blocks.preview_blocks(_sample()))
    assert "fix: thing" in text
    assert "a.py" in text and "b.py" in text


def test_preview_truncates_long_diff():
    out = blocks.preview_blocks(_sample(diff="x" * 5000))
    text = str(out)
    assert "… (truncated)" in text
    # the diff section stays within Slack's 3000-char section limit
    diff_sections = [b for b in out if b["type"] == "section"
                     and "```" in b.get("text", {}).get("text", "")]
    assert diff_sections and len(diff_sections[0]["text"]["text"]) <= 3000


def test_pr_opened_includes_url():
    assert "http://x/pr/1" in str(blocks.pr_opened_blocks("http://x/pr/1"))


def test_error_blocks_truncate_to_500():
    out = blocks.error_blocks("E" * 1000)
    assert len(out[0]["text"]["text"]) < 600  # message capped at 500 + label


def test_usage_blocks_is_a_section():
    out = blocks.usage_blocks()
    assert out and out[0]["type"] == "section"
