"""feishu-kit CLI — a rich terminal interface for Feishu Open Platform."""

from __future__ import annotations

import asyncio
import os
from importlib.metadata import version as pkg_version

import typer
from rich.console import Console
from rich.json import JSON
from rich.panel import Panel
from rich.table import Table
from rich.theme import Theme
from rich.tree import Tree

from feishu_kit import FeishuClient
from feishu_kit.modules.md2feishu import Md2FeishuService
from feishu_kit.modules.messaging import MessagingService
from feishu_kit.modules.wiki import WikiService

# ── Theme & Console ─────────────────────────────────────────

feishu_theme = Theme(
    {
        "info": "bold blue",
        "success": "bold green",
        "warning": "bold yellow",
        "error": "bold red",
        "title": "bold cyan",
    }
)

console = Console(theme=feishu_theme)
app = typer.Typer(
    name="feishu-kit",
    help="A modular CLI for Feishu (Lark) Open Platform.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

BANNER = r"""
[bold cyan]
 ███████╗███████╗██╗     ██╗         ██████╗ ██╗  ██╗██╗████████╗
 ██╔════╝██╔════╝██║     ██║         ██╔══██╗██║ ██╔╝██║╚══██╔══╝
 █████╗  █████╗  ██║     ██║         ██████╔╝█████╔╝ ██║   ██║
 ██╔══╝  ██╔══╝  ██║     ██║         ██╔═══╝ ██╔═██╗ ██║   ██║
 ██║     ███████╗███████╗███████╗    ██║     ██║  ██╗██║   ██║
 ╚═╝     ╚══════╝╚══════╝╚══════╝    ╚═╝     ╚═╝  ╚═╝╚═╝   ╚═╝
[/bold cyan]
"""


# ── Helpers ─────────────────────────────────────────────────


def _get_client() -> FeishuClient:
    """Create a FeishuClient from environment variables."""
    app_id = os.environ.get("FEISHU_APP_ID", "")
    app_secret = os.environ.get("FEISHU_APP_SECRET", "")
    if not app_id or not app_secret:
        console.print(
            "[error]Error:[/error] Set FEISHU_APP_ID and FEISHU_APP_SECRET "
            "environment variables first."
        )
        console.print(
            "  [dim]export FEISHU_APP_ID='cli_xxx'[/dim]\n"
            "  [dim]export FEISHU_APP_SECRET='xxx'[/dim]"
        )
        raise typer.Exit(1)
    return FeishuClient(app_id=app_id, app_secret=app_secret)


# ── Commands ────────────────────────────────────────────────


@app.command()
def version() -> None:
    """Print version with ASCII banner."""
    console.print(BANNER)
    ver = pkg_version("feishu-kit")
    console.print(f"  [bold]feishu-kit[/bold] v{ver}")
    console.print("  [dim]https://github.com/HustWolfzzb/feishu-kit[/dim]")


@app.command()
def spaces() -> None:
    """List all knowledge spaces."""

    async def _run() -> None:
        async with _get_client() as client:
            result = await client.request("GET", "/wiki/v2/spaces")
            items = result.get("data", {}).get("items", [])

            table = Table(
                title="Knowledge Spaces",
                show_header=True,
                header_style="bold cyan",
            )
            table.add_column("Name", style="bold")
            table.add_column("Space ID", style="dim")
            table.add_column("Description")

            for item in items:
                table.add_row(
                    item.get("name", ""),
                    item.get("space_id", ""),
                    item.get("description", ""),
                )

            console.print(table)
            console.print(f"[dim]Total: {len(items)} spaces[/dim]")

    asyncio.run(_run())


@app.command()
def nodes(space_id: str) -> None:
    """List nodes in a knowledge space (tree view)."""

    async def _run() -> None:
        async with _get_client() as client:
            wiki = WikiService(client)
            items = await wiki.list_all_nodes(space_id)

            tree = Tree(f"[bold cyan]{space_id}[/bold cyan]")
            for item in items:
                title = item.get("title", "Untitled")
                node_type = item.get("obj_type", "")
                tree.add(f"[bold]{title}[/bold] [dim]({node_type})[/dim]")

            console.print(tree)
            console.print(f"[dim]Total: {len(items)} nodes[/dim]")

    asyncio.run(_run())


@app.command()
def push(
    file: str = typer.Argument(..., help="Markdown file path"),
    space_id: str = typer.Argument(..., help="Target space ID"),
    title: str | None = typer.Option(None, "--title", "-t", help="Document title"),
    parent: str | None = typer.Option(None, "--parent", "-p", help="Parent node token"),
) -> None:
    """Push a Markdown file to Feishu Wiki."""

    async def _run() -> None:
        from pathlib import Path

        path = Path(file)
        if not path.exists():
            console.print(f"[error]Error:[/error] File not found: {file}")
            raise typer.Exit(1)

        markdown = path.read_text(encoding="utf-8")
        doc_title = title or path.stem

        with console.status(f"[bold]Pushing [cyan]{doc_title}[/cyan] to Wiki..."):
            async with _get_client() as client:
                wiki = WikiService(client)
                md = Md2FeishuService(wiki)
                result = await md.push_markdown(
                    markdown,
                    title=doc_title,
                    space_id=space_id,
                    parent_node_token=parent,
                )

        url = result.get("url", "")
        blocks = result.get("blocks_written", 0)
        console.print(f"[success]✓[/success] Pushed [bold]{doc_title}[/bold]")
        console.print(f"  Blocks written: {blocks}")
        if url:
            console.print(f"  URL: [link={url}]{url}[/link]")

    asyncio.run(_run())


@app.command()
def inspect(token: str) -> None:
    """Inspect document content (pretty-print JSON)."""

    async def _run() -> None:
        async with _get_client() as client:
            wiki = WikiService(client)
            result = await wiki.get_doc_raw_content(token)

            console.print(
                Panel(
                    JSON.from_data(result),
                    title=f"Document: {token}",
                    border_style="cyan",
                )
            )

    asyncio.run(_run())


@app.command()
def chats() -> None:
    """List chats the bot belongs to."""

    async def _run() -> None:
        async with _get_client() as client:
            msg = MessagingService(client)
            result = await msg.list_chats()

            items = result.get("data", {}).get("items", [])
            table = Table(
                title="Bot Chats",
                show_header=True,
                header_style="bold cyan",
            )
            table.add_column("Name", style="bold")
            table.add_column("Chat ID", style="dim")
            table.add_column("Members", justify="right")

            for item in items:
                table.add_row(
                    item.get("name", "DM"),
                    item.get("chat_id", ""),
                    str(item.get("user_count", "")),
                )

            console.print(table)
            console.print(f"[dim]Total: {len(items)} chats[/dim]")

    asyncio.run(_run())
