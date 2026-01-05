# recipes

Kyle and Alex's Personal Recipes. Hosted at https://recipes.kyleking.me

## Features

- **Search:** Full-text search across all recipes
- **TRMNL E-ink Display:** Optimized display mode for TRMNL e-ink devices (800x480 landscape)
  - Add `?trmnl=1` to any recipe URL for e-ink optimized view
  - See [TRMNL Setup Guide](_TRMNL_SETUP.md) for detailed instructions

## Usage

### Viewing on TRMNL E-ink Display

To display a recipe on your TRMNL e-ink device:

1. Add `?trmnl=1` to any recipe URL (e.g., `https://recipes.kyleking.me/seafood/shrimp_scampi.html?trmnl=1`)
2. Create a TRMNL Private Plugin with the Polling strategy
3. Use your recipe URL (with `?trmnl=1`) as the polling URL
