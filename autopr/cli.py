"""CLI entry point."""
import asyncio
import os
import sys

import click
from dotenv import load_dotenv

load_dotenv()


@click.group()
def main():
    """AutoPR — autonomous bounty PR agent."""


@main.command()
@click.option("--once", is_flag=True, help="Run one cycle and exit")
def run(once):
    """Start the agent loop (and dashboard)."""
    if once:
        from autopr.memory import init_db
        from autopr.agent_loop import run_one
        init_db()
        asyncio.run(run_one())
    else:
        import main as m
        asyncio.run(m._main())


@main.command()
def stats():
    """Show current stats."""
    from autopr.memory import init_db, stats as _stats, recent_attempts
    init_db()
    s = _stats()
    click.echo(f"\n{'═'*50}")
    click.echo(f"  AutoPR Stats")
    click.echo(f"{'═'*50}")
    click.echo(f"  Total attempts : {s['total_attempts']}")
    click.echo(f"  Total earned   : ${s['total_earned']:.2f}")
    for status, d in s.get("by_status", {}).items():
        click.echo(f"  {status:<14}: {d['count']}")
    click.echo(f"{'─'*50}")
    recent = recent_attempts(5)
    if recent:
        click.echo("  Recent:")
        for a in recent:
            click.echo(f"    {a['ts'][:16]}  {a['status']:<12}  {a['repo']}#{a['issue']}")
    click.echo()


@main.command()
@click.argument("repo")
@click.argument("issue_number", type=int)
def try_issue(repo, issue_number):
    """Manually try a specific issue."""
    from autopr.memory import init_db
    from autopr.scanner import fetch_issue_body
    from autopr.models import BountyIssue
    from autopr.coder import fix_issue
    from autopr.pr_submitter import submit

    init_db()
    body = fetch_issue_body(repo, issue_number)
    issue = BountyIssue(
        source="manual", repo=repo, issue_number=issue_number,
        title=f"#{issue_number}", body=body,
        url=f"https://github.com/{repo}/issues/{issue_number}",
        amount_usd=0,
    )

    def on_event(msg):
        click.echo(f"  {msg}")

    result = asyncio.run(fix_issue(issue, on_event=on_event))
    click.echo(f"\nResult: {result}")

    if result.success:
        pr = submit(issue, result)
        click.echo(f"PR: {pr}")
