# Browser Testing Guide

Browser tests verify interactive features using Python + Playwright.

## Quick Start

```bash
# 1. One-time setup: Install Playwright browsers
mise run browser-install

# 2. Run tests (easiest - auto-manages server and build)
./run_browser_tests.sh

# Or using mise (requires server already running on :8000):
mise run test-browser

# Or direct uv command (requires server):
uv run --with pytest --with pytest-playwright pytest test_browser.py -v
```

## What's Tested

The test suite verifies:

- **Ingredient Checkboxes**: Click to toggle, strikethrough, localStorage persistence
- **Recipe Steps**: Margin click (first 30px) and double-click to mark complete
- **Section Collapse/Expand**: Toggle with progress summaries (X/Y completed)
- **Reset Progress**: Clears all checkboxes and step completion
- **Collapse All / Expand All**: Batch operations on sections
- **Toolbar Toggle**: Show/hide with persistence
- **Header Anchors**: Clickable # links to sections
- **Multi-Recipe Independence**: Different recipes maintain separate state

## Running Specific Tests

```bash
# Run single test
uv run --with pytest --with pytest-playwright pytest test_browser.py::test_ingredient_checkbox_toggle -v

# Run all tests matching pattern
uv run --with pytest --with pytest-playwright pytest test_browser.py -k "checkbox" -v

# Run in headed mode (see browser)
uv run --with pytest --with pytest-playwright pytest test_browser.py --headed

# Run with slowmo for debugging
uv run --with pytest --with pytest-playwright pytest test_browser.py --headed --slowmo 1000

# Using the helper script (auto server):
./run_browser_tests.sh test_browser.py::test_ingredient_checkbox_toggle
```

## Test Recipes

Tests use multiple recipes to cover different features:

- **`/main/fried_rice.html`** - Primary test recipe with ingredients, steps, collapsible sections
- **`/drinks/margarita.html`** - Has task-list with nested task-list (parent checkbox with nested checkboxes)
- **`/main/chickpea_tikka_masala.html`** - Has links within ingredients

## Debugging Failed Tests

```bash
# Run with Playwright's debugger
uv run --with pytest --with pytest-playwright pytest test_browser.py --headed --pdb-trace

# Generate trace for debugging
PWDEBUG=1 uv run --with pytest --with pytest-playwright pytest test_browser.py

# Take screenshot on failure
uv run --with pytest --with pytest-playwright pytest test_browser.py --screenshot=on
```

## Architecture

- **test_browser.py**: Main test suite using pytest + Playwright (16 tests total)
- **run_browser_tests.sh**: Helper script that manages server lifecycle
- **mise.toml**: Task definitions for browser testing
- Uses `uv run --with` for dependency management (no pyproject.toml or requirements.txt needed)

## Adding New Tests

```python
def test_new_feature(recipe_page: Page):
    """Test description."""
    # recipe_page fixture provides:
    # - Navigation to test recipe
    # - Cleared localStorage
    # - Page object ready to use

    element = recipe_page.locator("#some-element")
    element.click()
    expect(element).to_be_visible()
```

## CI/CD Integration

For GitHub Actions or other CI:

```yaml
- name: Install Playwright browsers
  run: mise run browser-install

- name: Run browser tests
  run: ./run_browser_tests.sh
```

## Test Results

Current status: **16 passed, 0 skipped**

All interactive features are tested:

- Ingredient checkboxes (toggle, persistence, nested)
- Recipe steps (margin click, double-click, persistence)
- Section collapse/expand with progress summaries
- Reset progress, collapse all, toolbar toggle
- Link clicks don't trigger checkbox toggle
- Multiple recipes maintain independent localStorage state
