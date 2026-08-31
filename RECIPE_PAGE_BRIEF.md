# Recipe page: design brief

Produced by `/impeccable shape`. No code was written. `PRODUCT.md` holds the
durable product truth behind this; this file holds the strategy for one surface.

## Job and audience

Kyle and Alex, mid-cook, phone or iPad on the counter, wet hands, dish already
chosen and usually made before. Visitor mode is Operate. The cooking layout
works and is not being restructured. Two things change: following a step, and
capturing what you decide while cooking.

## Outcome and proof

Following a step never costs a scroll back for a number. Marking progress takes
one confident touch that lands where it was aimed. A decision made at the
counter (halve the sugar, a photo of how it actually came out, a 4 instead of a
3) gets written down before it is forgotten, and survives the phone.

Success is a recipe cooked without scrolling up, without a mis-tap, and with the
one change you decided already committed.

Most of the material exists already: ingredients authored in preparation order,
spaCy ingredient tokens computed at build time, two converters that render on
the wrong page, and 22 substitution entries across three reference files.

## Selected direction

The visual world is inherited unchanged: Atkinson Hyperlegible Next and Mono,
`#eaeaea` ground, `#454545` ink, `#07a` links, minimal-document CSS. This
direction was pinned by the user, so no concept roll was taken.

A row is a control with two actions, and a recipe is a document you write back
to. The page supports neither today. The work is one foundation, three reading
features, and one writing pipeline.

### Foundation: one touch model

Ingredients and steps share one geometry. A primary toggle target of at least
44px, real separation so no two adjacent targets abut, and a distinct secondary
target per row.

This is the prerequisite for everything else. Today an ingredient toggles from
anywhere on its line (`recipe.js:192`) while a step toggles only inside a narrow
left band with the rest of the row inert (`recipe.js:228-234`,
`styles.css:403-415`), and no second action can be added to a row until that is
rebuilt. The `show-step-zones` hint exists to teach an invisible affordance, so
deleting it is the test that the redesign worked.

### Reading: three ingredient states

`unmeasured` -> `measured` -> `spent`. Checking an ingredient means it has been
measured out. Completing a step marks the ingredients that step consumed as
spent. These are distinct states with distinct treatments, and retirement must
not reuse the checkbox.

### Reading: retire on complete

Marking a step done retires its ingredients. One touch retires three, which is
how cooking actually goes. Reversible, and an ingredient stays individually
toggleable.

### Reading: the ingredient dossier

On the secondary target: general substitutes for that ingredient, the
measurement conversion, and the other recipes using it.

Substitutes come from the existing reference pages, parsed at build time. Their
shape is already right: `### <amount> <ingredient>[, <use qualifier>]`, the list
underneath is the substitution, the trailing prose is the caveat. Use variation
is already encoded (`### 1 cup Heavy Cream, for cooking`), so it is carried
through rather than invented.

Recipe-inline alternatives ("canola or safflower oil") need no UI. They are
prose and stay prose.

With 22 entries against a few hundred distinct ingredients, "no substitute
known" is the common state, not the edge. That state offers to add one, which
edits the reference `.dj` through the same pipeline as any other edit.

### Reading: both ways, kept simple

One selection at a time, mutual. Selecting a step lights its ingredients;
selecting an ingredient lights the steps that use it. Selecting anything else,
or the same thing again, clears it. No modes and no second gesture to learn.

### Writing

Notes, rating, and photos edit in place. Ingredients and steps require an
explicit edit mode, so a wet-handed cooking touch can never mutate a recipe.

Edits accumulate on a per-recipe branch and land as one open pull request, so
unsent work lives on GitHub rather than on one device. Opening a recipe lazily
fetches the open PRs in a single request, matches them by title, and surfaces
any in-progress edits on the page.

Auth is a fine-grained token scoped to this repository's contents and pull
requests, pasted once per device and held in `localStorage`, with a visible
revoke that clears it. GitHub's device flow was ruled out: it cannot be called
from a browser and would need a server this project will not have.

Photos are resized to 900px height and re-encoded on the device. A canvas
re-encode carries no metadata, so GPS is gone before the file leaves the phone,
which is why no cloud intermediary is used. EXIF orientation must be read and
applied before drawing, or phone photos upload sideways.

### Focal moment

Finishing a step and watching its ingredients retire themselves. The page does
bookkeeping currently held in the cook's head.

## Scope and boundaries

In scope: ingredients, steps, their touch model, the dossier, both-ways
selection, inline editing, the photo pipeline, the PR pipeline, and whatever
toolbar change they require.

Untouched: nav, home, category indexes, search, filters, related recipes.

Anti-goals:

- no framework and no server, including for auth
- no cloud intermediary for photos, which would move un-stripped GPS off the
  device for no gain
- no cook mode and nothing that hides remaining work
- no duplicated quantities in the source; one place to edit stays the rule
- no gamification and no celebration states

## States and ranges

Measured from the 295 recipes:

- ingredients run 1 / 12 / 21 / 59 (min, median, p90, max)
- steps run 1 / 6 / 11 / 28
- 48% of steps use more than one ingredient, so multi-ingredient retirement is
  the common case
- 115 recipes group ingredients under `###` subheads and 56 use nested
  sub-steps, so retirement respects the existing no-cascade rule both ways
- 123 recipes are unrated and 138 have no photo, which makes "add the first
  photo" a main editing path rather than an edge

Also material: no token present (the page is fully read-only and says so), a
token revoked upstream, an open PR already existing for this recipe, an edit
made offline on bad kitchen wifi, an ingredient with no known substitute, and a
unit that does not convert.

## Interaction and layout

One target model across both lists, sized for a wet finger and visibly
separated. Toggling stays non-cascading between parents and children.
Retirement is reversible and a spent ingredient stays distinguishable from a
measured one. The dossier opens from a target that cannot be confused with the
toggle and dismisses without touching progress. Edit mode for ingredients and
steps is entered deliberately and is unmistakably different from reading.

In the iPad split layout, an ingredient retiring in the right pane because of a
step touched in the left pane has to be perceivable, since it happens outside
where the cook is looking.

## Constraints and open decisions

Binding: static output, no framework, no server, and the Playwright suite either
passes or is deliberately rewritten.

Two build changes are prerequisites rather than nice-to-haves:

- steps gain explicit ingredient references in the source, backfilled by a
  scripted migration across 295 files with the 59 low-coverage recipes checked
  by hand. Name matching binds only 72% of steps, which is not good enough
- headings get ids at build time. They are injected at runtime today
  (`recipe.js:447`) and the link validator strips fragments because of it, so a
  deep link into a substitution entry currently lands at the top of the page.
  Build-time ids also let the validator start checking fragments

Nothing else is left open. The four decisions previously outstanding are
resolved above: checked means measured, substitutes are general per-ingredient
with use caveats carried from the reference pages, in-progress edits are read
from open PRs, and both-ways selection ships in its simplest mutual form.

## Implementation decisions

**First build is a walking skeleton.** One thin slice through the whole thing:
the rebuilt touch model, retire-on-complete, the dossier, one editable field,
one photo upload, and one pull request. The pipeline is proven end to end before
any part of it is deepened. The two build prerequisites are cut to the minimum
the slice needs rather than done in full, so the migration covers only the
recipes the slice exercises.

**Steps reference ingredients with a keyed djot span:**

```
1. Beat the [brown sugar]{ing="brown-sugar"} until pale
```

This is native djot inline-span syntax, so no parser change is needed. The key
is explicit, which means it survives rewording the visible prose and it can be
validated at build time the way images and internal links already are. A bare
`[brown sugar]` was rejected because it collides with djot reference links.

**Editing requires a connection.** With no network, editing is unavailable and
says so. Nothing is ever half-saved and no edit state accumulates on the device.
Recorded consequence, chosen with the tradeoff stated: a note thought of in a
bad-wifi kitchen is lost, which is the situation that motivated inline editing
in the first place. Revisit if it bites.

**Pull requests stay open for review.** Every edit lands on its per-recipe
branch and waits to be merged from a desk after reading the diff. Nothing
auto-merges, including notes and ratings.
