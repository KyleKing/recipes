# Browser Testing Guide

Browser tests verify interactive features using Python + Playwright.

## Quick Start

```bash
# 1. One-time setup: Install Playwright browsers
mise run browser-install

# 2. Build the site
mise run build

# 3. Run tests (easiest method - auto-manages server)
mise run test-browser-auto

# Or manually (requires server running):
# Terminal 1:
mise run serve

# Terminal 2:
mise run test-browser
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
uv run pytest test_browser.py::test_ingredient_checkbox_toggle -v

# Run all tests matching pattern
uv run pytest test_browser.py -k "checkbox" -v

# Run with verbose output
uv run pytest test_browser.py -vv

# Run in headed mode (see browser)
uv run pytest test_browser.py --headed

# Run with slowmo for debugging
uv run pytest test_browser.py --headed --slowmo 1000
```

## Test Recipe

Tests use `/main/fried_rice.html` as the test recipe because it contains:
- Multiple ingredients with checkboxes
- Nested ingredient lists
- Multiple recipe steps
- Multiple collapsible sections

## Debugging Failed Tests

```bash
# Run with Playwright's debugger
uv run pytest test_browser.py --headed --pdb-trace

# Generate trace for debugging
PWDEBUG=1 uv run pytest test_browser.py

# Take screenshot on failure (add to pytest.ini if desired)
uv run pytest test_browser.py --screenshot=on
```

## Architecture

- **test_browser.py**: Main test suite using pytest + Playwright
- **run_browser_tests.sh**: Helper script that manages server lifecycle
- **mise.toml**: Task definitions for browser testing
- Uses `uv` inline script dependencies (no separate requirements.txt needed)

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

- name: Build site
  run: mise run build

- name: Run browser tests
  run: mise run test-browser-auto
```
