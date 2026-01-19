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

This script:
- Auto-links recipes with image="None" to matching image files
- Fuzzy-matches orphaned images (like IMG_3492.jpeg) to recipes via interactive prompts
- Documents intentionally ignored images in .imageignore
- Optionally compresses newly linked images

Usage:
    mise run link-images              # Interactive mode
    mise run link-images --dry-run    # Preview changes without modifying files
    mise run link-images --auto       # Auto-link exact matches only (no prompts)
    mise run link-images --category main  # Process specific category only
"""

import argparse
import base64
import io
import os
import re
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from PIL import Image
from rapidfuzz import fuzz
from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.table import Table

console = Console()

IMAGE_EXTENSIONS = {".jpeg", ".jpg", ".png"}
IGNORED_PREFIXES = {"_"}

# Global flag to disable image previews (set via --no-preview)
_DISABLE_PREVIEWS = False


def _supports_inline_images() -> bool:
    """Check if terminal supports iTerm2 inline images protocol."""
    if _DISABLE_PREVIEWS:
        return False
    term_program = os.getenv("TERM_PROGRAM", "")
    return term_program in ("WezTerm", "iTerm.app") or sys.stdout.isatty()


def _display_image_preview(image_path: Path, *, max_width: int = 800) -> None:
    """Display image preview in terminal using iTerm2 inline images protocol.

    Args:
        image_path: Path to image file
        max_width: Maximum width in pixels (default: 800)
    """
    if not _supports_inline_images():
        return

    try:
        img = Image.open(image_path)

        # Resize if too wide
        if img.width > max_width:
            ratio = max_width / img.width
            new_height = int(img.height * ratio)
            img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

        # Convert to PNG in memory
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        img_data = buffer.getvalue()

        # Encode as base64
        b64_data = base64.b64encode(img_data).decode("ascii")

        # Print iTerm2 inline image escape sequence
        # Format: ESC ] 1337 ; File=inline=1:<base64_data> BEL
        print(f"\033]1337;File=inline=1:{b64_data}\007")
    except Exception as err:
        console.print(f"[dim]Could not display image preview: {err}[/dim]")


@dataclass(frozen=True)
class RecipeMetadata:
    """Metadata extracted from a recipe .dj file."""

    path: Path
    category: str
    basename: str  # Without extension
    title: str  # From first H1
    rating: int
    image_value: str  # Raw: "None" or "filename.ext"
    has_image: bool  # True if image_value contains "."


@dataclass(frozen=True)
class ImageFile:
    """Image file found in content directory."""

    path: Path
    category: str
    basename: str
    extension: str  # .jpeg, .jpg, .png


@dataclass(frozen=True)
class LinkOperation:
    """Operation to link an image to a recipe."""

    image: ImageFile
    recipe: RecipeMetadata
    action: Literal["update_metadata", "rename_and_link"]
    new_image_name: str | None


def _parse_metadata(content: str) -> tuple[int, str]:
    """Extract (rating, image) from metadata block.

    Returns:
        Tuple of (rating, image_value)
    """
    pattern = r'\{\s*rating=(\d+)\s+image="([^"]+)"\s*\}'
    if match := re.search(pattern, content):
        rating = int(match.group(1))
        image = match.group(2)
        return rating, image
    return 0, "None"


def _extract_title(content: str) -> str:
    """Extract first H1 heading as title."""
    pattern = r'^#\s+(.+)$'
    if match := re.search(pattern, content, re.MULTILINE):
        return match.group(1).strip()
    return "Untitled"


def _scan_recipes(content_dir: Path, category_filter: str | None = None) -> list[RecipeMetadata]:
    """Walk content/*/ for .dj files, extract metadata.

    Args:
        content_dir: Path to content directory
        category_filter: Optional category name to filter by

    Returns:
        List of RecipeMetadata
    """
    recipes = []

    for dj_file in content_dir.rglob("*.dj"):
        if dj_file.name.startswith(tuple(IGNORED_PREFIXES)):
            continue

        category = dj_file.parent.name
        if category_filter and category != category_filter:
            continue

        content = dj_file.read_text()
        rating, image_value = _parse_metadata(content)
        title = _extract_title(content)

        recipe = RecipeMetadata(
            path=dj_file,
            category=category,
            basename=dj_file.stem,
            title=title,
            rating=rating,
            image_value=image_value,
            has_image="." in image_value,
        )
        recipes.append(recipe)

    return recipes


def _scan_images(content_dir: Path, category_filter: str | None = None) -> list[ImageFile]:
    """Find .jpeg/.jpg/.png files in content/.

    Args:
        content_dir: Path to content directory
        category_filter: Optional category name to filter by

    Returns:
        List of ImageFile
    """
    images = []

    for image_path in content_dir.rglob("*"):
        if image_path.is_file() and image_path.suffix.lower() in IMAGE_EXTENSIONS:
            if image_path.name.startswith(tuple(IGNORED_PREFIXES)):
                continue

            category = image_path.parent.name
            if category_filter and category != category_filter:
                continue

            image = ImageFile(
                path=image_path,
                category=category,
                basename=image_path.stem,
                extension=image_path.suffix,
            )
            images.append(image)

    return images


def _find_exact_matches(
    recipes: list[RecipeMetadata],
    images: list[ImageFile],
) -> list[tuple[RecipeMetadata, ImageFile]]:
    """Find recipes with image="None" that have matching basename.ext in same category.

    Args:
        recipes: List of all recipes
        images: List of all images

    Returns:
        List of (recipe, image) pairs for exact matches
    """
    matches = []
    recipes_needing_images = [r for r in recipes if not r.has_image]

    for recipe in recipes_needing_images:
        for image in images:
            if recipe.category == image.category and recipe.basename == image.basename:
                matches.append((recipe, image))
                break

    return matches


def _find_orphaned_images(
    images: list[ImageFile],
    recipes: list[RecipeMetadata],
    ignore_list: dict[str, str],
) -> list[ImageFile]:
    """Find images without matching recipe basename.

    Args:
        images: List of all images
        recipes: List of all recipes
        ignore_list: Dict of {basename: reason} for ignored images

    Returns:
        List of orphaned images
    """
    recipe_image_basenames = {
        (r.category, r.image_value.rsplit(".", 1)[0])
        for r in recipes
        if r.has_image and "." in r.image_value
    }

    orphaned = []
    for image in images:
        if image.path.name in ignore_list:
            continue

        if (image.category, image.basename) not in recipe_image_basenames:
            orphaned.append(image)

    return orphaned


def _fuzzy_score(query: str, recipe_path: str, recipe_basename: str) -> float:
    """Calculate weighted fuzzy match score.

    Args:
        query: Search query
        recipe_path: Relative path (category/basename)
        recipe_basename: Recipe basename only

    Returns:
        Score 0-100 (weighted: 70% basename, 30% path)
    """
    filename_score = fuzz.ratio(query.lower(), recipe_basename.lower())
    path_score = fuzz.ratio(query.lower(), recipe_path.lower())
    return (filename_score * 0.7) + (path_score * 0.3)


def _interactive_fuzzy_select(
    candidates: list[RecipeMetadata],
    image_basename: str,
) -> RecipeMetadata | None:
    """Interactive fuzzy filter using rich + rapidfuzz.

    Args:
        candidates: List of candidate recipes
        image_basename: Image basename to use as initial query

    Returns:
        Selected recipe or None if cancelled
    """
    if not candidates:
        console.print("[yellow]No candidate recipes available[/yellow]")
        return None

    console.print(f"\nFuzzy matching for: [cyan]{image_basename}[/cyan]")
    console.print(f"[dim]Found {len(candidates)} recipes without images[/dim]")

    query = image_basename

    while True:
        query = Prompt.ask(
            "\nEnter search query",
            default=query,
        )

        scored = [
            (
                recipe,
                _fuzzy_score(query, f"{recipe.category}/{recipe.basename}", recipe.basename),
            )
            for recipe in candidates
        ]

        scored.sort(key=lambda x: x[1], reverse=True)

        top_matches = scored[:20]

        if not top_matches:
            console.print("[yellow]No matches found. Try different search terms.[/yellow]")
            retry = Confirm.ask("Try again?", default=True)
            if not retry:
                return None
            continue

        table = Table(title="Top Matches")
        table.add_column("#", style="cyan", width=3)
        table.add_column("Score", justify="right", style="magenta", width=6)
        table.add_column("Recipe", style="white")

        for idx, (recipe, score) in enumerate(top_matches, 1):
            rel_path = f"{recipe.category}/{recipe.basename}"
            table.add_row(str(idx), f"{score:.0f}%", rel_path)

        console.print(table)

        choice = Prompt.ask(
            "\nSelect recipe number, 'r' to retry search, or 'c' to cancel",
            default="c",
        )

        if choice.lower() == "c":
            return None

        if choice.lower() == "r":
            continue

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(top_matches):
                return top_matches[idx][0]
            console.print("[red]Invalid selection. Please try again.[/red]")
        except ValueError:
            console.print("[red]Invalid input. Enter a number, 'r', or 'c'.[/red]")


def _update_recipe_image(recipe_path: Path, new_image: str, *, dry_run: bool) -> None:
    """Replace image="old" with image="new" in .dj file.

    Args:
        recipe_path: Path to recipe file
        new_image: New image filename
        dry_run: If True, only preview changes
    """
    content = recipe_path.read_text()
    pattern = r'(image=")([^"]+)(")'

    def replace_func(match: re.Match) -> str:
        return f'{match.group(1)}{new_image}{match.group(3)}'

    new_content = re.sub(pattern, replace_func, content)

    if dry_run:
        console.print(f"[yellow]Would update {recipe_path.name}[/yellow]")
        return

    recipe_path.write_text(new_content)
    console.print(f"[green]Updated {recipe_path.name}[/green]")


def _rename_image(old_path: Path, new_path: Path, *, dry_run: bool) -> None:
    """Safely rename image file.

    Args:
        old_path: Current image path
        new_path: Target image path
        dry_run: If True, only preview changes
    """
    if new_path.exists():
        console.print(f"[red]Error: {new_path.name} already exists[/red]")
        return

    if dry_run:
        console.print(f"[yellow]Would rename: {old_path.name} → {new_path.name}[/yellow]")
        return

    old_path.rename(new_path)
    console.print(f"[green]Renamed: {old_path.name} → {new_path.name}[/green]")


def _compress_image(image_path: Path, *, dry_run: bool) -> None:
    """Compress image using mise compress task.

    Args:
        image_path: Path to image to compress
        dry_run: If True, only preview changes
    """
    if dry_run:
        console.print(f"[yellow]Would compress: {image_path.name}[/yellow]")
        return

    try:
        result = subprocess.run(
            ["mise", "run", "compress", str(image_path)],
            capture_output=True,
            text=True,
            check=True,
        )
        console.print(f"[green]Compressed: {image_path.name}[/green]")
    except subprocess.CalledProcessError as err:
        console.print(f"[yellow]Warning: compression failed for {image_path.name}[/yellow]")
        console.print(f"[dim]{err.stderr}[/dim]")


def _load_ignore_list(content_dir: Path) -> dict[str, str]:
    """Load .imageignore, return {basename: reason}.

    Args:
        content_dir: Path to content directory

    Returns:
        Dict mapping image basename to ignore reason
    """
    ignore_file = content_dir / ".imageignore"
    if not ignore_file.exists():
        return {}

    ignore_list = {}
    for line in ignore_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        if "|" in line:
            basename, reason = line.split("|", 1)
            ignore_list[basename.strip()] = reason.strip()

    return ignore_list


def _add_to_ignore(basename: str, reason: str, content_dir: Path, *, dry_run: bool) -> None:
    """Append to .imageignore with user-provided reason.

    Args:
        basename: Image basename to ignore
        reason: Reason for ignoring
        content_dir: Path to content directory
        dry_run: If True, only preview changes
    """
    ignore_file = content_dir / ".imageignore"

    entry = f"{basename}|{reason}\n"

    if dry_run:
        console.print(f"[yellow]Would add to .imageignore: {entry.strip()}[/yellow]")
        return

    with ignore_file.open("a") as f:
        f.write(entry)

    console.print(f"[green]Added to .imageignore: {basename}[/green]")


def _process_exact_matches(
    matches: list[tuple[RecipeMetadata, ImageFile]],
    *,
    dry_run: bool,
    auto: bool,
) -> int:
    """Process exact matches between recipes and images.

    Args:
        matches: List of (recipe, image) exact matches
        dry_run: If True, only preview changes
        auto: If True, skip prompts

    Returns:
        Number of processed matches
    """
    if not matches:
        return 0

    console.print(f"\n[bold]Found {len(matches)} exact matches:[/bold]")

    table = Table()
    table.add_column("#", style="cyan", width=3)
    table.add_column("Recipe", style="white")
    table.add_column("Image", style="green")
    table.add_column("Size", justify="right", style="yellow")

    for idx, (recipe, image) in enumerate(matches, 1):
        size_mb = image.path.stat().st_size / (1024 * 1024)
        table.add_row(
            str(idx),
            f"{recipe.category}/{recipe.basename}",
            image.path.name,
            f"{size_mb:.1f} MB",
        )

    console.print(table)

    if not auto and not Confirm.ask("\nLink these automatically?", default=True):
        return 0

    count = 0
    for recipe, image in matches:
        _update_recipe_image(recipe.path, image.path.name, dry_run=dry_run)
        count += 1

    return count


def _process_orphaned_image(
    image: ImageFile,
    recipes_without_images: list[RecipeMetadata],
    content_dir: Path,
    *,
    dry_run: bool,
) -> bool:
    """Process a single orphaned image interactively.

    Args:
        image: Orphaned image
        recipes_without_images: List of recipes without images
        content_dir: Path to content directory
        dry_run: If True, only preview changes

    Returns:
        True if processed, False if skipped
    """
    console.print(f"\n[bold cyan]Orphaned: {image.path.name}[/bold cyan]")
    console.print(f"[dim]Category: {image.category}[/dim]")

    # Show image preview if terminal supports it
    _display_image_preview(image.path)

    choice = Prompt.ask(
        "Action",
        choices=["fuzzy", "ignore", "skip"],
        default="fuzzy",
    )

    if choice == "skip":
        return False

    if choice == "ignore":
        reason = Prompt.ask("Reason for ignoring")
        _add_to_ignore(image.path.name, reason, content_dir, dry_run=dry_run)
        return True

    # Fuzzy search
    selected_recipe = _interactive_fuzzy_select(recipes_without_images, image.basename)

    if not selected_recipe:
        return False

    console.print(f"\n[bold]Selected: {selected_recipe.category}/{selected_recipe.basename}[/bold]")

    link_choice = Prompt.ask(
        "How to link?",
        choices=["rename", "keep"],
        default="rename",
    )

    if link_choice == "rename":
        new_name = f"{selected_recipe.basename}{image.extension}"
        new_path = selected_recipe.path.parent / new_name

        _rename_image(image.path, new_path, dry_run=dry_run)
        _update_recipe_image(selected_recipe.path, new_name, dry_run=dry_run)

        if not dry_run:
            _compress_image(new_path, dry_run=dry_run)
    else:
        _update_recipe_image(selected_recipe.path, image.path.name, dry_run=dry_run)

        if not dry_run:
            _compress_image(image.path, dry_run=dry_run)

    return True


def _process_orphaned_images(
    orphaned: list[ImageFile],
    recipes_without_images: list[RecipeMetadata],
    content_dir: Path,
    *,
    dry_run: bool,
) -> int:
    """Process all orphaned images interactively.

    Args:
        orphaned: List of orphaned images
        recipes_without_images: List of recipes without images
        content_dir: Path to content directory
        dry_run: If True, only preview changes

    Returns:
        Number of processed images
    """
    if not orphaned:
        return 0

    console.print(f"\n[bold yellow]Found {len(orphaned)} orphaned images[/bold yellow]")

    count = 0
    for image in orphaned:
        if _process_orphaned_image(
            image,
            recipes_without_images,
            content_dir,
            dry_run=dry_run,
        ):
            count += 1

    return count


def main() -> None:
    """Interactive tool to manage recipe images."""
    parser = argparse.ArgumentParser(
        description="Interactive tool to manage recipe images"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without modifying files",
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Auto-link exact matches only (no prompts)",
    )
    parser.add_argument(
        "--category",
        type=str,
        help="Only process specific category",
    )
    parser.add_argument(
        "--image",
        type=Path,
        help="Process single orphaned image",
    )
    parser.add_argument(
        "--no-preview",
        action="store_true",
        help="Disable image previews in terminal",
    )
    args = parser.parse_args()

    # Set global preview flag
    global _DISABLE_PREVIEWS
    _DISABLE_PREVIEWS = args.no_preview

    content_dir = Path("content")

    if not content_dir.exists():
        console.print("[red]Error: content directory not found[/red]")
        return

    if args.dry_run:
        console.print("[yellow]DRY RUN MODE - No files will be modified[/yellow]")

    console.print("\n[bold]Scanning content/ directory...[/bold]")

    recipes = _scan_recipes(content_dir, args.category)
    images = _scan_images(content_dir, args.category)
    ignore_list = _load_ignore_list(content_dir)

    console.print(f"  {len(recipes)} recipes, {len(images)} images")

    exact_matches = _find_exact_matches(recipes, images)
    exact_count = _process_exact_matches(
        exact_matches,
        dry_run=args.dry_run,
        auto=args.auto,
    )

    if args.auto:
        console.print(f"\n[bold green]Auto-linked {exact_count} recipes[/bold green]")
        return

    orphaned = _find_orphaned_images(images, recipes, ignore_list)
    recipes_without_images = [r for r in recipes if not r.has_image]

    orphaned_count = _process_orphaned_images(
        orphaned,
        recipes_without_images,
        content_dir,
        dry_run=args.dry_run,
    )

    console.print("\n[bold]Summary:[/bold]")
    console.print(f"  Exact matches linked: {exact_count}")
    console.print(f"  Orphaned images processed: {orphaned_count}")

    if args.dry_run:
        console.print("\n[yellow]Run without --dry-run to apply changes[/yellow]")
    else:
        console.print("\n[bold green]Done![/bold green]")


if __name__ == "__main__":
    main()
