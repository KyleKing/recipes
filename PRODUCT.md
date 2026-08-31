# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Kyle and Alex, cooking. Two known people following a recipe they have already
chosen and usually already made before, reading from a phone or an iPad propped
up in the kitchen, hands wet or covered in flour, glancing at the screen between
actions rather than reading it continuously. Friends and family occasionally
receive a link, but the site is not designed for them.

## Product Purpose

A personal collection of 295 recipes, kept as Djot source files and published as
a static site at https://recipes.kyleking.me. It exists so the two of them can
find a recipe they have made before, cook from it without losing their place,
and record whether it was worth repeating.

## Positioning

The recipes are their own: written in their words, ordered the way they actually
cook, and rated from having made them. A public recipe site optimizes for
strangers arriving from search; this one optimizes for the second and tenth time
the same two people cook the same dish.

## Operating Context

- Cooking happens at the counter with a phone or iPad, not at a desk. Landscape
  iPad is a first-class scene: the page splits into a steps pane and an
  ingredients reference rail
- Recipes are short enough to hold in view. Ingredients run 1 / 12 / 21 / 59
  (min, median, p90, max) and steps run 1 / 6 / 11 / 28, so seeing the whole
  recipe at once and reading ahead is a real and frequent task
- Progress is tracked in the browser: ingredients check off, steps mark as done,
  sections collapse. State lives in `localStorage` and expires 48h after the
  last progress change. Crossing items off works and is worth preserving
- Recipes are authored by hand in `.dj` files with a metadata block carrying
  `rating`, `image`, and an optional `search` flag. Ingredients are listed in
  preparation order and grouped by component when the recipe has distinct parts
- Source URLs are preserved and paired with Wayback snapshots so a dead link
  does not lose the original

## Capabilities and Constraints

- Static output only: Go + templ generate HTML from Djot, then minify, then
  Pagefind indexes it. No JS framework and no runtime dependencies. This is
  binding
- Interactive behavior is one vanilla `content/_static/recipe.js` plus one
  `content/styles.css`; browser tests (Playwright) cover the toggling, expiry,
  and split-layout rules
- Related recipes are computed at build time by spaCy ingredient matching, and
  each match exposes its own score breakdown
- Full-text search is Pagefind; a recipe can opt out of the index while keeping
  the interactive toolbar
- The build fails on a missing metadata block, a missing image file, or a broken
  internal link
- The `.dj` authoring format may change, including a one-time scripted migration
  across all 295 files, when a design genuinely needs it
- Editing from the counter is a requirement, not a nicety: notes, ratings,
  photos, ingredients, and steps must all be changeable from the phone or iPad,
  because a change decided while cooking and not written down is lost. Confirmed
  approach: a fine-grained token scoped to this repo's contents and pull
  requests, pasted once per device and held in `localStorage`. GitHub's device
  flow was ruled out because it cannot be called from a browser and would
  require a server this project will not have
- Edits land as a pull request per recipe, on a branch that accumulates commits,
  so unsent work lives on GitHub rather than on one phone
- Photos are resized and re-encoded on the device before upload. A canvas
  re-encode carries no metadata at all, so GPS is gone before the file leaves
  the phone, which is why no cloud intermediary is used. EXIF orientation must
  be read and applied before drawing, or phone photos upload sideways. Target
  900px height, matching `mise run compress`
- Known gap: substituting an ingredient means leaving the site and searching by
  hand, and measurement conversion lives on a reference page instead of where it
  is needed. The build already extracts ingredient tokens with spaCy for related-recipe
  matching, and two converters (measurement, oven temperature) already exist, so
  the material for resolving a substitution in place is present and unused
- Known defect: the two lists use opposite touch models. An ingredient toggles
  from anywhere on its line, while a step toggles only inside a narrow left band
  and the rest of the row is inert. Adjacent step zones abut with no separation,
  and a coarse-pointer ingredient row is about 42px tall, under the 44px floor.
  No second action can be added to a row until this is rebuilt
- Name matching binds a step to its ingredients for only 72% of steps, which is
  not good enough. Steps will carry explicit ingredient references in the source,
  backfilled by a scripted migration across all 295 files

## Brand Commitments

- Name: "Kyle and Alex's Personal Recipes"
- Typeface: Atkinson Hyperlegible Next and Atkinson Hyperlegible Mono, chosen
  for legibility, self-hosted from `content/resources/`
- The CSS lineage is deliberately minimal-document ("better motherfucking
  website", Practical Typography, natural-selection boilerplate). Restraint is a
  standing preference, not an accident

## Evidence on Hand

- 295 `.dj` recipes across 14 category directories. 195 carry a Notes section,
  115 group ingredients under `###` subheads, 19 use nested ingredient lists,
  and 56 use nested sub-steps
- 123 recipes are unrated and 138 have no photo, so the empty rating and the
  placeholder image are the common case rather than the edge
- The longest single step is 797 characters, in `content/dessert/carrot_cake.dj`
- `content/reference/nested_list_demo.dj` exists only as a browser-test fixture
  for hard click-handling cases
- No analytics, no user accounts, no traffic data, and no testimonials. Future
  work must not invent usage numbers or an audience

## Product Principles

- The kitchen is the design constraint. Glanceable beats dense; a recipe read
  from three feet away with wet hands is the real test
- Show the whole recipe. Reading ahead is part of cooking, so nothing that hides
  the remaining work earns its place
- Never lose the cook's place. Progress, position, and state survive
  interruption
- Source stays plain text. The recipes outlive any rendering of them
- Restraint over decoration. Nothing on the page that does not help someone cook
  or decide what to cook
- Honest ratings, including bad ones, and honest provenance for every recipe
- A decision made at the counter should be capturable at the counter. What is
  not written down while cooking is lost

## Accessibility & Inclusion

Legibility is a deliberate product choice, not a checkbox: the Atkinson
Hyperlegible family, generous body size, and high-contrast text. Targets must
work for a coarse pointer with imprecise, wet fingers.
