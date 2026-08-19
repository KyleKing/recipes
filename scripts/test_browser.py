#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.13"
# dependencies = [
#   "pytest-playwright",
# ]
# ///
"""Browser tests for recipe site interactive features.

Tests verify:
- Ingredient checkbox toggling, and that a parent never cascades to nested children
- Recipe step marking via the left click zone and via double-click, including nested steps
- Click zone width, its touch-sized variant, and the post-toggle highlight affordance
- Text selection never toggles an item
- Section collapse/expand with progress summaries
- Floating toolbar: visibility, persistence, per-button visibility rules, inertness when hidden
- localStorage persistence across reloads, 48h progress expiry, and cross-recipe sweeping
- Copying remaining ingredients as djot
- iPad landscape split layout

Test Recipes:
- /main/fried_rice.html - Primary test recipe
- /reference/nested_list_demo.html - Nested ingredients and steps, wrapping lines, links
- /main/chickpea_tikka_masala.html - Has links within ingredients

Run with: uv run scripts/test_browser.py -v
Or via helper script: ./run_browser_tests.sh
Or via mise: mise run test-browser (requires server on :8000)

Requires: Site must be built and served on http://localhost:8000
"""

import json
import re

import pytest
from playwright.sync_api import Browser, Page, expect


BASE_URL = "http://localhost:8000"
TEST_RECIPE = "/main/fried_rice.html"
DEMO_RECIPE = "/reference/nested_list_demo.html"  # Nested lists, wrapping lines, links
RECIPE_WITH_LINKS = "/main/chickpea_tikka_masala.html"

IPAD_MINI_LANDSCAPE = {"width": 1133, "height": 744}
EXPIRY_MS = 48 * 60 * 60 * 1000

# Matches the JS constants in content/_static/recipe.js
STEP_ZONE_PX = 30
STEP_ZONE_TOUCH_PX = 44


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Configure browser context with viewport size."""
    return {
        **browser_context_args,
        "viewport": {"width": 1280, "height": 720},
    }


def _fresh(page: Page, path: str) -> Page:
    page.goto(BASE_URL + path)
    page.evaluate("localStorage.clear()")
    page.reload()
    return page


@pytest.fixture
def recipe_page(page: Page):
    """Navigate to test recipe and clear localStorage."""
    return _fresh(page, TEST_RECIPE)


@pytest.fixture
def demo_page(page: Page):
    """Navigate to the nested-list demo recipe and clear localStorage."""
    return _fresh(page, DEMO_RECIPE)


def storage_key(page: Page) -> str:
    return page.evaluate("`recipe-progress-${location.pathname}`")


def stored_state(page: Page) -> dict:
    raw = page.evaluate(f"localStorage.getItem({json.dumps(storage_key(page))})")
    return json.loads(raw) if raw else {}


def age_progress(page: Page, hours: float, key: str | None = None) -> None:
    """Backdate the progress timestamp so the next load sees it as expired."""
    target = key or storage_key(page)
    page.evaluate(
        """([key, hours]) => {
            var s = JSON.parse(localStorage.getItem(key));
            s._progressAt = Date.now() - hours * 60 * 60 * 1000;
            localStorage.setItem(key, JSON.stringify(s));
        }""",
        [target, hours],
    )


def click_step_at(page: Page, step, offset_x: float, offset_y: float | None = None) -> None:
    """Click a step `offset_x` px from its own left edge, `offset_y` px from its top.

    A step containing sub-steps is only its own first row; the rows below it belong to
    the nested list, so pass `offset_y` to target a specific row.
    """
    step.scroll_into_view_if_needed()
    box = step.bounding_box()
    assert box is not None
    y = box["y"] + (box["height"] / 2 if offset_y is None else offset_y)
    page.mouse.click(box["x"] + offset_x, y)


def test_server_is_running(page: Page):
    """Verify the local server is accessible."""
    response = page.goto(BASE_URL)
    assert response is not None
    assert response.status == 200


# --- Ingredients ------------------------------------------------------------


def test_ingredient_checkbox_toggle(recipe_page: Page):
    """Clicking an ingredient toggles its checkbox and strikethrough."""
    first_ingredient = recipe_page.locator("ul.task-list > li").first
    checkbox = first_ingredient.locator("input[type='checkbox']")

    expect(checkbox).not_to_be_checked()
    expect(first_ingredient).not_to_have_class(re.compile("completed"))

    first_ingredient.click()
    expect(checkbox).to_be_checked()
    expect(first_ingredient).to_have_class(re.compile("completed"))

    first_ingredient.click()
    expect(checkbox).not_to_be_checked()
    expect(first_ingredient).not_to_have_class(re.compile("completed"))


def test_ingredient_parent_does_not_cascade_to_nested(demo_page: Page):
    """Clicking a parent ingredient leaves its nested children untouched."""
    parent = demo_page.locator("ul.task-list > li:has(ul.task-list)").first
    parent_checkbox = parent.locator("> input[type='checkbox']")
    nested = parent.locator("ul.task-list input[type='checkbox']")

    expect(parent_checkbox).not_to_be_checked()
    expect(nested).to_have_count(3)

    # Click the parent's own text row, above the nested list
    parent.click(position={"x": 40, "y": 8})

    expect(parent_checkbox).to_be_checked()
    expect(parent.locator("ul.task-list input[type='checkbox']:checked")).to_have_count(0)


def test_nested_ingredient_does_not_toggle_parent(demo_page: Page):
    """Clicking a nested child toggles only that child."""
    parent = demo_page.locator("ul.task-list > li:has(ul.task-list)").first
    child = parent.locator("ul.task-list > li").first

    child.click()

    expect(child.locator("input[type='checkbox']")).to_be_checked()
    expect(parent.locator("> input[type='checkbox']")).not_to_be_checked()


def test_link_clicks_dont_toggle_checkboxes(page: Page):
    """Clicking a link inside an ingredient does not toggle its checkbox."""
    _fresh(page, RECIPE_WITH_LINKS)

    ingredient_with_link = page.locator("ul.task-list > li:has(a)").first
    link = ingredient_with_link.locator("a").first
    checkbox = ingredient_with_link.locator("input[type='checkbox']").first

    expect(checkbox).not_to_be_checked()

    page.evaluate(
        "document.querySelectorAll('a').forEach(a => a.addEventListener('click', e => e.preventDefault()))"
    )
    link.click()

    expect(checkbox).not_to_be_checked()


def test_text_selection_does_not_toggle_ingredient(demo_page: Page):
    """Dragging to select ingredient text must not check the item off."""
    long_item = demo_page.locator("ul.task-list > li").nth(1)
    long_item.scroll_into_view_if_needed()
    box = long_item.bounding_box()
    assert box is not None

    demo_page.mouse.move(box["x"] + 30, box["y"] + 8)
    demo_page.mouse.down()
    demo_page.mouse.move(box["x"] + 260, box["y"] + 8, steps=10)
    demo_page.mouse.up()

    assert demo_page.evaluate("window.getSelection().toString().trim()") != ""
    expect(long_item.locator("input[type='checkbox']")).not_to_be_checked()


# --- Recipe steps -----------------------------------------------------------


def test_recipe_step_margin_click(demo_page: Page):
    """Clicking the left zone of a step toggles completion."""
    first_step = demo_page.locator("ol.recipe-steps > li").first

    expect(first_step).not_to_have_class(re.compile("completed"))
    click_step_at(demo_page, first_step, 5)
    expect(first_step).to_have_class(re.compile("completed"))


def test_step_click_beyond_zone_does_not_toggle(demo_page: Page):
    """Clicking in the body of a step leaves it alone, so text stays selectable."""
    first_step = demo_page.locator("ol.recipe-steps > li").first

    click_step_at(demo_page, first_step, STEP_ZONE_PX + 20)

    expect(first_step).not_to_have_class(re.compile("completed"))


def test_nested_step_click_does_not_toggle_parent(demo_page: Page):
    """Clicking a sub-step's zone toggles the sub-step, never the enclosing step."""
    parent_step = demo_page.locator("ol.recipe-steps > li:has(ol)").first
    nested_step = parent_step.locator("ol.recipe-steps > li").first

    click_step_at(demo_page, nested_step, 5)

    expect(nested_step).to_have_class(re.compile("completed"))
    expect(parent_step).not_to_have_class(re.compile("completed"))


def test_parent_step_click_does_not_toggle_nested(demo_page: Page):
    """Toggling a step that contains sub-steps leaves the sub-steps unmarked."""
    parent_step = demo_page.locator("ol.recipe-steps > li:has(ol)").first
    nested_steps = parent_step.locator("ol.recipe-steps > li")

    # The parent owns only its first row; lower rows are occupied by the nested list
    click_step_at(demo_page, parent_step, 5, offset_y=10)

    expect(parent_step).to_have_class(re.compile("completed"))
    expect(parent_step.locator("ol.recipe-steps > li.completed")).to_have_count(0)
    expect(nested_steps).to_have_count(2)


def test_nested_marker_column_targets_the_nested_step(demo_page: Page):
    """On a nested row, the parent's text column is where the sub-step's number is drawn,
    so a click there belongs to the sub-step rather than falling through to the parent."""
    parent_step = demo_page.locator("ol.recipe-steps > li:has(ol)").first
    nested_step = parent_step.locator("ol.recipe-steps > li").first

    nested_step.scroll_into_view_if_needed()
    parent_box = parent_step.bounding_box()
    nested_box = nested_step.bounding_box()
    assert parent_box is not None and nested_box is not None

    demo_page.mouse.click(parent_box["x"] + 5, nested_box["y"] + nested_box["height"] / 2)

    expect(nested_step).to_have_class(re.compile("completed"))
    expect(parent_step).not_to_have_class(re.compile("completed"))


def test_parent_step_zone_ends_at_its_nested_list(demo_page: Page):
    """The parent's own gutter is dead on rows occupied by its sub-steps."""
    parent_step = demo_page.locator("ol.recipe-steps > li:has(ol)").first
    nested_step = parent_step.locator("ol.recipe-steps > li").first

    nested_step.scroll_into_view_if_needed()
    outer_ol_left = demo_page.evaluate(
        "document.querySelector('ol.recipe-steps').getBoundingClientRect().left"
    )
    nested_box = nested_step.bounding_box()
    assert nested_box is not None

    # The outer list's marker gutter, on a row that belongs to the nested list
    demo_page.mouse.click(outer_ol_left + 5, nested_box["y"] + nested_box["height"] / 2)

    expect(demo_page.locator("ol.recipe-steps li.completed")).to_have_count(0)


def test_step_zone_highlight_stops_at_nested_list(demo_page: Page):
    """The tint shows the real clickable band, so a parent's tint excludes its sub-steps."""
    parent_step = demo_page.locator("ol.recipe-steps > li:has(ol)").first
    click_step_at(demo_page, parent_step, 5, offset_y=10)
    demo_page.wait_for_timeout(400)

    measured = demo_page.evaluate(
        """(() => {
            var li = document.querySelector('ol.recipe-steps > li:has(ol)');
            var nested = li.querySelector(':scope > ol');
            return {
                tint: parseFloat(getComputedStyle(li, '::before').height),
                own: nested.getBoundingClientRect().top - li.getBoundingClientRect().top,
                full: li.getBoundingClientRect().height,
            };
        })()"""
    )
    assert measured["own"] < measured["full"], "expected the parent to be taller than its own row"
    assert abs(measured["tint"] - measured["own"]) < 2


def test_step_zone_click_on_wrapped_row(demo_page: Page):
    """The click zone covers continuation rows of a step that wraps."""
    long_step = demo_page.locator("ol.recipe-steps > li").filter(
        has_text="An intentionally long step"
    ).first
    long_step.scroll_into_view_if_needed()
    box = long_step.bounding_box()
    assert box is not None
    assert box["height"] > 50, "expected the long step to wrap onto multiple rows"

    # Click the last visual row rather than the first
    demo_page.mouse.click(box["x"] + 5, box["y"] + box["height"] - 8)

    expect(long_step).to_have_class(re.compile("completed"))


def test_step_zone_is_wider_on_touch(browser: Browser):
    """A coarse pointer gets a wider zone than a mouse at the same offset."""
    offset = (STEP_ZONE_PX + STEP_ZONE_TOUCH_PX) / 2  # inside touch zone, outside mouse zone

    results = {}
    for label, touch in (("mouse", False), ("touch", True)):
        context = browser.new_context(viewport={"width": 1280, "height": 900}, has_touch=touch)
        page = context.new_page()
        _fresh(page, DEMO_RECIPE)
        step = page.locator("ol.recipe-steps > li").first
        click_step_at(page, step, offset)
        page.wait_for_timeout(100)
        results[label] = "completed" in (step.get_attribute("class") or "")
        context.close()

    assert results == {"mouse": False, "touch": True}


def test_step_toggle_flashes_click_zones(demo_page: Page):
    """Toggling a step highlights every step's click zone, then clears it."""
    first_step = demo_page.locator("ol.recipe-steps > li").first

    assert demo_page.evaluate("document.body.classList.contains('show-step-zones')") is False

    click_step_at(demo_page, first_step, 5)
    assert demo_page.evaluate("document.body.classList.contains('show-step-zones')") is True
    # The tint fades in over a transition, so let it settle before reading opacity
    demo_page.wait_for_timeout(400)
    assert (
        demo_page.evaluate(
            "getComputedStyle(document.querySelector('ol.recipe-steps > li'), '::before').opacity"
        )
        == "1"
    )

    demo_page.wait_for_function(
        "() => !document.body.classList.contains('show-step-zones')", timeout=5000
    )


def test_selection_clears_step_zone_highlight(demo_page: Page):
    """Starting a text selection cancels the click-zone highlight."""
    first_step = demo_page.locator("ol.recipe-steps > li").first
    click_step_at(demo_page, first_step, 5)
    assert demo_page.evaluate("document.body.classList.contains('show-step-zones')") is True

    long_step = demo_page.locator("ol.recipe-steps > li").nth(2)
    long_step.scroll_into_view_if_needed()
    box = long_step.bounding_box()
    assert box is not None
    demo_page.mouse.move(box["x"] + 60, box["y"] + 8)
    demo_page.mouse.down()
    demo_page.mouse.move(box["x"] + 300, box["y"] + 8, steps=10)
    demo_page.mouse.up()

    assert demo_page.evaluate("document.body.classList.contains('show-step-zones')") is False


def test_recipe_step_double_click(demo_page: Page):
    """Double-clicking a step's text toggles completion."""
    first_step = demo_page.locator("ol.recipe-steps > li").first

    first_step.dblclick()
    expect(first_step).to_have_class(re.compile("completed"))

    first_step.dblclick()
    expect(first_step).not_to_have_class(re.compile("completed"))


# --- Persistence and expiry -------------------------------------------------


def test_ingredient_checkbox_persistence(recipe_page: Page):
    """Ingredient state survives a reload."""
    first_ingredient = recipe_page.locator("ul.task-list > li").first
    first_ingredient.click()
    expect(first_ingredient.locator("input[type='checkbox']")).to_be_checked()

    recipe_page.reload()

    after = recipe_page.locator("ul.task-list > li").first
    expect(after.locator("input[type='checkbox']")).to_be_checked()
    expect(after).to_have_class(re.compile("completed"))


def test_recipe_step_persistence(demo_page: Page):
    """Step completion survives a reload."""
    first_step = demo_page.locator("ol.recipe-steps > li").first
    first_step.dblclick()
    expect(first_step).to_have_class(re.compile("completed"))

    demo_page.reload()

    expect(demo_page.locator("ol.recipe-steps > li").first).to_have_class(re.compile("completed"))


def test_progress_expires_and_is_erased_from_storage(demo_page: Page):
    """Progress older than 48h clears from the DOM and from localStorage."""
    demo_page.locator("ul.task-list > li").first.click()
    expect(demo_page.locator("input[type='checkbox']:checked")).to_have_count(1)

    age_progress(demo_page, hours=49)
    demo_page.reload()

    expect(demo_page.locator("input[type='checkbox']:checked")).to_have_count(0)
    assert "ingredient-0" not in stored_state(demo_page)


def test_progress_within_window_is_kept(demo_page: Page):
    """Progress younger than 48h is left alone."""
    demo_page.locator("ul.task-list > li").first.click()

    age_progress(demo_page, hours=47)
    demo_page.reload()

    expect(demo_page.locator("input[type='checkbox']:checked")).to_have_count(1)


def test_expiry_window_is_not_extended_by_collapsing(demo_page: Page):
    """Collapsing a section is not progress, so it must not restart the 48h window."""
    demo_page.locator("ul.task-list > li").first.click()
    age_progress(demo_page, hours=47.9)
    before = stored_state(demo_page)["_progressAt"]

    demo_page.locator("section.collapsible .collapse-toggle").first.click()
    demo_page.wait_for_timeout(500)

    assert stored_state(demo_page)["_progressAt"] == before


def test_stale_keys_for_other_recipes_are_swept(demo_page: Page):
    """Visiting any recipe purges expired progress left behind by other recipes."""
    stale_key = "recipe-progress-/main/some_other_recipe.html"
    demo_page.evaluate(
        """([key, ms]) => localStorage.setItem(key, JSON.stringify({
            "ingredient-0": true,
            _progressAt: Date.now() - ms - 1000,
            _savedAt: Date.now() - ms - 1000,
        }))""",
        [stale_key, EXPIRY_MS],
    )
    fresh_key = "recipe-progress-/main/recent_recipe.html"
    demo_page.evaluate(
        """(key) => localStorage.setItem(key, JSON.stringify({
            "ingredient-0": true, _progressAt: Date.now(), _savedAt: Date.now(),
        }))""",
        fresh_key,
    )

    demo_page.reload()

    assert demo_page.evaluate(f"localStorage.getItem({json.dumps(stale_key)})") is None
    assert demo_page.evaluate(f"localStorage.getItem({json.dumps(fresh_key)})") is not None


def test_multiple_recipes_independent_state(page: Page):
    """Different recipes keep independent localStorage state."""
    _fresh(page, TEST_RECIPE)
    page.locator("ul.task-list > li").first.click()

    page.goto(BASE_URL + DEMO_RECIPE)
    expect(page.locator("input[type='checkbox']:checked")).to_have_count(0)

    page.goto(BASE_URL + TEST_RECIPE)
    expect(page.locator("ul.task-list > li").first.locator("input[type='checkbox']")).to_be_checked()


# --- Sections ---------------------------------------------------------------


def test_section_collapse_toggle(demo_page: Page):
    """Sections start expanded and toggle on click."""
    section = demo_page.locator("section.collapsible").first
    toggle = section.locator(".collapse-toggle")

    expect(toggle).to_have_text("-")
    expect(section).not_to_have_class(re.compile("collapsed"))

    toggle.click()
    demo_page.wait_for_timeout(500)
    expect(toggle).to_have_text("+")
    expect(section).to_have_class(re.compile("collapsed"))

    toggle.click()
    expect(toggle).to_have_text("-")
    expect(section).not_to_have_class(re.compile("collapsed"))


def test_section_collapse_persistence(demo_page: Page):
    """Collapsed sections stay collapsed across a reload."""
    section = demo_page.locator("section.collapsible").first
    section.locator(".collapse-toggle").click()
    demo_page.wait_for_timeout(500)
    expect(section).to_have_class(re.compile("collapsed"))

    demo_page.reload()

    expect(demo_page.locator("section.collapsible").first).to_have_class(re.compile("collapsed"))


def test_section_progress_summary(demo_page: Page):
    """A collapsed section reports its completed/total counts."""
    section = demo_page.locator("section.collapsible").first
    demo_page.locator("ul.task-list > li").first.click()

    section.locator(".collapse-toggle").click()
    demo_page.wait_for_timeout(500)

    summary = section.locator(".section-summary")
    expect(summary).to_be_visible()
    expect(summary).to_contain_text("/")


def test_collapse_all_button(demo_page: Page):
    """Collapse all / expand all flips every collapsible section."""
    demo_page.locator("#toolbar-toggle").click()
    button = demo_page.locator("#toggle-collapse-btn")
    all_sections = demo_page.locator("section.collapsible")

    expect(button).to_contain_text("Collapse All")
    expect(demo_page.locator("section.collapsed")).to_have_count(0)

    button.click()
    demo_page.wait_for_timeout(500)
    expect(demo_page.locator("section.collapsed")).to_have_count(all_sections.count())
    expect(button).to_contain_text("Expand All")

    button.click()
    expect(demo_page.locator("section.collapsed")).to_have_count(0)
    expect(button).to_contain_text("Collapse All")


def test_header_anchors(demo_page: Page):
    """Header anchors put the section id in the URL."""
    demo_page.locator(".header-anchor").first.click()
    expect(demo_page).to_have_url(re.compile("#.+"))


# --- Floating toolbar -------------------------------------------------------


def test_toolbar_toggle(demo_page: Page):
    """The floating panel opens and closes."""
    toolbar = demo_page.locator("#recipe-toolbar")
    toggle = demo_page.locator("#toolbar-toggle")

    expect(toolbar).to_have_class(re.compile("hidden"))

    toggle.click()
    expect(toolbar).not_to_have_class(re.compile("hidden"))

    toggle.click()
    expect(toolbar).to_have_class(re.compile("hidden"))


def test_toolbar_toggle_persistence(demo_page: Page):
    """Panel visibility survives a reload."""
    demo_page.locator("#toolbar-toggle").click()
    expect(demo_page.locator("#recipe-toolbar")).not_to_have_class(re.compile("hidden"))

    demo_page.reload()

    expect(demo_page.locator("#recipe-toolbar")).not_to_have_class(re.compile("hidden"))


def test_toolbar_buttons_are_inert_when_hidden(demo_page: Page):
    """A hidden panel must not intercept clicks meant for the page."""
    expect(demo_page.locator("#recipe-toolbar")).to_have_class(re.compile("hidden"))

    assert (
        demo_page.evaluate(
            "getComputedStyle(document.getElementById('toolbar-buttons')).pointerEvents"
        )
        == "none"
    )


def test_toolbar_stays_fixed_while_scrolling(demo_page: Page):
    """The panel is pinned to the viewport, not the document."""
    toggle = demo_page.locator("#toolbar-toggle")
    before = toggle.bounding_box()

    demo_page.mouse.wheel(0, 600)
    demo_page.wait_for_timeout(200)

    after = toggle.bounding_box()
    assert before is not None and after is not None
    assert abs(before["y"] - after["y"]) < 1


def test_reset_progress_button(demo_page: Page):
    """Reset appears once there is progress, clears it, then hides again."""
    demo_page.locator("#toolbar-toggle").click()
    reset_button = demo_page.locator("#reset-btn")

    expect(reset_button).to_be_hidden()

    demo_page.locator("ul.task-list > li").first.click()
    click_step_at(demo_page, demo_page.locator("ol.recipe-steps > li").first, 5)

    expect(reset_button).to_be_visible()
    reset_button.click()

    expect(demo_page.locator("input[type='checkbox']:checked")).to_have_count(0)
    expect(demo_page.locator("ol.recipe-steps li.completed")).to_have_count(0)
    expect(reset_button).to_be_hidden()
    assert "ingredient-0" not in stored_state(demo_page)


# --- Copy ingredients -------------------------------------------------------


def _clipboard_text(page: Page) -> str:
    return page.evaluate("navigator.clipboard.readText()")


def test_copy_ingredients_writes_djot(demo_page: Page):
    """Copy emits every unchecked ingredient as a flat djot bullet list."""
    demo_page.context.grant_permissions(["clipboard-read", "clipboard-write"])
    demo_page.locator("#toolbar-toggle").click()

    demo_page.locator("#copy-ingredients-btn").click()
    expect(demo_page.locator("#copy-ingredients-btn")).to_have_text("Copied")

    lines = _clipboard_text(demo_page).splitlines()
    assert lines[0] == "- Short leaf ingredient"
    assert "- First nested child" in lines
    assert "- Grouped ingredient two" in lines
    assert all(line.startswith("- ") for line in lines)
    # Nested children are flattened, not indented, and the parent keeps only its own text
    assert "- Parent with nested children" in lines


def test_copy_ingredients_omits_checked(demo_page: Page):
    """Crossed-out ingredients are left out of the copied list."""
    demo_page.context.grant_permissions(["clipboard-read", "clipboard-write"])
    demo_page.locator("#toolbar-toggle").click()

    demo_page.locator("ul.task-list > li").first.click()
    demo_page.locator("#copy-ingredients-btn").click()
    expect(demo_page.locator("#copy-ingredients-btn")).to_have_text("Copied")

    assert "- Short leaf ingredient" not in _clipboard_text(demo_page).splitlines()


def test_copy_button_absent_without_ingredients(page: Page):
    """A page with no task list does not offer the copy action."""
    _fresh(page, "/reference/vegetable_cuts.html")
    page.locator("#toolbar-toggle").click()

    if page.locator("ul.task-list li").count() > 0:
        pytest.skip("reference page unexpectedly has a task list")
    expect(page.locator("#copy-ingredients-btn")).to_be_hidden()


# --- iPad split layout ------------------------------------------------------


@pytest.fixture
def ipad_page(browser: Browser):
    """An iPad Mini sized, touch-capable landscape page."""
    context = browser.new_context(viewport=IPAD_MINI_LANDSCAPE, has_touch=True)
    page = context.new_page()
    yield _fresh(page, DEMO_RECIPE)
    context.close()


def test_split_layout_on_ipad_landscape(ipad_page: Page):
    """Landscape tablets get ingredients and the rest of the recipe side by side."""
    main = ipad_page.locator("main")
    expect(main).to_have_class(re.compile("split-layout"))

    left = ipad_page.locator(".split-pane-ingredients > section")
    assert left.count() > 0
    assert ipad_page.evaluate(
        "Array.from(document.querySelectorAll('.split-pane-ingredients > section')).map(s => s.id)"
    ) == ["Ingredients", "Sub-Group"]

    boxes = ipad_page.evaluate(
        """Array.from(document.querySelectorAll('.split-pane')).map(p => {
            var r = p.getBoundingClientRect();
            return {left: r.left, right: r.right, overflow: getComputedStyle(p).overflowY};
        })"""
    )
    assert len(boxes) == 2
    assert boxes[0]["right"] <= boxes[1]["left"] + 1, "panes must sit side by side"
    assert all(b["overflow"] == "auto" for b in boxes), "each pane scrolls on its own"


def test_split_layout_uses_full_width(ipad_page: Page):
    """The split layout drops the narrow reading column and fills the screen."""
    width = ipad_page.evaluate("document.querySelector('main').getBoundingClientRect().width")
    assert width > IPAD_MINI_LANDSCAPE["width"] * 0.9


def test_split_layout_absent_on_desktop(demo_page: Page):
    """A desktop browser keeps the single-column layout at any window size."""
    expect(demo_page.locator("main")).not_to_have_class(re.compile("split-layout"))
    expect(demo_page.locator(".split-pane")).to_have_count(0)


def test_split_layout_absent_in_portrait(browser: Browser):
    """A tablet held in portrait keeps the single-column layout."""
    context = browser.new_context(
        viewport={"width": IPAD_MINI_LANDSCAPE["height"], "height": IPAD_MINI_LANDSCAPE["width"]},
        has_touch=True,
    )
    page = context.new_page()
    _fresh(page, DEMO_RECIPE)

    expect(page.locator("main")).not_to_have_class(re.compile("split-layout"))
    context.close()


def test_split_layout_keeps_progress_working(ipad_page: Page):
    """Re-parenting sections into panes must not break toggling or persistence."""
    ingredient = ipad_page.locator("ul.task-list > li").first
    ingredient.click()
    expect(ingredient.locator("input[type='checkbox']")).to_be_checked()

    ipad_page.reload()

    expect(ipad_page.locator("ul.task-list > li").first.locator("input")).to_be_checked()


if __name__ == "__main__":
    import sys

    pytest.main([__file__, *sys.argv[1:]])
