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

### Change (Old)

- update chocolatines
- move robotos to template
- update web manifest and close #5
- move icons to deployment doc directory
- try to fix CNAME, manifest, & robots for #5
- updated recipes from beach trip
- try image alignment @WIP
- implement None option for image_name
- convert rest of png images to jpg #11
- mark all md files for manual review (#11)
- bump ratings by 3 stars for 4-8 (from 1-5)
- prevent dash_dev from writing to MKDocs dir
- compress images for #6
- update README instructions
- remove temporary hack for image_name
- “stylesheets” folder name for sorting
- make rating a special section in prep for #9
- remove unused (for #7)
- update README
- remove other unused files (#5)
- update TODO items
- migrate the rest of the recipes
- track icons
- remove unused files
- mark all WIP files
- update toml
- minor recipe updates
- add potatoes and updated popcorn recipes
- add margarita and shaker recipes
- minor recipe updates
- update README
- add dash_dev for flake8 dependencies
- minor tweaks to recipes
- add slight variation of vanilla ice cream
- rename veggie wraps & move to veggie section
- update chili recipe
- simplify red curry recipe
- puch new pasta e ceci photo
- rename ceci to chickpeas and add orange noolde photo
- set all uncooked meals to rating of 0 for filtering
- week 3 and 4 of veggie WAPO
- fix veggie folder naming
- add first two weeks of veggie WAPO
- removed duplicate recipe and added Porcelain pot care
- Back in business!
- added choc-oat-cookies and pineapple cake
- fix tacos/scampi/Choc-Nuttella

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

### Fix (Old)

- make rating sortable (#9)
- edit URI
- relative links from ROC (#9)
- check all images with duplicates
- full image filename matching
- indent on sublists
- handle sublists (dict) from JSON
- banana bread, rice, and pasta
- section headers & Add: new recipes
- remove images missed in first-pass
- regenerate placeholder SVG images
- rename scampi recipe
- typo in recipe names
- outdated image
- searching ingredients by using deep copy
- lazy load & Add: new family recipes and guac
- mobile zoom on input selection
- minified database.js
- bug in Fuse searching
- rotation of image
- error when highlighting text
- scroll to link & Refac: eslint
- missing ‘end’ statements on lists

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

### New (Old)

- use sortable literal table for TOC (#9)
- initialize TOC page
- initialize tests
- intialize python package
- check that the image file exists and update
- add recipe template
- implement script to update generated sections
- initialize script to update markdown sections
- delete JSON files (fixes #7)
- doit serve task
- migrate photos for each recipe
- add git-revision-date
- migrated up to 5 recipes form each section
- start mkdocs migration from JSON
- add dash_dev and lint config
- add WaPo summer cocktail recipes
- shakshuka & oven_baked_fish_with_tomatoes
- popcorn, chicken, and bake ware notes @WIP
- coconut cake and minor updates
- build!
- beer and updated wine, etc.
- init poetry project
- initialize five new recieps
- recipes photos and kale soup
- peanut sauce!
- add two NYT pasta recipes and eggs
- Crisp, Breaded Chicken, and Chicken Thighs
- chocolate/vanilla ice cream and solved the p-crisp mystery
- add bundt cake and glaze
- H-BPLTs and fixed Banana Bread
- Microwaveable Cacio Pepe and more

### Refactor

- minor update
- update pizza
- upgrade type annotations for 3.9
- move docs to z_dev
- fix and improve dodo
- comment-out duplicate task
- update Cravings book links
- update to calcipy from dash_dev
