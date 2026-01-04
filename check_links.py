#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "httpx>=0.27.0",
#     "rich>=13.7.0",
# ]
# ///

"""Check and fix links in markdown recipe files.

This script:
- Finds all .dj files in content directory
- Checks if links are still available
- Searches Wayback Machine for available snapshots
- Updates links based on availability:
  - Working link: adds Wayback Machine link after original
  - Only Wayback works: replaces with Wayback link
  - Neither works: adds note in parenthesis

Usage:
    ./check_links.py              # Apply changes
    ./check_links.py --dry-run    # Preview changes without modifying files
"""

from __future__ import annotations

import argparse
import asyncio
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import httpx
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

if TYPE_CHECKING:
    from collections.abc import Iterator

console = Console()

USER_AGENT = "Mozilla/5.0 (compatible; LinkChecker/1.0; +https://recipes.kyleking.me)"
TIMEOUT = 10
RATE_LIMIT_DELAY = 0.5
WAYBACK_DELAY = 2.0

_url_cache: dict[str, bool] = {}
_wayback_cache: dict[str, str | None] = {}


@dataclass(frozen=True)
class LinkStatus:
    """Status of a link check."""

    original_url: str
    is_live: bool
    wayback_url: str | None
    error_message: str | None = None


@dataclass(frozen=True)
class LinkReplacement:
    """Replacement instruction for a link."""

    original_text: str
    new_text: str
    status: LinkStatus


def _normalize_url(url: str) -> str:
    """Normalize URL by trimming trailing slashes."""
    return url.rstrip("/")


def _extract_links(content: str) -> Iterator[tuple[str, str, str, str | None, bool]]:
    """Extract markdown links from content.

    Returns tuples of (full_match, display_text, url, existing_wayback_link, has_unavailable_marker).
    """
    pattern = re.compile(
        r"\[([^\]]+)\]\(([^\)]+)\)(?:\s+\(\[(?:wayback|archive)\]\([^\)]+\)\))*(?:\s+\((?:wayback|link) unavailable\))*"
    )
    for match in re.finditer(pattern, content):
        full_match = match.group(0)
        display_text = match.group(1)
        url = match.group(2)

        if not url.startswith(("http://", "https://")):
            continue

        existing_wayback = None
        wayback_pattern = re.compile(r"\(\[(?:wayback|archive)\]\(([^\)]+)\)\)")
        if wayback_matches := list(re.finditer(wayback_pattern, full_match)):
            existing_wayback = wayback_matches[0].group(1)

        has_unavailable = "(wayback unavailable)" in full_match or "(link unavailable)" in full_match

        yield full_match, display_text, url, existing_wayback, has_unavailable


async def _check_url_availability(client: httpx.AsyncClient, url: str) -> bool:
    """Check if URL is available and returns valid content."""
    normalized_url = _normalize_url(url)

    if normalized_url in _url_cache:
        return _url_cache[normalized_url]

    try:
        await asyncio.sleep(RATE_LIMIT_DELAY)
        response = await client.head(
            normalized_url,
            headers={"User-Agent": USER_AGENT},
            timeout=TIMEOUT,
            follow_redirects=True,
        )
        if response.status_code == 405:
            response = await client.get(
                normalized_url,
                headers={"User-Agent": USER_AGENT},
                timeout=TIMEOUT,
                follow_redirects=True,
            )
        is_available = response.status_code < 400
        _url_cache[normalized_url] = is_available
        return is_available
    except (httpx.HTTPError, Exception) as exc:
        console.print(f"[yellow]Error checking {normalized_url}: {exc!s}[/yellow]")
        _url_cache[normalized_url] = False
        return False


async def _get_wayback_link(client: httpx.AsyncClient, url: str) -> str | None:
    """Get most recent Wayback Machine link."""
    normalized_url = _normalize_url(url)

    if normalized_url in _wayback_cache:
        return _wayback_cache[normalized_url]

    api_url = f"https://archive.org/wayback/available?url={normalized_url}"
    try:
        await asyncio.sleep(WAYBACK_DELAY)
        response = await client.get(
            api_url,
            headers={"User-Agent": USER_AGENT},
            timeout=TIMEOUT,
        )
        data = response.json()

        wayback_url = None
        if archived := data.get("archived_snapshots", {}).get("closest"):
            if archived.get("available"):
                wayback_url = archived["url"]

        _wayback_cache[normalized_url] = wayback_url
        return wayback_url
    except (httpx.HTTPError, Exception) as exc:
        console.print(
            f"[yellow]Error checking Wayback for {normalized_url}: {exc!s}[/yellow]"
        )
        _wayback_cache[normalized_url] = None
        return None


async def _check_link(client: httpx.AsyncClient, url: str) -> LinkStatus:
    """Check link status and find Wayback link if needed."""
    normalized_url = _normalize_url(url)
    console.print(f"Checking: {normalized_url}")

    if "web.archive.org" in normalized_url:
        return LinkStatus(
            original_url=normalized_url,
            is_live=True,
            wayback_url=normalized_url,
        )

    is_live = await _check_url_availability(client, normalized_url)
    wayback_url = await _get_wayback_link(client, normalized_url)

    return LinkStatus(
        original_url=normalized_url,
        is_live=is_live,
        wayback_url=wayback_url,
    )


def _create_replacement(
    full_match: str,
    display_text: str,
    status: LinkStatus,
    existing_wayback: str | None,
    has_unavailable: bool,
) -> LinkReplacement | None:
    """Create replacement text based on link status.

    Returns None if no replacement needed.
    """
    base_link = f"[{display_text}]({status.original_url})"

    if status.is_live and status.wayback_url:
        new_text = f"{base_link} ([wayback]({status.wayback_url}))"
    elif not status.is_live and status.wayback_url:
        new_text = f"[{display_text}]({status.wayback_url})"
    elif not status.is_live and not status.wayback_url:
        new_text = f"{base_link} (wayback unavailable)"
    else:
        return None

    if new_text == full_match:
        return None

    return LinkReplacement(
        original_text=full_match,
        new_text=new_text,
        status=status,
    )


async def _process_file(
    client: httpx.AsyncClient, file_path: Path, *, force: bool = False
) -> list[LinkReplacement]:
    """Process a single file and return replacements."""
    content = file_path.read_text()
    replacements = []

    for (
        full_match,
        display_text,
        url,
        existing_wayback,
        has_unavailable,
    ) in _extract_links(content):
        if not force and existing_wayback:
            console.print(f"Skipping (has wayback link): {_normalize_url(url)}")
            continue

        status = await _check_link(client, url)
        replacement = _create_replacement(
            full_match, display_text, status, existing_wayback, has_unavailable
        )

        if replacement:
            replacements.append(replacement)

    return replacements


def _apply_replacements(
    file_path: Path, replacements: list[LinkReplacement], *, dry_run: bool
) -> None:
    """Apply replacements to file."""
    if not replacements:
        return

    if dry_run:
        console.print(f"\n[cyan]Would update {file_path.name}:[/cyan]")
        for replacement in replacements:
            console.print(f"  [red]- {replacement.original_text}[/red]")
            console.print(f"  [green]+ {replacement.new_text}[/green]")
        return

    content = file_path.read_text()

    for replacement in replacements:
        content = content.replace(
            replacement.original_text,
            replacement.new_text,
        )

    file_path.write_text(content)
    console.print(
        f"[green]Updated {file_path.name} with {len(replacements)} changes[/green]"
    )


def _find_dj_files(content_dir: Path) -> list[Path]:
    """Find all .dj files in content directory."""
    return sorted(content_dir.rglob("*.dj"))


async def main() -> None:
    """Check and fix links in recipe markdown files."""
    parser = argparse.ArgumentParser(description="Check and fix links in recipe files")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without modifying files",
    )
    parser.add_argument(
        "--file",
        type=Path,
        help="Process a single file instead of all files",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force check all links, even those with existing wayback links",
    )
    args = parser.parse_args()

    content_dir = Path("content")

    if args.file:
        if not args.file.exists():
            console.print(f"[red]Error: file {args.file} not found[/red]")
            return
        files = [args.file]
    else:
        if not content_dir.exists():
            console.print("[red]Error: content directory not found[/red]")
            return
        files = _find_dj_files(content_dir)

    console.print(f"Found {len(files)} recipe file{'s' if len(files) != 1 else ''}")

    if args.dry_run:
        console.print("[yellow]DRY RUN MODE - No files will be modified[/yellow]")

    all_replacements: dict[Path, list[LinkReplacement]] = {}

    async with httpx.AsyncClient() as client:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Processing files...", total=len(files))

            for file_path in files:
                progress.update(task, description=f"Processing {file_path.name}")

                replacements = await _process_file(client, file_path, force=args.force)
                if replacements:
                    all_replacements[file_path] = replacements
                    _apply_replacements(file_path, replacements, dry_run=args.dry_run)

                progress.advance(task)

    _print_summary(all_replacements, dry_run=args.dry_run)


def _print_summary(
    all_replacements: dict[Path, list[LinkReplacement]], *, dry_run: bool
) -> None:
    """Print summary of changes."""
    if not all_replacements:
        console.print("\n[green]No changes needed - all links are valid![/green]")
        return

    table = Table(title=f"\nSummary ({'Dry Run' if dry_run else 'Applied Changes'})")
    table.add_column("File", style="cyan")
    table.add_column("Changes", justify="right", style="magenta")
    table.add_column("Live", justify="right", style="green")
    table.add_column("Wayback", justify="right", style="yellow")
    table.add_column("Dead", justify="right", style="red")

    total_changes = 0
    total_live = 0
    total_wayback = 0
    total_dead = 0

    for file_path, replacements in all_replacements.items():
        total_changes += len(replacements)
        live = sum(1 for r in replacements if r.status.is_live)
        wayback = sum(
            1 for r in replacements if not r.status.is_live and r.status.wayback_url
        )
        dead = sum(
            1 for r in replacements if not r.status.is_live and not r.status.wayback_url
        )

        total_live += live
        total_wayback += wayback
        total_dead += dead

        table.add_row(
            file_path.name, str(len(replacements)), str(live), str(wayback), str(dead)
        )

    console.print(table)
    console.print(
        f"\n[bold]Total: {total_changes} link{'s' if total_changes != 1 else ''} in {len(all_replacements)} file{'s' if len(all_replacements) != 1 else ''}[/bold]"
    )
    console.print(
        f"[bold]Live: {total_live}, Wayback: {total_wayback}, Dead: {total_dead}[/bold]"
    )

    if dry_run:
        console.print("\n[yellow]Run without --dry-run to apply changes[/yellow]")
    else:
        console.print("\n[bold green]Done![/bold green]")


if __name__ == "__main__":
    asyncio.run(main())
