"""Unit tests for the Slack mention parser."""
from slack_app.parse import parse_request


def test_shorthand_with_task():
    req = parse_request("<@U123> fix owner/repo#42 the CSV parser crashes on empty input")
    assert req is not None
    assert req.repo == "owner/repo"
    assert req.issue_number == 42
    assert "CSV parser crashes" in req.task
    assert req.task.lower().split()[0] != "fix"  # filler stripped


def test_github_issue_url():
    req = parse_request("<@U1> https://github.com/acme/widget/issues/7 please fix")
    assert req is not None
    assert req.repo == "acme/widget"
    assert req.issue_number == 7


def test_github_pull_url():
    req = parse_request("look at github.com/acme/widget/pull/9 and address review")
    assert req is not None
    assert req.repo == "acme/widget"
    assert req.issue_number == 9
    assert "address review" in req.task


def test_repo_only_no_issue():
    req = parse_request("<@U1> owner/repo make the build badge link to CI")
    assert req is not None
    assert req.repo == "owner/repo"
    assert req.issue_number == 0
    assert "build badge" in req.task


def test_empty_task_gets_default():
    req = parse_request("<@U1> owner/repo#5")
    assert req is not None
    assert req.task == "Fix issue #5"


def test_plain_repo_url_without_issue():
    req = parse_request("<@U1> https://github.com/octocat/Hello-World please fix the readme")
    assert req is not None
    assert req.repo == "octocat/Hello-World"
    assert req.issue_number == 0
    assert "readme" in req.task  # URL residue scrubbed; "please fix" filler stripped


def test_repo_url_with_extra_path():
    req = parse_request("fix github.com/octocat/Hello-World/tree/main typo")
    assert req is not None
    assert req.repo == "octocat/Hello-World"


def test_slack_autolinked_url_residue_is_scrubbed():
    req = parse_request("<@U1> <https://github.com/octocat/Hello-World> fix the bug")
    assert req is not None
    assert req.repo == "octocat/Hello-World"
    assert all(c not in req.task for c in "<>|")
    assert "github.com" not in req.task and "https" not in req.task
    assert "bug" in req.task


def test_no_repo_returns_none():
    assert parse_request("<@U1> hello what can you do?") is None


def test_empty_text_returns_none():
    assert parse_request("") is None
