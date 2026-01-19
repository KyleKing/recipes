#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "rich>=13.7.0",
#     "rapidfuzz>=3.6.0",
#     "pillow>=11.1.0",
# ]
# ///

"""Interactive tool to manage recipe images.

Usage:
    mise run link-images              # Interactive mode
    mise run link-images --dry-run    # Preview changes without modifying files
    mise run link-images --auto       # Auto-link exact matches only (no prompts)
"""

import argparse
import base64
import io
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from PIL import Image
from rapidfuzz import fuzz
from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.table import Table

console = Console()

IMAGE_EXTENSIONS = {".jpeg", ".jpg", ".png"}
CONTENT_DIR = Path("content")


@dataclass(frozen=True)
class Recipe:
    path: Path
    basename: str
    image_filename: str | None

    @property
    def rel_path(self) -> str:
        return str(self.path.relative_to(CONTENT_DIR))

    @property
    def has_image(self) -> bool:
        return self.image_filename is not None


@dataclass(frozen=True)
class ImageFile:
    path: Path
    basename: str
    extension: str

    @property
    def rel_path(self) -> str:
        return str(self.path.relative_to(CONTENT_DIR))


@dataclass
class PendingLink:
    image: ImageFile
    recipe: Recipe | None = None
    score: float = 0.0
    action: str = ""


# --- Scanning ---


def _parse_recipe(path: Path) -> Recipe:
    content = path.read_text()
    image_filename = None
    if match := re.search(r'\{\s*rating=\d+\s+image="([^"]+)"\s*\}', content):
        image_val = match.group(1)
        if "." in image_val:
            image_filename = image_val
    return Recipe(path=path, basename=path.stem, image_filename=image_filename)


def _scan_content() -> tuple[list[Recipe], list[ImageFile]]:
    recipes, images = [], []
    for item in CONTENT_DIR.rglob("*"):
        if item.name.startswith("_"):
            continue
        if item.suffix == ".dj":
            recipes.append(_parse_recipe(item))
        elif item.is_file() and item.suffix.lower() in IMAGE_EXTENSIONS:
            images.append(
                ImageFile(path=item, basename=item.stem, extension=item.suffix)
            )
    return recipes, images


def _load_ignore_list() -> set[str]:
    ignore_file = CONTENT_DIR / ".imageignore"
    if not ignore_file.exists():
        return set()
    ignored = set()
    for line in ignore_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "|" in line:
            ignored.add(line.split("|", 1)[0].strip())
    return ignored


# --- Matching ---


def _find_exact_matches(
    recipes: list[Recipe], images: list[ImageFile]
) -> list[tuple[Recipe, ImageFile]]:
    matches = []
    for recipe in recipes:
        if recipe.has_image:
            continue
        for image in images:
            if (
                recipe.path.parent == image.path.parent
                and recipe.basename == image.basename
            ):
                matches.append((recipe, image))
                break
    return matches


def _find_orphaned_images(
    images: list[ImageFile],
    recipes: list[Recipe],
    exact_matches: list[tuple[Recipe, ImageFile]],
    ignore_list: set[str],
) -> list[ImageFile]:
    exact_match_paths = {img.path for _, img in exact_matches}
    linked_filenames = {r.image_filename for r in recipes if r.image_filename}

    return [
        img
        for img in images
        if img.path not in exact_match_paths
        and img.path.name not in linked_filenames
        and img.path.name not in ignore_list
    ]


def _fuzzy_score(query: str, recipe: Recipe) -> float:
    return fuzz.ratio(query.lower(), recipe.basename.lower())


def _best_match(
    image: ImageFile, candidates: list[Recipe]
) -> tuple[Recipe | None, float]:
    if not candidates:
        return None, 0.0
    scored = [(r, _fuzzy_score(image.basename, r)) for r in candidates]
    return max(scored, key=lambda x: x[1])


# --- File Operations ---


def _add_to_ignore(basename: str, reason: str) -> None:
    ignore_file = CONTENT_DIR / ".imageignore"
    with ignore_file.open("a") as f:
        f.write(f"{basename}|{reason}\n")
    console.print(f"[green]Added to .imageignore: {basename}[/green]")


def _update_recipe_image(recipe_path: Path, new_image: str) -> None:
    content = recipe_path.read_text()
    new_content = re.sub(r'(image=")[^"]+(")', rf"\g<1>{new_image}\2", content)
    recipe_path.write_text(new_content)
    console.print(f"[green]Updated {recipe_path.name}[/green]")


def _rename_and_link(image: ImageFile, recipe: Recipe) -> Path | None:
    new_name = f"{recipe.basename}{image.extension}"
    new_path = recipe.path.parent / new_name

    if new_path.exists():
        console.print(f"[red]Error: {new_name} already exists[/red]")
        return None

    image.path.rename(new_path)
    console.print(f"[green]Renamed: {image.path.name} -> {new_name}[/green]")
    _update_recipe_image(recipe.path, new_name)
    return new_path


def _compress_image(image_path: Path) -> None:
    try:
        subprocess.run(
            ["mise", "run", "compress", str(image_path)],
            capture_output=True,
            text=True,
            check=True,
        )
        console.print(f"[green]Compressed: {image_path.name}[/green]")
    except subprocess.CalledProcessError as err:
        console.print(f"[yellow]Compression failed: {image_path.name}[/yellow]")
        if err.stderr:
            console.print(f"[dim]{err.stderr}[/dim]")


# --- Display ---


def _display_image_preview(image_path: Path, *, max_width: int = 800) -> None:
    term_program = os.getenv("TERM_PROGRAM", "")
    if term_program not in ("WezTerm", "iTerm.app") and not sys.stdout.isatty():
        return
    try:
        img = Image.open(image_path)
        if img.width > max_width:
            ratio = max_width / img.width
            img = img.resize(
                (max_width, int(img.height * ratio)), Image.Resampling.LANCZOS
            )
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        b64_data = base64.b64encode(buffer.getvalue()).decode("ascii")
        print(f"\033]1337;File=inline=1:{b64_data}\007")
    except Exception as err:
        console.print(f"[dim]Could not display preview: {err}[/dim]")


def _show_pending_table(pending: list[PendingLink]) -> None:
    table = Table(title="Orphaned Images")
    table.add_column("#", style="cyan", width=3)
    table.add_column("Image", style="white")
    table.add_column("Best Match", style="green")
    table.add_column("Score", justify="right", style="magenta", width=6)
    table.add_column("Action", style="yellow", width=8)

    for idx, p in enumerate(pending, 1):
        match_str = p.recipe.basename if p.recipe else "[dim]none[/dim]"
        score_str = f"{p.score:.0f}%" if p.recipe else "-"
        table.add_row(str(idx), p.image.rel_path, match_str, score_str, p.action)

    console.print(table)


def _show_search_results(scored: list[tuple[Recipe, float]], query: str) -> None:
    table = Table(title=f"Search: {query}")
    table.add_column("#", style="cyan", width=3)
    table.add_column("Recipe", style="white")
    table.add_column("Score", justify="right", style="magenta")
    for i, (r, s) in enumerate(scored, 1):
        table.add_row(str(i), r.rel_path, f"{s:.0f}%")
    console.print(table)


def _show_batch_help() -> None:
    console.print("\n[dim]Commands:[/dim]")
    console.print("  [cyan]1,3,5[/cyan] or [cyan]1-5[/cyan] - Link these matches")
    console.print("  [cyan]i2,i4[/cyan] - Ignore these images")
    console.print("  [cyan]all[/cyan] - Link all matches")
    console.print("  [cyan]v3[/cyan] - View image #3")
    console.print("  [cyan]s3 query[/cyan] - Search for image #3")
    console.print("  [cyan]enter[/cyan] - Execute pending actions")


# --- Input Parsing ---


def _parse_batch_input(
    user_input: str, max_idx: int
) -> tuple[set[int], set[int], str | None]:
    link, ignore = set(), set()

    if not user_input.strip():
        return link, ignore, None

    if user_input.strip().lower() == "all":
        return set(range(1, max_idx + 1)), set(), None

    for part in user_input.replace(" ", ",").split(","):
        part = part.strip()
        if not part:
            continue

        is_ignore = part.lower().startswith("i")
        if is_ignore:
            part = part[1:]

        try:
            nums = (
                list(range(int(part.split("-")[0]), int(part.split("-")[-1]) + 1))
                if "-" in part
                else [int(part)]
            )
            for n in nums:
                if n < 1 or n > max_idx:
                    return set(), set(), f"Invalid index: {n}"
                (ignore if is_ignore else link).add(n)
        except ValueError:
            return set(), set(), f"Invalid input: {part}"

    return link, ignore, None


# --- Batch Processing ---


def _handle_view_command(pending: list[PendingLink], cmd: str) -> bool:
    try:
        idx = int(cmd[1:]) - 1
        if 0 <= idx < len(pending):
            _display_image_preview(pending[idx].image.path)
        else:
            console.print("[red]Invalid index[/red]")
    except ValueError:
        console.print("[red]Usage: v3[/red]")
    return True


def _handle_search_command(
    pending: list[PendingLink], candidates: list[Recipe], cmd: str
) -> bool:
    parts = cmd[1:].split(None, 1)
    if len(parts) < 2:
        console.print("[red]Usage: s3 search_query[/red]")
        return True

    try:
        idx = int(parts[0]) - 1
        query = parts[1]
    except ValueError:
        console.print("[red]Usage: s3 search_query[/red]")
        return True

    if not (0 <= idx < len(pending)):
        console.print("[red]Invalid index[/red]")
        return True

    scored = sorted(
        [(r, _fuzzy_score(query, r)) for r in candidates],
        key=lambda x: x[1],
        reverse=True,
    )[:5]

    _show_search_results(scored, query)
    choice = Prompt.ask("Select 1-5 or enter to cancel", default="")

    if choice:
        try:
            sel_idx = int(choice) - 1
            if 0 <= sel_idx < len(scored):
                pending[idx].recipe = scored[sel_idx][0]
                pending[idx].score = scored[sel_idx][1]
                pending[idx].action = "link"
                _show_pending_table(pending)
        except ValueError:
            pass

    return True


def _handle_batch_selection(pending: list[PendingLink], user_input: str) -> bool:
    link_set, ignore_set, err = _parse_batch_input(user_input, len(pending))
    if err:
        console.print(f"[red]{err}[/red]")
        return True

    for idx in link_set:
        if pending[idx - 1].recipe:
            pending[idx - 1].action = "link"

    for idx in ignore_set:
        pending[idx - 1].action = "ignore"

    _show_pending_table(pending)
    return True


def _execute_pending_actions(pending: list[PendingLink], *, dry_run: bool) -> int:
    count = 0
    ignore_reason = None

    for p in pending:
        if p.action == "link" and p.recipe:
            if dry_run:
                console.print(
                    f"[yellow]Would rename {p.image.rel_path} -> {p.recipe.basename}{p.image.extension}[/yellow]"
                )
            else:
                new_path = _rename_and_link(p.image, p.recipe)
                if new_path:
                    _compress_image(new_path)
            count += 1

        elif p.action == "ignore":
            if not dry_run and ignore_reason is None:
                ignore_reason = Prompt.ask(
                    "Reason for ignored images", default="Not a recipe image"
                )
            if dry_run:
                console.print(
                    f"[yellow]Would add to .imageignore: {p.image.path.name}[/yellow]"
                )
            else:
                _add_to_ignore(p.image.path.name, ignore_reason)
            count += 1

    return count


def _collect_batch_actions(
    pending: list[PendingLink], candidates: list[Recipe]
) -> None:
    _show_pending_table(pending)
    _show_batch_help()

    while True:
        user_input = Prompt.ask("\nAction", default="")

        if not user_input:
            break

        cmd_lower = user_input.lower()
        if cmd_lower.startswith("v"):
            _handle_view_command(pending, user_input)
        elif cmd_lower.startswith("s"):
            _handle_search_command(pending, candidates, user_input)
        else:
            _handle_batch_selection(pending, user_input)


# --- Main Processing ---


def _process_exact_matches(
    matches: list[tuple[Recipe, ImageFile]], *, dry_run: bool, auto: bool
) -> int:
    if not matches:
        return 0

    console.print(f"\n[bold]Found {len(matches)} exact matches:[/bold]")

    table = Table()
    table.add_column("#", style="cyan", width=3)
    table.add_column("Recipe", style="white")
    table.add_column("Image", style="green")

    for idx, (recipe, image) in enumerate(matches, 1):
        table.add_row(str(idx), recipe.rel_path, image.rel_path)

    console.print(table)

    if not auto and not Confirm.ask("\nLink these automatically?", default=True):
        return 0

    for recipe, image in matches:
        if dry_run:
            console.print(f"[yellow]Would update {recipe.path.name}[/yellow]")
        else:
            _update_recipe_image(recipe.path, image.path.name)

    return len(matches)


def _process_orphaned_batch(
    orphaned: list[ImageFile], candidates: list[Recipe], *, dry_run: bool
) -> int:
    if not orphaned:
        return 0

    pending = [
        PendingLink(image=img, recipe=recipe, score=score)
        for img in orphaned
        for recipe, score in [_best_match(img, candidates)]
    ]

    console.print(f"\n[bold yellow]Found {len(pending)} orphaned images[/bold yellow]")
    _collect_batch_actions(pending, candidates)
    return _execute_pending_actions(pending, dry_run=dry_run)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Interactive tool to manage recipe images"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview changes without modifying files"
    )
    parser.add_argument(
        "--auto", action="store_true", help="Auto-link exact matches only (no prompts)"
    )
    args = parser.parse_args()

    if not CONTENT_DIR.exists():
        console.print("[red]Error: content directory not found[/red]")
        return

    if args.dry_run:
        console.print("[yellow]DRY RUN MODE - No files will be modified[/yellow]")

    console.print("\n[bold]Scanning content/ directory...[/bold]")

    recipes, images = _scan_content()
    ignore_list = _load_ignore_list()

    console.print(f"  {len(recipes)} recipes, {len(images)} images")

    exact_matches = _find_exact_matches(recipes, images)
    exact_count = _process_exact_matches(
        exact_matches, dry_run=args.dry_run, auto=args.auto
    )

    if args.auto:
        console.print(f"\n[bold green]Auto-linked {exact_count} recipes[/bold green]")
        return

    orphaned = _find_orphaned_images(images, recipes, exact_matches, ignore_list)
    candidates = [r for r in recipes if not r.has_image]

    orphaned_count = _process_orphaned_batch(orphaned, candidates, dry_run=args.dry_run)

    console.print("\n[bold]Summary:[/bold]")
    console.print(f"  Exact matches linked: {exact_count}")
    console.print(f"  Orphaned images processed: {orphaned_count}")

    if args.dry_run:
        console.print("\n[yellow]Run without --dry-run to apply changes[/yellow]")
    else:
        console.print("\n[bold green]Done![/bold green]")


if __name__ == "__main__":
    main()
