#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.13"
# dependencies = [
#   "playwright==1.60.0",
#   "pytest-playwright",
# ]
# ///
"""Browser tests for recipe site interactive features.

Tests verify:
- Ingredient checkbox toggling, and that a parent never cascades to nested children
- Recipe step marking, including nested steps, via the same row model as ingredients
- Row geometry: a touch-sized label target, a separate trailing selector, no abutting targets
- Retirement: completing a step spends the ingredients it references
- Mutual selection and the ingredient dossier built from the reference substitution pages
- Editing: token handling, the offline block, and the rating/photo pull request flow
- Text selection never toggles an item
- Section collapse/expand with progress summaries
- Floating toolbar: visibility, persistence, per-button visibility rules, inertness when hidden
- localStorage persistence across reloads, 48h progress expiry, and cross-recipe sweeping
- Copying remaining ingredients as djot
- iPad landscape split layout, its floating-toolbar clearance, and the split-view toggle

Test Recipes:
- /main/fried_rice.html - Primary test recipe
- /reference/nested_list_demo.html - Nested ingredients and steps, wrapping lines, links
- /main/chickpea_tikka_masala.html - Has links within ingredients

Run with: uv run scripts/test_browser.py -v
Or via helper script: ./run_browser_tests.sh
Or via mise: mise run test-browser (requires server on :8000)

Requires: Site must be built and served on http://localhost:8000
"""

import base64
import json
import pathlib
import re

import pytest
from playwright.sync_api import Browser, Page, expect


BASE_URL = "http://localhost:8000"
TEST_RECIPE = "/main/fried_rice.html"
DEMO_RECIPE = "/reference/nested_list_demo.html"  # Nested lists, wrapping lines, links
RECIPE_WITH_LINKS = "/main/chickpea_tikka_masala.html"
KEYED_RECIPE = "/dessert/chocolate_chip_cookies.html"  # Carries `ing=` step references

IPAD_MINI_LANDSCAPE = {"width": 1133, "height": 744}
EXPIRY_MS = 48 * 60 * 60 * 1000

# Matches `--row-control` and `--row-gap` in content/styles.css
ROW_CONTROL_PX = 44
ROW_GAP_PX = 6


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


@pytest.fixture
def keyed_page(page: Page):
    """Navigate to the recipe whose steps carry explicit ingredient references."""
    return _fresh(page, KEYED_RECIPE)


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


def toggle(item) -> None:
    """Mark an item done by clicking its own label, the only target that toggles it."""
    label = item.locator("> .item-label")
    label.scroll_into_view_if_needed()
    label.click()


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

    toggle(first_ingredient)
    expect(checkbox).to_be_checked()
    expect(first_ingredient).to_have_class(re.compile("completed"))

    toggle(first_ingredient)
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
    toggle(parent)

    expect(parent_checkbox).to_be_checked()
    expect(parent.locator("ul.task-list input[type='checkbox']:checked")).to_have_count(0)


def test_nested_ingredient_does_not_toggle_parent(demo_page: Page):
    """Clicking a nested child toggles only that child."""
    parent = demo_page.locator("ul.task-list > li:has(ul.task-list)").first
    child = parent.locator("ul.task-list > li").first

    toggle(child)

    expect(child.locator("input[type='checkbox']")).to_be_checked()
    expect(parent.locator("> input[type='checkbox']")).not_to_be_checked()


def _paints_strikethrough(page: Page, selector: str) -> bool:
    """Whether the element is inside a box that paints a line-through over it.

    `text-decoration: none` on a descendant cannot undo an ancestor's line, so the
    computed style of the item itself does not answer this - walk the ancestors.
    """
    return page.evaluate(
        """(sel) => {
            var node = document.querySelector(sel);
            while (node && node !== document.body) {
                if (getComputedStyle(node).textDecorationLine.includes("line-through")) return true;
                node = node.parentElement;
            }
            return false;
        }""",
        selector,
    )


def test_completed_parent_does_not_strike_nested_children(demo_page: Page):
    """A checked parent must not paint its line-through over unchecked children."""
    parent = demo_page.locator("ul.task-list > li:has(ul.task-list)").first
    toggle(parent)
    expect(parent.locator("> input[type='checkbox']")).to_be_checked()

    child = "ul.task-list > li:has(ul.task-list) ul.task-list > li"
    assert _paints_strikethrough(demo_page, child) is False
    assert (
        _paints_strikethrough(demo_page, "ul.task-list > li:has(ul.task-list) > .item-label")
        is True
    )


def test_completed_parent_step_does_not_strike_nested_steps(demo_page: Page):
    """A completed step must not paint its line-through over its sub-steps."""
    parent_step = demo_page.locator("ol.recipe-steps > li:has(ol)").first
    toggle(parent_step)
    expect(parent_step).to_have_class(re.compile("completed"))

    assert _paints_strikethrough(demo_page, "ol.recipe-steps > li:has(ol) > ol > li") is False
    assert _paints_strikethrough(demo_page, "ol.recipe-steps > li:has(ol) > .item-label") is True


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
    label = long_item.locator("> .item-label")
    label.scroll_into_view_if_needed()
    box = label.bounding_box()
    assert box is not None

    demo_page.mouse.move(box["x"] + 30, box["y"] + 20)
    demo_page.mouse.down()
    demo_page.mouse.move(box["x"] + 260, box["y"] + 20, steps=10)
    demo_page.mouse.up()

    assert demo_page.evaluate("window.getSelection().toString().trim()") != ""
    expect(long_item.locator("input[type='checkbox']")).not_to_be_checked()


# --- Recipe steps -----------------------------------------------------------


def test_recipe_step_toggle(demo_page: Page):
    """Clicking a step's label toggles completion, the same gesture ingredients use."""
    first_step = demo_page.locator("ol.recipe-steps > li").first

    expect(first_step).not_to_have_class(re.compile("completed"))
    toggle(first_step)
    expect(first_step).to_have_class(re.compile("completed"))
    toggle(first_step)
    expect(first_step).not_to_have_class(re.compile("completed"))


def test_step_toggles_from_a_wrapped_continuation_row(demo_page: Page):
    """A step that wraps responds on its last visual row, not only its first."""
    long_step = demo_page.locator("ol.recipe-steps > li").filter(
        has_text="An intentionally long step"
    ).first
    label = long_step.locator("> .item-label")
    label.scroll_into_view_if_needed()
    box = label.bounding_box()
    assert box is not None
    assert box["height"] > 50, "expected the long step to wrap onto multiple rows"

    demo_page.mouse.click(box["x"] + 30, box["y"] + box["height"] - 10)

    expect(long_step).to_have_class(re.compile("completed"))


def test_nested_step_does_not_toggle_parent(demo_page: Page):
    """Marking a sub-step toggles the sub-step, never the enclosing step."""
    parent_step = demo_page.locator("ol.recipe-steps > li:has(ol)").first
    nested_step = parent_step.locator("ol.recipe-steps > li").first

    toggle(nested_step)

    expect(nested_step).to_have_class(re.compile("completed"))
    expect(parent_step).not_to_have_class(re.compile("completed"))


def test_parent_step_does_not_toggle_nested(demo_page: Page):
    """Marking a step that contains sub-steps leaves the sub-steps unmarked."""
    parent_step = demo_page.locator("ol.recipe-steps > li:has(ol)").first

    toggle(parent_step)

    expect(parent_step).to_have_class(re.compile("completed"))
    expect(parent_step.locator("ol.recipe-steps > li.completed")).to_have_count(0)


# --- Row geometry -----------------------------------------------------------


def test_row_targets_are_touch_sized_and_separated(keyed_page: Page):
    """Every toggle target clears the touch floor and no two adjacent targets abut."""
    measured = keyed_page.evaluate(
        """(() => {
            var labels = Array.from(document.querySelectorAll("li.recipe-row > .item-label"));
            var boxes = labels.map((el) => el.getBoundingClientRect());
            var gaps = [];
            for (var i = 1; i < boxes.length; i++) {
                var gap = boxes[i].top - boxes[i - 1].bottom;
                if (gap >= 0) gaps.push(gap);
            }
            var links = Array.from(document.querySelectorAll("li.recipe-row > .row-link"));
            return {
                count: labels.length,
                minHeight: Math.min(...boxes.map((b) => b.height)),
                minGap: Math.min(...gaps),
                linkCount: links.length,
                minLink: Math.min(...links.map((el) => {
                    var b = el.getBoundingClientRect();
                    return Math.min(b.width, b.height);
                })),
            };
        })()"""
    )
    assert measured["count"] > 0
    assert measured["linkCount"] > 0
    assert measured["minHeight"] >= ROW_CONTROL_PX
    assert measured["minLink"] >= ROW_CONTROL_PX
    assert measured["minGap"] >= ROW_GAP_PX


def test_label_text_stops_before_the_selector(keyed_page: Page):
    """The label reserves the selector's column, so a word never sits under the button."""
    encroaching = keyed_page.evaluate(
        """(() => {
            return Array.from(document.querySelectorAll("li.recipe-row")).filter((li) => {
                var link = li.querySelector(":scope > .row-link");
                if (!link) return false;
                var label = li.querySelector(":scope > .item-label");
                var linkBox = link.getBoundingClientRect();
                var range = document.createRange();
                range.selectNodeContents(label);
                return Array.from(range.getClientRects()).some((r) => r.right > linkBox.left);
            }).length;
        })()"""
    )
    assert encroaching == 0


# --- Retirement -------------------------------------------------------------


def _spent_names(page: Page) -> list[str]:
    return page.evaluate(
        """Array.from(document.querySelectorAll("ul.task-list > li.spent"))
               .map((li) => li.querySelector(".ing-ref").textContent)"""
    )


def test_completing_a_step_retires_its_ingredients(keyed_page: Page):
    """One touch on a multi-ingredient step spends every ingredient it names."""
    step = keyed_page.locator("ol.recipe-steps > li").filter(has_text="In a small bowl").first

    assert _spent_names(keyed_page) == []
    toggle(step)

    assert sorted(_spent_names(keyed_page)) == ["all-purpose flour", "baking soda", "salt"]


def test_retirement_is_reversible(keyed_page: Page):
    """Unmarking the step returns its ingredients to the unspent state."""
    step = keyed_page.locator("ol.recipe-steps > li").filter(has_text="In a small bowl").first

    toggle(step)
    assert _spent_names(keyed_page) != []
    toggle(step)
    assert _spent_names(keyed_page) == []


def test_ingredient_stays_spent_while_another_step_claims_it(keyed_page: Page):
    """Flour is used twice, so unmarking one of its steps must not un-spend it."""
    first = keyed_page.locator("ol.recipe-steps > li").filter(has_text="In a small bowl").first
    second = keyed_page.locator("ol.recipe-steps ol.recipe-steps > li").filter(
        has_text="Beat in flour"
    ).first

    toggle(first)
    toggle(second)
    toggle(first)

    assert _spent_names(keyed_page) == ["all-purpose flour"]


def test_spent_is_distinct_from_measured(keyed_page: Page):
    """Checking an ingredient means measured; retirement must not reuse that state."""
    ingredient = keyed_page.locator("ul.task-list > li").filter(has_text="baking soda").first
    step = keyed_page.locator("ol.recipe-steps > li").filter(has_text="In a small bowl").first

    toggle(step)

    expect(ingredient).to_have_class(re.compile("spent"))
    expect(ingredient).not_to_have_class(re.compile("completed"))
    expect(ingredient.locator("input[type='checkbox']")).not_to_be_checked()


# --- Selection and the ingredient dossier -----------------------------------


def select(item) -> None:
    item.locator("> .row-link").click()


def test_selecting_a_step_lists_its_amounts(keyed_page: Page):
    """The panel answers the measurement question without scrolling back up."""
    step = keyed_page.locator("ol.recipe-steps > li").filter(has_text="In a small bowl").first

    select(step)

    panel = keyed_page.locator("#recipe-panel")
    expect(panel).to_be_visible()
    expect(panel).to_contain_text("2.25 cups all-purpose flour")
    expect(panel).to_contain_text("1 tsp baking soda")


def test_selecting_a_step_lights_its_ingredients(keyed_page: Page):
    """Selection is mutual: a lit ingredient marks what the selected step uses."""
    step = keyed_page.locator("ol.recipe-steps > li").filter(has_text="In a small bowl").first

    select(step)

    expect(step).to_have_class(re.compile("selected"))
    expect(keyed_page.locator("ul.task-list > li.lit")).to_have_count(3)


def test_selecting_an_ingredient_lights_its_steps(keyed_page: Page):
    """The other direction works from the same control."""
    ingredient = keyed_page.locator("ul.task-list > li").filter(has_text="brown sugar").first

    select(ingredient)

    expect(ingredient).to_have_class(re.compile("selected"))
    expect(keyed_page.locator("ol.recipe-steps > li.lit")).to_have_count(1)


def test_only_one_row_is_selected_at_a_time(keyed_page: Page):
    """Selecting elsewhere clears the previous selection, and re-selecting clears it."""
    first = keyed_page.locator("ul.task-list > li").filter(has_text="brown sugar").first
    second = keyed_page.locator("ul.task-list > li").filter(has_text="baking soda").first

    select(first)
    select(second)
    expect(keyed_page.locator("li.selected")).to_have_count(1)
    expect(second).to_have_class(re.compile("selected"))

    select(second)
    expect(keyed_page.locator("li.selected")).to_have_count(0)
    expect(keyed_page.locator("#recipe-panel")).to_be_hidden()


def test_dossier_shows_substitutes_from_the_reference_pages(keyed_page: Page):
    """Brown sugar has an entry, so its substitute, caveat, and deep link all render."""
    ingredient = keyed_page.locator("ul.task-list > li").filter(has_text="brown sugar").first

    select(ingredient)

    panel = keyed_page.locator("#recipe-panel")
    expect(panel).to_contain_text("1 Tbsp molasses")
    expect(panel).to_contain_text("dark brown sugar")
    expect(panel.locator("a")).to_have_attribute(
        "href", "/reference/ingredient_substitutions.html#1-cup-Brown-Sugar"
    )


def test_dossier_says_when_no_substitute_is_recorded(keyed_page: Page):
    """With 22 entries against hundreds of ingredients, this is the common state."""
    ingredient = keyed_page.locator("ul.task-list > li").filter(has_text="chocolate chips").first

    select(ingredient)

    expect(keyed_page.locator("#recipe-panel")).to_contain_text("No substitute recorded")


def test_dossier_deep_link_lands_on_the_entry(keyed_page: Page):
    """The build emits the heading ids the dossier links to."""
    keyed_page.goto(BASE_URL + "/reference/ingredient_substitutions.html#1-cup-Brown-Sugar")
    expect(keyed_page.locator('[id="1-cup-Brown-Sugar"]')).to_be_visible()


# --- Persistence and expiry -------------------------------------------------


def test_ingredient_checkbox_persistence(recipe_page: Page):
    """Ingredient state survives a reload."""
    first_ingredient = recipe_page.locator("ul.task-list > li").first
    toggle(first_ingredient)
    expect(first_ingredient.locator("input[type='checkbox']")).to_be_checked()

    recipe_page.reload()

    after = recipe_page.locator("ul.task-list > li").first
    expect(after.locator("input[type='checkbox']")).to_be_checked()
    expect(after).to_have_class(re.compile("completed"))


def test_recipe_step_persistence(demo_page: Page):
    """Step completion survives a reload."""
    first_step = demo_page.locator("ol.recipe-steps > li").first
    toggle(first_step)
    expect(first_step).to_have_class(re.compile("completed"))

    demo_page.reload()

    expect(demo_page.locator("ol.recipe-steps > li").first).to_have_class(re.compile("completed"))


def test_progress_expires_and_is_erased_from_storage(demo_page: Page):
    """Progress older than 48h clears from the DOM and from localStorage."""
    toggle(demo_page.locator("ul.task-list > li").first)
    expect(demo_page.locator("input[type='checkbox']:checked")).to_have_count(1)

    age_progress(demo_page, hours=49)
    demo_page.reload()

    expect(demo_page.locator("input[type='checkbox']:checked")).to_have_count(0)
    assert "ingredient-0" not in stored_state(demo_page)


def test_progress_within_window_is_kept(demo_page: Page):
    """Progress younger than 48h is left alone."""
    toggle(demo_page.locator("ul.task-list > li").first)

    age_progress(demo_page, hours=47)
    demo_page.reload()

    expect(demo_page.locator("input[type='checkbox']:checked")).to_have_count(1)


def test_expiry_window_is_not_extended_by_collapsing(demo_page: Page):
    """Collapsing a section is not progress, so it must not restart the 48h window."""
    toggle(demo_page.locator("ul.task-list > li").first)
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
    toggle(page.locator("ul.task-list > li").first)

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
    toggle(demo_page.locator("ul.task-list > li").first)

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

    toggle(demo_page.locator("ul.task-list > li").first)
    toggle(demo_page.locator("ol.recipe-steps > li").first)

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

    toggle(demo_page.locator("ul.task-list > li").first)
    demo_page.locator("#copy-ingredients-btn").click()
    expect(demo_page.locator("#copy-ingredients-btn")).to_have_text("Copied")

    assert "- Short leaf ingredient" not in _clipboard_text(demo_page).splitlines()


def test_copy_reports_a_refused_clipboard(demo_page: Page):
    """A rejected clipboard write must say so instead of silently doing nothing."""
    demo_page.locator("#toolbar-toggle").click()
    demo_page.evaluate(
        """() => {
            navigator.clipboard.writeText = () =>
                Promise.reject(new DOMException("refused", "NotAllowedError"));
        }"""
    )

    demo_page.locator("#copy-ingredients-btn").click()

    expect(demo_page.locator("#copy-ingredients-btn")).to_have_text("Copy failed")


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
    toggle(ingredient)
    expect(ingredient.locator("input[type='checkbox']")).to_be_checked()

    ipad_page.reload()

    expect(ipad_page.locator("ul.task-list > li").first.locator("input")).to_be_checked()


def test_split_pane_ingredients_clears_the_floating_toolbar(ipad_page: Page):
    """Scrolled to its end, the ingredients pane's content must not sit under the fixed toolbar."""
    ipad_page.locator(".split-pane-ingredients").evaluate("el => el.scrollTop = el.scrollHeight")

    last_content_bottom = ipad_page.locator(".split-pane-ingredients > :last-child").last.evaluate(
        "el => el.getBoundingClientRect().bottom"
    )
    toolbar_top = ipad_page.locator("#recipe-toolbar").evaluate("el => el.getBoundingClientRect().top")
    assert last_content_bottom <= toolbar_top


def test_split_pane_body_keeps_title_inline(ipad_page: Page):
    """Title, description, and rating stay with the recipe pane instead of a separate strip."""
    expect(ipad_page.locator(".split-header")).to_have_count(0)
    expect(ipad_page.locator(".split-pane-body h1")).to_have_text("Nested List Demo")

    body_box = ipad_page.locator(".split-pane-body").evaluate("el => el.getBoundingClientRect()")
    ingredients_box = ipad_page.locator(".split-pane-ingredients").evaluate("el => el.getBoundingClientRect()")
    assert body_box["width"] > ingredients_box["width"], "steps get the wider column"
    assert body_box["right"] <= ingredients_box["left"] + 1, "ingredients sit on the right"


def test_split_toggle_btn_forces_single_column(ipad_page: Page):
    """The split-view toggle lets a user opt out even though their device qualifies."""
    main = ipad_page.locator("main")
    toggle = ipad_page.locator("#split-toggle-btn")
    expect(main).to_have_class(re.compile("split-layout"))
    expect(toggle).to_have_text("Split View: On")

    ipad_page.locator("#toolbar-toggle").click()
    toggle.click()

    expect(main).not_to_have_class(re.compile("split-layout"))
    expect(toggle).to_have_text("Split View: Off")

    ipad_page.reload()
    expect(ipad_page.locator("main")).not_to_have_class(re.compile("split-layout"))

    ipad_page.locator("#split-toggle-btn").click()
    expect(ipad_page.locator("main")).to_have_class(re.compile("split-layout"))


# --- reference converters ---------------------------------------------------


def test_measurement_converter_computes(page: Page):
    """The converter button is wired to the script that ships with the page."""
    _fresh(page, "/reference/measurement_conversions.html")
    page.locator("#inputValue").fill("2")
    page.select_option("#inputUnit", "cup")
    page.select_option("#outputUnit", "tbsp")
    page.locator("#convertMeasurementBtn").click()

    expect(page.locator("#result")).to_have_text("2 cup = 32.00 tbsp")


def test_temperature_converter_computes(page: Page):
    """The converter button is wired to the script that ships with the page."""
    _fresh(page, "/reference/oven_temperature_conversions.html")
    page.locator("#tempValue").fill("350")
    page.select_option("#tempUnit", "f")
    page.locator("#convertTempBtn").click()

    expect(page.locator("#tempResult")).to_have_text("350\u00b0F = 176.7\u00b0C")


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, *sys.argv[1:]]))


# --- Editing ----------------------------------------------------------------

GITHUB_TOKEN = "github_pat_test"
SOURCE = "content/dessert/chocolate_chip_cookies.dj"
BRANCH = "edit/dessert-chocolate_chip_cookies"


class FakeGitHub:
    """Stands in for api.github.com at the network boundary.

    Records every write so a test can assert on what would reach the repository,
    including the committed djot source and the re-encoded photo bytes.
    """

    def __init__(self, source_text: str, *, existing_pr: bool = False, branch_exists: bool = False):
        self.files = {SOURCE: {"content": source_text, "sha": "sha-source"}}
        self.commits: list[dict] = []
        self.created_branches: list[str] = []
        self.created_prs: list[dict] = []
        self.pulls = (
            [{"number": 12, "html_url": "https://github.test/pr/12", "head": {"ref": BRANCH}}]
            if existing_pr
            else []
        )
        self.branch_exists = branch_exists

    def install(self, page: Page) -> None:
        page.route("https://api.github.com/**", self._handle)

    def _json(self, route, status: int, body) -> None:
        route.fulfill(status=status, content_type="application/json", body=json.dumps(body))

    def _handle(self, route):
        request = route.request
        path = request.url.removeprefix("https://api.github.com")
        method = request.method

        if path.endswith(f"/git/ref/heads/{BRANCH}"):
            if not self.branch_exists:
                return self._json(route, 404, {"message": "Not Found"})
            return self._json(route, 200, {"object": {"sha": "sha-branch"}})

        if path.endswith("/git/ref/heads/main"):
            return self._json(route, 200, {"object": {"sha": "sha-main"}})

        if method == "POST" and path.endswith("/git/refs"):
            self.created_branches.append(json.loads(request.post_data)["ref"])
            self.branch_exists = True
            return self._json(route, 201, {})

        if path.startswith("/repos/KyleKing/recipes/contents/"):
            file_path = path.removeprefix("/repos/KyleKing/recipes/contents/").split("?")[0]
            if method == "GET":
                stored = self.files.get(file_path)
                if stored is None:
                    return self._json(route, 404, {"message": "Not Found"})
                encoded = base64.b64encode(stored["content"].encode()).decode()
                return self._json(route, 200, {"content": encoded, "sha": stored["sha"]})
            payload = json.loads(request.post_data)
            self.commits.append({"path": file_path, **payload})
            return self._json(route, 200, {"content": {}})

        if path.startswith("/repos/KyleKing/recipes/pulls"):
            if method == "GET":
                return self._json(route, 200, self.pulls)
            created = {"number": 34, "html_url": "https://github.test/pr/34"}
            self.created_prs.append(json.loads(request.post_data))
            self.pulls.append({**created, "head": {"ref": BRANCH}})
            return self._json(route, 201, created)

        return self._json(route, 404, {"message": "Unrouted: " + path})

    def committed(self, suffix: str) -> dict:
        return next(c for c in self.commits if c["path"].endswith(suffix))

    def committed_source(self) -> str:
        return base64.b64decode(self.committed(".dj")["content"]).decode()


def read_source() -> str:
    return pathlib.Path(SOURCE).read_text()


def open_editor(page: Page, *, token: str | None = GITHUB_TOKEN) -> None:
    if token is not None:
        page.evaluate(f"localStorage.setItem('recipe-github-token', {json.dumps(token)})")
    page.locator("#toolbar-toggle").click()
    page.locator("#edit-btn").click()


def test_editing_asks_for_a_token_first(keyed_page: Page):
    """With no token the dialog collects one rather than offering to save."""
    open_editor(keyed_page, token=None)

    expect(keyed_page.locator("#edit-token")).to_be_visible()
    expect(keyed_page.locator("#edit-submit")).to_have_count(0)


def test_saved_token_unlocks_the_edit_form(keyed_page: Page):
    """A stored token moves the dialog straight to the editable fields."""
    open_editor(keyed_page)

    expect(keyed_page.locator("#edit-rating")).to_be_visible()
    expect(keyed_page.locator("#edit-photo")).to_be_visible()
    expect(keyed_page.locator("#edit-token")).to_have_count(0)


def test_forgetting_the_token_clears_it_from_storage(keyed_page: Page):
    """The revoke path has to actually remove the credential, not just hide the form."""
    open_editor(keyed_page)
    keyed_page.locator("#edit-forget-token").click()

    assert keyed_page.evaluate("localStorage.getItem('recipe-github-token')") is None
    expect(keyed_page.locator("#edit-token")).to_be_visible()


def test_editing_is_blocked_offline(keyed_page: Page):
    """Nothing half-saves on the device, so with no network the dialog says so."""
    keyed_page.evaluate("Object.defineProperty(navigator, 'onLine', {get: () => false})")
    open_editor(keyed_page)

    expect(keyed_page.locator("#edit-offline")).to_be_visible()
    expect(keyed_page.locator("#edit-submit")).to_have_count(0)


def test_rating_edit_opens_a_pull_request(keyed_page: Page):
    """One rating change creates the branch, commits the djot, and opens the PR."""
    github = FakeGitHub(read_source())
    github.install(keyed_page)

    open_editor(keyed_page)
    keyed_page.locator("#edit-rating").select_option("2")
    keyed_page.locator("#edit-submit").click()

    expect(keyed_page.locator("#edit-status a")).to_have_text("Saved to pull request #34")
    assert github.created_branches == [f"refs/heads/{BRANCH}"]
    assert 'rating="2"' in github.committed_source()
    assert github.created_prs[0]["head"] == BRANCH
    assert github.created_prs[0]["base"] == "main"


def test_editing_reuses_an_open_pull_request(keyed_page: Page):
    """A second edit lands on the same branch instead of opening a rival PR."""
    github = FakeGitHub(read_source(), existing_pr=True, branch_exists=True)
    github.install(keyed_page)

    open_editor(keyed_page)
    keyed_page.locator("#edit-rating").select_option("1")
    keyed_page.locator("#edit-submit").click()

    expect(keyed_page.locator("#edit-status a")).to_have_text("Saved to pull request #12")
    assert github.created_branches == []
    assert github.created_prs == []


def test_open_pull_request_is_surfaced_on_load(page: Page):
    """Opening a recipe shows the edits already in flight for it."""
    page.goto(BASE_URL + KEYED_RECIPE)
    page.evaluate(f"localStorage.setItem('recipe-github-token', {json.dumps(GITHUB_TOKEN)})")
    FakeGitHub(read_source(), existing_pr=True).install(page)
    page.reload()

    expect(page.locator("#edit-banner a")).to_have_text("Edits in progress: pull request #12")


def test_photo_upload_is_shrunk_and_stripped(keyed_page: Page):
    """The photo is re-encoded on the device, so it arrives resized and without EXIF."""
    github = FakeGitHub(read_source())
    github.install(keyed_page)

    open_editor(keyed_page)
    keyed_page.locator("#edit-photo").set_input_files(
        files=[{
            "name": "counter.jpg",
            "mimeType": "image/jpeg",
            "buffer": _tall_jpeg_bytes(keyed_page),
        }]
    )
    keyed_page.locator("#edit-submit").click()
    expect(keyed_page.locator("#edit-status a")).to_have_text("Saved to pull request #34")

    photo = github.committed(".jpeg")
    raw = base64.b64decode(photo["content"])
    assert raw[:2] == b"\xff\xd8", "expected a JPEG"
    assert b"Exif" not in raw and b"GPS" not in raw
    assert _jpeg_height(raw) == 900, "expected the 1800px source to be halved to 900px"
    assert 'image="chocolate_chip_cookies.jpeg"' in github.committed_source()


def _tall_jpeg_bytes(page: Page) -> bytes:
    """A 1200x1800 JPEG carrying an EXIF block, built in the browser to avoid a dependency."""
    encoded = page.evaluate(
        """(async () => {
            var canvas = document.createElement("canvas");
            canvas.width = 1200;
            canvas.height = 1800;
            var ctx = canvas.getContext("2d");
            ctx.fillStyle = "#c33";
            ctx.fillRect(0, 0, 1200, 1800);
            var blob = await new Promise((r) => canvas.toBlob(r, "image/jpeg", 0.9));
            var bytes = new Uint8Array(await blob.arrayBuffer());
            var binary = "";
            bytes.forEach((b) => { binary += String.fromCharCode(b); });
            return btoa(binary);
        })()"""
    )
    jpeg = base64.b64decode(encoded)
    exif = b"Exif\x00\x00" + b"\x00" * 40
    app1 = b"\xff\xe1" + (len(exif) + 2).to_bytes(2, "big") + exif
    return jpeg[:2] + app1 + jpeg[2:]


def _jpeg_height(data: bytes) -> int:
    """Read the height out of the first start-of-frame marker."""
    i = 2
    while i < len(data):
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
            return int.from_bytes(data[i + 5 : i + 7], "big")
        i += 2 + int.from_bytes(data[i + 2 : i + 4], "big")
    raise AssertionError("no start-of-frame marker found")
