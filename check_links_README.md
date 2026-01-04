# Link Checker Script

Checks and fixes links in recipe markdown files by verifying availability and adding Wayback Machine archive links.

## Features

- Checks all links in `.dj` files
- Verifies if links are still accessible
- Searches Wayback Machine for archived versions
- Updates links based on availability:
  - **Working link**: adds web archive permalink after original
  - **Only archive works**: replaces with archive link
  - **Neither works**: adds note in parenthesis but keeps original

## Usage

```bash
# Preview changes without modifying files
./check_links.py --dry-run

# Apply changes to all files
./check_links.py

# Check a single file
./check_links.py --file content/bread/pretzels.dj

# Dry-run on a single file
./check_links.py --dry-run --file content/bread/pretzels.dj
```

## Requirements

- Python 3.11+
- `uv` (for dependency management)

The script uses uv's inline script metadata, so dependencies are automatically installed when you run it.

## How It Works

1. Scans all `.dj` files in the `content/` directory
2. Extracts markdown-style links `[text](url)`
3. For each link:
   - Checks if the original URL is accessible
   - Queries the Wayback Machine for archived versions
   - Determines the best action based on availability
4. Creates replacements following these rules:
   - Live link + archive exists → Add `([archive](wayback_url))` after link
   - Dead link + archive exists → Replace with `[text](wayback_url)`
   - Dead link + no archive → Add `(link unavailable)` after link
   - Live link + no archive → No change needed

## Example Output

```
Found 1 recipe file
DRY RUN MODE - No files will be modified
Checking: http://example.com/recipe

Would update pretzels.dj:
  - [http://example.com/...](http://example.com/recipe)
  + [http://example.com/...](http://example.com/recipe) ([archive](http://web.archive.org/web/...))

Summary (Dry Run)
┏━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━┓
┃ File        ┃ Changes ┃ Status    ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━┩
│ pretzels.dj │       1 │ ✓1 📦0 ✗0 │
└─────────────┴─────────┴───────────┘

Status Legend:
✓ = Live links with archive added
📦 = Dead links replaced with archive
✗ = Dead links with no archive found
```

## Notes

- The script respects rate limits for the Wayback Machine API (1 second delay between requests)
- Already archived links (containing `web.archive.org`) are skipped
- The script uses a 10-second timeout for HTTP requests
- Links are checked with HEAD requests first, falling back to GET if needed
