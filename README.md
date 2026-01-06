# recipes

Kyle and Alex's Personal Recipes. Hosted at https://recipes.kyleking.me

## Features

- **Search:** Full-text search across all recipes
- **TRMNL E-ink Display:** JSON recipe format for TRMNL e-ink devices (800x480 landscape)
  - Change `.html` to `.json` in any recipe URL for JSON version
  - See [TRMNL Setup Guide](_TRMNL_SETUP.md) for detailed instructions

## Usage

### Viewing on TRMNL E-ink Display

To display a recipe on your TRMNL e-ink device:

1. Change `.html` to `.json` in any recipe URL (e.g., `https://recipes.kyleking.me/seafood/shrimp_scampi.json`)
2. Create a TRMNL Private Plugin with the Polling strategy
3. Use the JSON URL as the polling URL and format it with Liquid templates
