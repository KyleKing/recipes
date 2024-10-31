## Unreleased

### Feat

- one-pot Shrimp Scampi pasta
- add Chicken Pot Pie
- add grinder_salad_sandwich
- add garlic rice and new links
- simplify the pizza recipe
- add the Creamy Orzo Skillet
- experiment with beartype_this_package
- add recipes from Chef's Fridges and Crispy Tofu from WaPo
- begin converting tasks to Invoke
- add blackened seasoning
- migrate to Python 3.11

### Fix

- restore extra.css
- correct links to Garam Masala recipe
- ignore linting warning
- use the new ignore_patterns configuration
- upgrade with copier
- update cz-legacy for breaking changes
- bump minimum pymdown dependency
- set indent to 4
- resolve bugs in recipe formatter
- migrate to mdformat-mkdocs
- add missing instruction to drain
- correct indentation for tonight's dinner!

### Refactor

- rename baked fish
- move poultry/seafood recipes appropriately
- merge sides into meals
- merge veggies into meals
- merge rice into meals
- remove Chicken Shawarma
- apply rating deflation
- remove BUMP_RATING
- rename the burrito recipe
- generalize the burrito recipe
- one pizza recipe!
- move z_dev/ out to docs-code/
- fix links
- another round of recipe cleanup
- resolve next batch of manual review comments
- use a function for the global beartype
- remove redundant 3.11 python constraint
- run copier update
- remove the mufuletta sanwich
- convert fractions to ascii and remove gremlins
- hide the right TOC sidebar
- run prettier
- remove duplicate beartype wrapper
- use patched deploy from calcipy
- remove the difficult Chicken and Dumpling recipe
- remove Obsidian vault reference
- remove cauliflower platter and cleanup checklists
- update copier

## 0.4.0 (2022-10-20)

### Feat

- symlink obsidian vault for editing
- add Gnocchi Bake
- add tomato butter noodles
- Add Spicy Salmon Bowl recipe
- copier update. Add Github Actions
- add markdown autoformatter
- initial hummus recipe
- standardize cookie recipes
- new Whiskey Sour recipe

### Fix

- suppress mdformat errors on admonitions
- admonitions should be four spaces
- admonitions are incorrectly modified

### Refactor

- try to fix type errors
- use spacing consistent with mdformatter
- Python type annotations from beartype
- apply mdformat


- remove old recipes

## 2021.0.3.0 (2022-01-04)

### Feat

- new fish and carbonara recipes!
- minor cleanup and new photos
- beach enchiladas
- add beach rice and doit updates
- add Garlic Bread
- implement formatter for TOC based on calcipy
- replace recipe-formatting with calcipy
- add falafel recipe
- setup CD on AppVeyor
- update calcipy for better dodo
- add recipes using-up leftovers
- show password modal

### Fix

- the earlier PEP585 issues were an error with poetry using 3.8 and not 3.9
- sync pre-commit and delay PEP585
- restore Python 3.9-safe type annotations
- drop suffix from TOC table
- ../ url from TOC is no longer necessary
- rename isort
- correct for changes in calcipy  ad148bc
- apply type fixes from mypy
- formatter logic
- password prompt on mobile
- skip icons from png to jpg conversion
- remove duplicate images

### Refactor

- minor update
- update pizza
- upgrade type annotations for 3.9
- move docs to z_dev
- fix and improve dodo
- comment-out duplicate task
- update Cravings book links
- update to calcipy from dash_dev
