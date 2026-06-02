# recipes

Kyle and Alex's Personal Recipes. Hosted at https://recipes.kyleking.me

## Features

- **Search:** Full-text search across all recipes
- **Related Recipes:** Semantic ingredient matching using spaCy NLP for multi-word phrase extraction

## Development Setup

### Quick Start

```bash
# Prerequisites: mise, uv, Xcode CLI (macOS) or python3-dev build-essential (Linux)
brew install mise uv
xcode-select --install  # macOS only

gh repo clone KyleKing/recipes
cd recipes

mise install
python -m spacy download en_core_web_sm
mise run test ::: build ::: serve  # Visit http://localhost:8000
```

### Common Commands

```bash
mise run                  # Interactive list of all tasks
mise run build            # Build website (format → generate → minify → index)
mise run format           # Format code
mise run format-djot      # Format djot recipe files
mise run test             # Run tests with coverage
mise run serve            # Serve built site on :8000
mise run compress <path>  # Compress images
mise run wayback          # Check/fix recipe links, add Wayback archives
```

### Browser Testing

```bash
mise run browser-install              # One-time Playwright setup
./scripts/run_browser_tests.sh        # Auto-manages server and build
mise run test-browser                 # With server already running
PWDEBUG=1 ./scripts/run_browser_tests.sh  # Debug mode with inspector
```
