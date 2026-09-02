#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///
"""Backfill explicit ingredient references into djot recipes.

Adds `[name]{ ing="key" }` to every ingredient in the Ingredients section and to every
mention of one in the Recipe steps, which is what binds a step to the ingredients it
spends. Name matching is only good enough as an authoring aid, so this writes a first pass
for review rather than a finished answer: run it, read the diff, fix what it missed.

    uv run scripts/_backfill_ingredient_refs.py --report content/dessert
    uv run scripts/_backfill_ingredient_refs.py content/dessert/carrot_cake.dj

Already-keyed lines are left exactly as they are, so a hand-corrected file survives a rerun.
"""

import argparse
import json
import pathlib
import re
import sys
import unicodedata


SUBSTITUTIONS = pathlib.Path("public/_static/substitutions.json")

UNITS = {
    "bag", "bags", "batch", "block", "bottle", "box", "bunch", "bunches", "c", "can", "cans",
    "clove", "cloves", "container", "cube", "cubes", "cup", "cups", "dash", "ear", "ears",
    "envelope", "g", "gallon", "gram", "grams", "handful", "head", "heads", "inch", "jar",
    "jars", "kg", "l", "lb", "lbs", "leaf", "leaves", "liter", "liters", "loaf", "ml", "oz",
    "ounce", "ounces", "package", "packages", "packet", "pinch", "pint", "pkg", "pound",
    "pounds", "quart", "quarts", "recipe", "scoop", "sheet", "sheets", "slice", "slices",
    "block", "blocks", "sprig", "sprigs", "stalk", "stalks", "stick", "sticks", "tbsp", "tbsps", "tablespoon",
    "tablespoons", "tsp", "tsps", "teaspoon", "teaspoons", "tin", "wedge", "wedges",
}
# Only size and freshness. Words like "ground" or "smoked" belong to the ingredient's name.
LEADING_ADJECTIVES = {"extra", "extra-large", "fresh", "freshly", "jumbo", "large", "medium", "small"}
FILLER = {"a", "an", "about", "and", "approx", "of", "or", "plus", "roughly", "some", "to"}

# Recipes write amounts as "1/2", "1⁄2", and "½" alike. Missing the unicode forms
# leaves the unit inside the wrapped name, which keys the ingredient by its measurement.
FRACTIONS = "½¼¾⅓⅔⅛⅜⅝⅞"
QUANTITY = re.compile(rf"^[~≈]?[\d{FRACTIONS}]+([./⁄x×-][\d{FRACTIONS}]+)*(\s+\d+[/⁄]\d+)?\s*")
PARENTHETICAL = re.compile(r"^\([^)]*\)\s*")
WORD = re.compile(r"^[A-Za-z][\w'-]*\s*")
# `[text]{...}` and `[text](...)` are already spoken for; never wrap inside one.
PROTECTED = re.compile(r"\[[^\]]*\]\s*[({][^)}]*[)}]")
TRAILING_NOISE = re.compile(
    r"(\s*,.*"
    r"|\s+(to taste|as needed|if using|for (serving|garnish|topping|dusting|greasing|the .*))"
    r"|\s+\(optional\)|\s+optional|\s+divided)+$",
    re.IGNORECASE,
)
TASK_ITEM = re.compile(r"^(\s*)-\s+\[[ xX]\]\s+")
STEP_ITEM = re.compile(r"^\s*\d+\.\s+")
HEADING = re.compile(r"^(#+)\s+(.*)$")


def strip_quantity(text: str) -> int:
    """Offset in `text` where the ingredient's own name starts."""
    i = 0
    while i < len(text):
        rest = text[i:]
        for pattern in (QUANTITY, PARENTHETICAL):
            if match := pattern.match(rest):
                i += match.end()
                break
        else:
            match = WORD.match(rest)
            if not match:
                break
            word = match.group().strip().lower().rstrip(".")
            if word in UNITS or word in FILLER or word in LEADING_ADJECTIVES:
                i += match.end()
                continue
            break
    return i


def ingredient_span(body: str) -> tuple[int, int] | None:
    """Bounds of the ingredient name inside one task-item body, or None if nothing survives."""
    start = strip_quantity(body)
    end = len(body)
    if match := TRAILING_NOISE.search(body[start:]):
        end = start + match.start()

    # A trailing parenthetical is a note about the ingredient, never part of its name
    if (paren := body.find(" (", start)) != -1 and paren < end:
        end = paren
    # "lemon juice or 1/2 tsp pure lemon extract" names one ingredient twice, and "Everything
    # Seasoning from Trader Joe's" trails a source. Cut at either, but only once enough has
    # been read to be a name rather than an adjective
    for match in re.finditer(r"\s+(or|from|with|in|for)\s+", body[start:end]):
        if len(body[start : start + match.start()].split()) >= 2:
            end = start + match.start()
            break
    # "moist, plump raisins": a lone word before a comma is describing what follows it
    if (comma := body.find(", ", start)) != -1 and comma < end and len(body[start:comma].split()) == 1:
        start = comma + 2

    name = body[start:end].strip()
    if not name or not re.search(r"[A-Za-z]", name):
        return None
    # Djot markup inside the wrapped text would nest a span in a span
    if any(ch in name for ch in "[]{}*_`"):
        return None
    # A long phrase keys off its tail, which is the part a step actually repeats
    words = name.split()
    if len(words) > 4:
        tail = " ".join(words[-3:])
        start = body.rindex(tail, start, end)
        return start, start + len(tail)
    return start, start + len(body[start:end].rstrip())


def key_for(name: str, known: set[str]) -> str:
    # Decompose so an accent drops rather than becoming a hyphen, which spelled jalapeño
    # as "jalape-o" and hid it from every lookup keyed by the ingredient's name
    decomposed = unicodedata.normalize("NFKD", name.lower())
    folded = "".join(c for c in decomposed if not unicodedata.combining(c))
    slug = re.sub(r"[^a-z0-9]+", "-", folded).strip("-")
    if slug in known:
        return slug
    # Snap to the reference pages' spelling so a substitution is actually found
    for variant in (slug.rstrip("s"), f"{slug}s", f"{slug}es"):
        if variant in known:
            return variant
    return slug


def aliases_for(name: str) -> list[str]:
    """Ways a step is likely to name this ingredient, longest first."""
    words = name.split()
    forms = {name}
    if len(words) > 1:
        forms.add(words[-1])
    if len(words) > 2:
        forms.add(" ".join(words[-2:]))
    for form in list(forms):
        forms.add(form.rstrip("s") if form.endswith("s") else f"{form}s")
    return sorted((f for f in forms if len(f) > 2), key=len, reverse=True)


def free_regions(line: str) -> list[tuple[int, int]]:
    """Stretches of the line not already inside a span or a link."""
    regions, cursor = [], 0
    for match in PROTECTED.finditer(line):
        if match.start() > cursor:
            regions.append((cursor, match.start()))
        cursor = match.end()
    if cursor < len(line):
        regions.append((cursor, len(line)))
    return regions


def annotate_step(line: str, index: list[tuple[str, str]], used: set[str]) -> tuple[str, bool]:
    """Wrap each ingredient this step is the first to name.

    `used` carries the keys earlier steps already claimed and gains the ones this step takes.
    """
    edits = []
    for lo, hi in free_regions(line):
        segment = line[lo:hi]
        taken: list[tuple[int, int]] = []
        for alias, key in index:
            if key in used:
                continue
            for match in re.finditer(rf"\b{re.escape(alias)}\b", segment, re.IGNORECASE):
                if any(s < match.end() and match.start() < e for s, e in taken):
                    continue
                taken.append((match.start(), match.end()))
                edits.append((lo + match.start(), lo + match.end(), key))
                used.add(key)
                break
    if not edits:
        return line, False
    out, cursor = [], 0
    for start, end, key in sorted(edits):
        out.append(line[cursor:start])
        out.append(f'[{line[start:end]}]{{ ing="{key}" }}')
        cursor = end
    out.append(line[cursor:])
    return "".join(out), True


def process(text: str, known: set[str]) -> tuple[str, dict]:
    lines = text.split("\n")
    section = ""
    declared: dict[str, str] = {}
    stats = {"ingredients": 0, "keyed": 0, "steps": 0, "bound": 0}

    for i, line in enumerate(lines):
        if match := HEADING.match(line):
            if len(match.group(1)) == 2:
                section = match.group(2).strip().lower()
            continue
        if section != "ingredients":
            continue
        item = TASK_ITEM.match(line)
        if not item:
            continue
        stats["ingredients"] += 1
        body = line[item.end() :]
        if "ing=" in body:
            stats["keyed"] += 1
            for name, key in re.findall(r'\[([^\]]+)\]\s*\{\s*ing="([^"]+)"', body):
                declared[name.lower()] = key.split()[0]
            continue
        span = ingredient_span(body)
        if span is None:
            continue
        name = body[span[0] : span[1]]
        key = key_for(name, known)
        declared[name.lower()] = key
        lines[i] = line[: item.end()] + body[: span[0]] + f'[{name}]{{ ing="{key}" }}' + body[span[1] :]
        stats["keyed"] += 1

    index = sorted(
        {(alias, key) for name, key in declared.items() for alias in aliases_for(name)},
        key=lambda pair: len(pair[0]),
        reverse=True,
    )
    section = ""
    used: set[str] = set()
    for i, line in enumerate(lines):
        if match := HEADING.match(line):
            if len(match.group(1)) == 2:
                section = match.group(2).strip().lower()
            continue
        if section != "recipe" or not STEP_ITEM.match(line):
            continue
        stats["steps"] += 1
        if "ing=" in line:
            stats["bound"] += 1
            used.update(k for keys in re.findall(r'ing="([^"]+)"', line) for k in keys.split())
            continue
        updated, changed = annotate_step(line, index, used)
        lines[i] = updated
        stats["bound"] += int(changed)

    return "\n".join(lines), stats


def djot_files(paths: list[str]) -> list[pathlib.Path]:
    found = []
    for raw in paths:
        path = pathlib.Path(raw)
        found.extend(sorted(path.rglob("*.dj")) if path.is_dir() else [path])
    return [p for p in found if not p.name.startswith("_")]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", help="Recipe files or directories")
    parser.add_argument("--report", action="store_true", help="Print coverage without writing")
    args = parser.parse_args()

    known = set(json.loads(SUBSTITUTIONS.read_text())) if SUBSTITUTIONS.exists() else set()
    totals = {"ingredients": 0, "keyed": 0, "steps": 0, "bound": 0}

    for path in djot_files(args.paths):
        text = path.read_text()
        updated, stats = process(text, known)
        for field in totals:
            totals[field] += stats[field]
        if args.report:
            if stats["ingredients"]:
                print(
                    f"{stats['keyed']:>3}/{stats['ingredients']:<3} ingredients "
                    f"{stats['bound']:>3}/{stats['steps']:<3} steps  {path}"
                )
        elif updated != text:
            path.write_text(updated)

    def pct(part: int, whole: int) -> str:
        return f"{100 * part / whole:.1f}%" if whole else "n/a"

    print(
        f"\ningredients keyed {totals['keyed']}/{totals['ingredients']} ({pct(totals['keyed'], totals['ingredients'])})"
        f"   steps bound {totals['bound']}/{totals['steps']} ({pct(totals['bound'], totals['steps'])})",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
