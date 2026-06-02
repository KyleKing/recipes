# recipes

Kyle and Alex's Personal Recipes. Hosted at https://recipes.kyleking.me

## Features

- **Search:** Full-text search across all recipes
- **Related Recipes:** Semantic ingredient matching using spaCy NLP for multi-word phrase extraction

## Development Setup

### Prerequisites

Required tools:

- [mise](https://mise.jdx.dev/) - Development environment manager
- [uv](https://github.com/astral-sh/uv) - Python package manager
- System dependencies:
    - macOS: Python development headers (via Xcode Command Line Tools)
    - Linux: `python3-dev pkg-config build-essential`

### Initial Setup on a New Laptop

1. **Clone the repository:**

    ```bash
    git clone https://github.com/KyleKing/recipes.git
    cd recipes
    ```

2. **Install mise:**

    ```bash
    # macOS
    brew install mise

    # Or follow https://mise.jdx.dev/getting-started.html
    ```

3. **Install uv:**

    ```bash
    # macOS/Linux
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

4. **Install system dependencies (macOS):**

    ```bash
    # Xcode Command Line Tools (provides Python headers)
    xcode-select --install
    ```

5. **Install project dependencies:**

    ```bash
    # Install tools via mise (Go, Python, Node packages)
    mise install

    # Install Python dependencies and spaCy model
    uv sync
    uv run python -m spacy download en_core_web_sm
    ```

6. **Build the C++ wrapper for go-spacy:**

    ```bash
    # This creates lib/libspacy_wrapper.dylib (macOS) or lib/libspacy_wrapper.so (Linux)
    ./scripts/setup-spacy.sh

    # Source the generated .env file to set environment variables for local development
    source .env
    ```

7. **Run tests to verify setup:**

    ```bash
    mise run test
    ```

8. **Build the site:**

    ```bash
    mise run build
    ```

9. **Serve locally:**
    ```bash
    mise run serve
    # Visit http://localhost:8000
    ```

### Common Commands

```bash
mise run build        # Build website (format → go run . → minify → pagefind index)
mise run format       # Format code (templ generate → templ fmt → go fmt)
mise run format-djot  # Format djot recipe files (djot-fmt)
mise run test         # Run tests with coverage
mise run serve        # Serve built site on port 8000

mise run compress <path>   # Compress images
./check_links.py          # Check/fix recipe links, add Wayback archive links
```

### Browser Testing

Browser tests verify interactive features using Python + Playwright.

```bash
# One-time setup
mise run browser-install

# Run tests (auto-manages server and build)
./scripts/run_browser_tests.sh

# Or with server already running on :8000
mise run test-browser

# Run a single test
uv run --with pytest --with pytest-playwright pytest scripts/test_browser.py::test_ingredient_checkbox_toggle -v
```

**Debugging options:**

```bash
# See the browser while tests run
uv run --with pytest --with pytest-playwright pytest scripts/test_browser.py --headed --slowmo 1000

# Playwright inspector
PWDEBUG=1 uv run --with pytest --with pytest-playwright pytest scripts/test_browser.py
```

**What's tested:** ingredient checkbox toggling and localStorage persistence, recipe step marking (margin click and double-click), section collapse/expand with progress summaries, reset progress, collapse all / expand all, toolbar toggle, header anchors, and multi-recipe state independence.

### Troubleshooting

**C++ compilation errors:**

- Ensure Python development headers are installed (`python3-config --includes` should work)
- Run `./scripts/setup-spacy.sh` to rebuild the C++ wrapper
- Check that `lib/libspacy_wrapper.dylib` (macOS) or `lib/libspacy_wrapper.so` (Linux) exists

**Missing Python dependencies:**

- Run `uv sync` to install Python packages
- Run `uv run python -m spacy download en_core_web_sm` to install spaCy model

**mise tool installation issues:**

- Run `mise doctor` to diagnose issues
- Run `mise install` to reinstall tools
