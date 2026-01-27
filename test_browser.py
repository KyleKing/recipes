#!/usr/bin/env -S uv run --quiet --script
# /// script
# dependencies = ["pytest", "pytest-playwright"]
# ///
"""Browser tests for recipe site interactive features.

Tests verify:
- Ingredient checkbox toggling and persistence
- Recipe step marking (margin click and double-click)
- Section collapse/expand with progress summaries
- Reset progress functionality
- Collapse/expand all functionality
- Toolbar visibility toggle
- localStorage persistence across page reloads
- Nested checkbox behavior
- Link clicks don't toggle checkboxes
- Multiple recipes maintain independent state

Test Recipes:
- /main/fried_rice.html - Primary test recipe
- /drinks/margarita.html - Has nested task-list (parent checkbox with nested checkboxes)
- /main/chickpea_tikka_masala.html - Has links within ingredients

Run with: uv run --with pytest --with pytest-playwright pytest test_browser.py -v
Or via helper script: ./run_browser_tests.sh
Or via mise: mise run test-browser (requires server on :8000)

Requires: Site must be built and served on http://localhost:8000
"""

import re

import pytest
from playwright.sync_api import Page, expect


BASE_URL = "http://localhost:8000"
TEST_RECIPE = "/main/fried_rice.html"  # Known recipe with ingredients and steps
RECIPE_WITH_NESTED = "/drinks/margarita.html"  # Has task-list with nested task-list
RECIPE_WITH_LINKS = "/main/chickpea_tikka_masala.html"  # Has links in ingredients


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Configure browser context with viewport size."""
    return {
        **browser_context_args,
        "viewport": {"width": 1280, "height": 720},
    }


@pytest.fixture
def recipe_page(page: Page):
    """Navigate to test recipe and clear localStorage."""
    page.goto(BASE_URL + TEST_RECIPE)
    page.evaluate("localStorage.clear()")
    page.reload()
    yield page


def test_server_is_running(page: Page):
    """Verify the local server is accessible."""
    response = page.goto(BASE_URL)
    assert response is not None
    assert response.status == 200


def test_ingredient_checkbox_toggle(recipe_page: Page):
    """Test clicking ingredient item toggles checkbox and adds strikethrough."""
    # Find first ingredient
    first_ingredient = recipe_page.locator(".task-list li").first
    checkbox = first_ingredient.locator("input[type='checkbox']")

    # Initially unchecked
    expect(checkbox).not_to_be_checked()
    expect(first_ingredient).not_to_have_class(re.compile("completed"))

    # Click ingredient (not the checkbox directly)
    first_ingredient.click()

    # Verify checked and completed class added
    expect(checkbox).to_be_checked()
    expect(first_ingredient).to_have_class(re.compile("completed"))

    # Click again to uncheck
    first_ingredient.click()
    expect(checkbox).not_to_be_checked()
    expect(first_ingredient).not_to_have_class(re.compile("completed"))


def test_ingredient_checkbox_persistence(recipe_page: Page):
    """Test ingredient checkbox state persists across page reloads."""
    first_ingredient = recipe_page.locator(".task-list li").first
    checkbox = first_ingredient.locator("input[type='checkbox']")

    # Check ingredient
    first_ingredient.click()
    expect(checkbox).to_be_checked()

    # Reload page
    recipe_page.reload()

    # State should persist
    first_ingredient_after = recipe_page.locator(".task-list li").first
    checkbox_after = first_ingredient_after.locator("input[type='checkbox']")
    expect(checkbox_after).to_be_checked()
    expect(first_ingredient_after).to_have_class(re.compile("completed"))


def test_nested_checkbox_toggle(page: Page):
    """Test that toggling parent checkbox also toggles nested checkboxes."""
    # Use recipe known to have nested checkboxes
    page.goto(BASE_URL + RECIPE_WITH_NESTED)
    page.evaluate("localStorage.clear()")
    page.reload()

    # Find an ingredient with nested items
    nested_list = page.locator(".task-list ul.task-list").first
    if nested_list.count() == 0:
        pytest.skip("No nested checkboxes in recipe")

    parent_item = page.locator(".task-list li:has(ul.task-list)").first
    parent_checkbox = parent_item.locator("> input[type='checkbox']").first
    nested_items = parent_item.locator("ul.task-list li")

    # Verify parent initially unchecked
    expect(parent_checkbox).not_to_be_checked()

    # Click parent item's em element (the text before nested list)
    # This avoids triggering the nested li closest() check in JS
    parent_em = parent_item.locator("> em").first
    parent_em.click()

    # Wait for JS to complete
    page.wait_for_timeout(100)

    # Parent should be checked
    expect(parent_checkbox).to_be_checked()

    # All nested checkboxes should also be checked
    nested_count = nested_items.count()
    for i in range(nested_count):
        nested_checkbox = nested_items.nth(i).locator("input[type='checkbox']")
        expect(nested_checkbox).to_be_checked()


def test_recipe_step_margin_click(recipe_page: Page):
    """Test clicking step margin (first 30px) toggles completion."""
    # Find section containing recipe steps
    section = recipe_page.locator("section").filter(has=recipe_page.locator("ol.recipe-steps")).first
    first_step = section.locator("ol.recipe-steps > li").first

    # Initially not completed
    expect(first_step).not_to_have_class(re.compile("completed"))

    # Click in margin (left edge, within 30px)
    # Note: JS code listens on section, not individual li elements
    box = first_step.bounding_box()
    assert box is not None
    # Click at 10px from left edge (well within 30px margin)
    section.click(position={"x": 10, "y": box["y"] - section.bounding_box()["y"] + box["height"] / 2})

    # Should be marked completed
    expect(first_step).to_have_class(re.compile("completed"))


def test_recipe_step_double_click(recipe_page: Page):
    """Test double-clicking step toggles completion."""
    first_step = recipe_page.locator("ol.recipe-steps > li").first

    # Double-click step text
    first_step.dblclick()

    # Should be marked completed
    expect(first_step).to_have_class(re.compile("completed"))

    # Double-click again to toggle off
    first_step.dblclick()
    expect(first_step).not_to_have_class(re.compile("completed"))


def test_recipe_step_persistence(recipe_page: Page):
    """Test recipe step completion persists across page reloads."""
    first_step = recipe_page.locator("ol.recipe-steps > li").first

    # Mark step complete via double-click
    first_step.dblclick()
    expect(first_step).to_have_class(re.compile("completed"))

    # Reload page
    recipe_page.reload()

    # State should persist
    first_step_after = recipe_page.locator("ol.recipe-steps > li").first
    expect(first_step_after).to_have_class(re.compile("completed"))


def test_section_collapse_toggle(recipe_page: Page):
    """Test section collapse/expand functionality."""
    # Find collapsible section (has completable content)
    collapsible_section = recipe_page.locator("section.collapsible").first
    if collapsible_section.count() == 0:
        pytest.skip("No collapsible sections in test recipe")

    toggle_button = collapsible_section.locator(".collapse-toggle")

    # Initially expanded (toggle shows "-")
    expect(toggle_button).to_have_text("-")
    expect(collapsible_section).not_to_have_class(re.compile("collapsed"))

    # Click to collapse
    toggle_button.click()

    # Wait for animation
    recipe_page.wait_for_timeout(500)

    # Should be collapsed (toggle shows "+")
    expect(toggle_button).to_have_text("+")
    expect(collapsible_section).to_have_class(re.compile("collapsed"))

    # Click to expand
    toggle_button.click()
    expect(toggle_button).to_have_text("-")
    expect(collapsible_section).not_to_have_class(re.compile("collapsed"))


def test_section_progress_summary(recipe_page: Page):
    """Test section shows progress summary when collapsed."""
    collapsible_section = recipe_page.locator("section.collapsible").first
    if collapsible_section.count() == 0:
        pytest.skip("No collapsible sections in test recipe")

    # Mark some items complete
    first_item = collapsible_section.locator(
        ".task-list li, ol.recipe-steps > li"
    ).first
    first_item.click()

    # Collapse section
    toggle_button = collapsible_section.locator(".collapse-toggle")
    toggle_button.click()
    recipe_page.wait_for_timeout(500)

    # Should show progress summary like "(1/5)"
    summary = collapsible_section.locator(".section-summary")
    expect(summary).to_be_visible()
    expect(summary).to_contain_text("/")


def test_collapse_all_button(recipe_page: Page):
    """Test collapse all / expand all button."""
    collapse_button = recipe_page.locator("#toggle-collapse-btn")

    if collapse_button.count() == 0:
        pytest.skip("No collapsible sections in test recipe")

    # Button should say "Collapse All" initially
    expect(collapse_button).to_contain_text("Collapse All")

    # Click to collapse all
    collapse_button.click()
    recipe_page.wait_for_timeout(500)

    # All collapsible sections should be collapsed
    all_sections = recipe_page.locator("section.collapsible")
    collapsed_sections = recipe_page.locator("section.collapsed")
    expect(collapsed_sections).to_have_count(all_sections.count())

    # Button should now say "Expand All"
    expect(collapse_button).to_contain_text("Expand All")

    # Click to expand all
    collapse_button.click()

    # No sections should be collapsed
    expect(recipe_page.locator("section.collapsed")).to_have_count(0)
    expect(collapse_button).to_contain_text("Collapse All")


def test_reset_progress_button(recipe_page: Page):
    """Test reset button clears all progress."""
    reset_button = recipe_page.locator("#reset-btn")

    # Mark some items complete
    first_ingredient = recipe_page.locator(".task-list li").first
    first_step = recipe_page.locator("ol.recipe-steps > li").first

    first_ingredient.click()
    first_step.dblclick()

    # Reset button should be visible
    expect(reset_button).to_be_visible()

    # Click reset
    reset_button.click()

    # All checkboxes should be unchecked
    expect(recipe_page.locator("input[type='checkbox']:checked")).to_have_count(0)

    # No completed steps
    expect(recipe_page.locator("ol.recipe-steps > li.completed")).to_have_count(0)

    # Reset button should be hidden
    expect(reset_button).to_be_hidden()


def test_toolbar_toggle(recipe_page: Page):
    """Test toolbar visibility toggle."""
    toolbar = recipe_page.locator("#recipe-toolbar")
    toggle_button = recipe_page.locator("#toolbar-toggle")

    if toolbar.count() == 0 or toggle_button.count() == 0:
        pytest.skip("No toolbar in test recipe")

    # Initially visible
    expect(toolbar).not_to_have_class(re.compile("hidden"))

    # Click to hide
    toggle_button.click()
    expect(toolbar).to_have_class(re.compile("hidden"))

    # Click to show
    toggle_button.click()
    expect(toolbar).not_to_have_class(re.compile("hidden"))


def test_toolbar_toggle_persistence(recipe_page: Page):
    """Test toolbar visibility persists across page reloads."""
    toolbar = recipe_page.locator("#recipe-toolbar")
    toggle_button = recipe_page.locator("#toolbar-toggle")

    if toolbar.count() == 0 or toggle_button.count() == 0:
        pytest.skip("No toolbar in test recipe")

    # Hide toolbar
    toggle_button.click()
    expect(toolbar).to_have_class(re.compile("hidden"))

    # Reload page
    recipe_page.reload()

    # Should still be hidden
    toolbar_after = recipe_page.locator("#recipe-toolbar")
    expect(toolbar_after).to_have_class(re.compile("hidden"))


def test_header_anchors(recipe_page: Page):
    """Test header anchor links work and scroll to section."""
    # Find first header anchor
    anchor = recipe_page.locator(".header-anchor").first

    if anchor.count() == 0:
        pytest.skip("No header anchors in test recipe")

    # Click anchor
    anchor.click()

    # URL should have hash
    expect(recipe_page).to_have_url(re.compile("#.+"))


def test_link_clicks_dont_toggle_checkboxes(page: Page):
    """Test clicking links inside ingredients doesn't toggle checkbox."""
    # Use recipe known to have links in ingredients
    page.goto(BASE_URL + RECIPE_WITH_LINKS)
    page.evaluate("localStorage.clear()")
    page.reload()

    # Find ingredient with a link
    ingredient_with_link = page.locator(".task-list li:has(a)").first

    # Verify we found an ingredient with a link
    link = ingredient_with_link.locator("a").first
    if link.count() == 0:
        pytest.skip("No ingredient with link in recipe")

    # Find checkbox in same list item
    checkbox = ingredient_with_link.locator("input[type='checkbox']").first

    # Verify checkbox initially unchecked
    expect(checkbox).not_to_be_checked()

    # Prevent link navigation so we can verify checkbox state
    page.evaluate("document.querySelectorAll('a').forEach(a => a.addEventListener('click', e => e.preventDefault()))")

    # Click link (should not toggle checkbox due to JS check: if (e.target.tagName === "A") return;)
    link.click()

    # Checkbox should still be unchecked (not toggled by click)
    expect(checkbox).not_to_be_checked()


def test_multiple_recipes_independent_state(page: Page):
    """Test that different recipes maintain independent localStorage state."""
    # Visit first recipe
    page.goto(BASE_URL + TEST_RECIPE)
    page.evaluate("localStorage.clear()")
    page.reload()

    first_ingredient = page.locator(".task-list li").first
    first_ingredient.click()

    # Visit second recipe (use known different recipe)
    page.goto(BASE_URL + RECIPE_WITH_NESTED)

    # Second recipe should have no checked items
    expect(page.locator("input[type='checkbox']:checked")).to_have_count(0)

    # Go back to first recipe
    page.goto(BASE_URL + TEST_RECIPE)

    # First ingredient should still be checked
    first_ingredient_after = page.locator(".task-list li").first
    checkbox_after = first_ingredient_after.locator("input[type='checkbox']")
    expect(checkbox_after).to_be_checked()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
