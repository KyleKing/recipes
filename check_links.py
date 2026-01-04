#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "requests>=2.31.0",
#     "rich>=13.7.0",
# ]
# ///

"""Check and fix links in markdown recipe files.

This script:
- Finds all .dj files in content directory
- Checks if links are still available
- Searches Wayback Machine for archived versions
- Updates links based on availability:
  - Working link: adds web archive permalink after original
  - Only archive works: replaces with archive link
  - Neither works: adds note in parenthesis

Usage:
    ./check_links.py              # Apply changes
    ./check_links.py --dry-run    # Preview changes without modifying files
"""

from __future__ import annotations

import argparse
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import requests
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

if TYPE_CHECKING:
    from collections.abc import Iterator

console = Console()

USER_AGENT = "Mozilla/5.0 (compatible; LinkChecker/1.0; +https://recipes.kyleking.me)"
TIMEOUT = 10
RATE_LIMIT_DELAY = 1.0


@dataclass(frozen=True)
class LinkStatus:
    """Status of a link check."""

    original_url: str
    is_live: bool
    archive_url: str | None
    error_message: str | None = None


@dataclass(frozen=True)
class LinkReplacement:
    """Replacement instruction for a link."""

    original_text: str
    new_text: str
    status: LinkStatus


def _extract_links(content: str) -> Iterator[tuple[str, str, str]]:
    """Extract markdown links from content.

    Returns tuples of (full_match, display_text, url).
    """
    pattern = r'\[([^\]]+)\]\(([^\)]+)\)'
    for match in re.finditer(pattern, content):
        full_match = match.group(0)
        display_text = match.group(1)
        url = match.group(2)
        if url.startswith(('http://', 'https://')):
            yield full_match, display_text, url


def _check_url_availability(url: str) -> bool:
    """Check if URL is available and returns valid content."""
    try:
        response = requests.head(
            url,
            headers={'User-Agent': USER_AGENT},
            timeout=TIMEOUT,
            allow_redirects=True,
        )
        if response.status_code == 405:
            response = requests.get(
                url,
                headers={'User-Agent': USER_AGENT},
                timeout=TIMEOUT,
                allow_redirects=True,
            )
        return response.status_code < 400
    except (requests.RequestException, Exception) as exc:
        console.print(f"[yellow]Error checking {url}: {exc!s}[/yellow]")
        return False


def _get_wayback_archive(url: str) -> str | None:
    """Get most recent Wayback Machine archive URL."""
    api_url = f"https://archive.org/wayback/available?url={url}"
    try:
        time.sleep(RATE_LIMIT_DELAY)
        response = requests.get(
            api_url,
            headers={'User-Agent': USER_AGENT},
            timeout=TIMEOUT,
        )
        data = response.json()

        if archived := data.get('archived_snapshots', {}).get('closest'):
            if archived.get('available'):
                return archived['url']
    except (requests.RequestException, Exception) as exc:
        console.print(f"[yellow]Error checking Wayback for {url}: {exc!s}[/yellow]")

    return None


def _check_link(url: str) -> LinkStatus:
    """Check link status and find archive if needed."""
    console.print(f"Checking: {url}")

    if 'web.archive.org' in url:
        return LinkStatus(
            original_url=url,
            is_live=True,
            archive_url=url,
        )

    is_live = _check_url_availability(url)
    archive_url = _get_wayback_archive(url)

    return LinkStatus(
        original_url=url,
        is_live=is_live,
        archive_url=archive_url,
    )


def _create_replacement(full_match: str, display_text: str, status: LinkStatus) -> LinkReplacement | None:
    """Create replacement text based on link status.

    Returns None if no replacement needed.
    """
    if status.is_live and status.archive_url:
        new_text = f"{full_match} ([archive]({status.archive_url}))"
    elif not status.is_live and status.archive_url:
        new_text = f"[{display_text}]({status.archive_url})"
    elif not status.is_live and not status.archive_url:
        new_text = f"{full_match} (link unavailable)"
    else:
        return None

    return LinkReplacement(
        original_text=full_match,
        new_text=new_text,
        status=status,
    )


def _process_file(file_path: Path) -> list[LinkReplacement]:
    """Process a single file and return replacements."""
    content = file_path.read_text()
    replacements = []

    for full_match, display_text, url in _extract_links(content):
        status = _check_link(url)
        replacement = _create_replacement(full_match, display_text, status)

        if replacement:
            replacements.append(replacement)

    return replacements


def _apply_replacements(file_path: Path, replacements: list[LinkReplacement], *, dry_run: bool) -> None:
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
    console.print(f"[green]Updated {file_path.name} with {len(replacements)} changes[/green]")


def _find_dj_files(content_dir: Path) -> list[Path]:
    """Find all .dj files in content directory."""
    return sorted(content_dir.rglob("*.dj"))


def main() -> None:
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

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Processing files...", total=len(files))

        for file_path in files:
            progress.update(task, description=f"Processing {file_path.name}")

            replacements = _process_file(file_path)
            if replacements:
                all_replacements[file_path] = replacements
                _apply_replacements(file_path, replacements, dry_run=args.dry_run)

            progress.advance(task)

    _print_summary(all_replacements, dry_run=args.dry_run)


def _print_summary(all_replacements: dict[Path, list[LinkReplacement]], *, dry_run: bool) -> None:
    """Print summary of changes."""
    if not all_replacements:
        console.print("\n[green]No changes needed - all links are valid![/green]")
        return

    table = Table(title=f"\nSummary ({'Dry Run' if dry_run else 'Applied Changes'})")
    table.add_column("File", style="cyan")
    table.add_column("Changes", justify="right", style="magenta")
    table.add_column("Status", style="green")

    total_changes = 0
    for file_path, replacements in all_replacements.items():
        total_changes += len(replacements)
        status_counts = {
            "live": sum(1 for r in replacements if r.status.is_live),
            "archived": sum(1 for r in replacements if not r.status.is_live and r.status.archive_url),
            "dead": sum(1 for r in replacements if not r.status.is_live and not r.status.archive_url),
        }
        status = f"✓{status_counts['live']} 📦{status_counts['archived']} ✗{status_counts['dead']}"
        table.add_row(file_path.name, str(len(replacements)), status)

    console.print(table)
    console.print(f"\n[bold]Total: {total_changes} link{'s' if total_changes != 1 else ''} in {len(all_replacements)} file{'s' if len(all_replacements) != 1 else ''}[/bold]")

    if dry_run:
        console.print("\n[yellow]Run without --dry-run to apply changes[/yellow]")
    else:
        console.print("\n[bold green]Done![/bold green]")


if __name__ == "__main__":
    main()
