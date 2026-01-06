# TRMNL E-ink Display Setup Guide

This guide explains how to display recipes from this site on your TRMNL e-ink display (800x480 pixels, landscape orientation).

## Overview

The recipe site generates JSON versions of all recipes optimized for TRMNL e-ink displays:
- Structured JSON format with title, ingredients, and steps
- Easy to format using Liquid templates in TRMNL
- No images or navigation to maximize recipe content
- Perfect for grayscale e-ink rendering

## Quick Start

### Step 1: Choose Your Recipe

1. Navigate to your deployed recipe site (e.g., `https://recipes.kyleking.me`)
2. Find the recipe you want to display on TRMNL
3. Copy the full URL and change `.html` to `.json`

**Example:**
- HTML version: `https://recipes.kyleking.me/seafood/shrimp_scampi.html`
- JSON version: `https://recipes.kyleking.me/seafood/shrimp_scampi.json`

### Step 2: Create TRMNL Private Plugin

1. Log into your TRMNL account at [usetrmnl.com](https://usetrmnl.com)
2. Navigate to: **Plugins → Private Plugin → New**
3. Configure the plugin:
   - **Name:** "Active Recipe" (or your preferred name)
   - **Strategy:** Polling
   - **Polling URL:** Your recipe `.json` URL
   - **Polling Verb:** GET

**Example configuration:**
- Polling URL: `https://recipes.kyleking.me/seafood/shrimp_scampi.json`

### Step 3: Configure the Markup

In the **Markup** section, use this Liquid template to format the JSON data:

```html
<!DOCTYPE html>
<html>
<head>
    <link rel="stylesheet" href="https://usetrmnl.com/css/latest/plugins.css">
    <style>
        body { font-family: sans-serif; font-size: 14px; padding: 20px; }
        h1 { font-size: 24px; margin-bottom: 15px; border-bottom: 2px solid black; }
        h2 { font-size: 18px; margin-top: 20px; margin-bottom: 10px; }
        ul, ol { padding-left: 20px; }
        li { margin-bottom: 5px; }
    </style>
</head>
<body>
    <h1>{{ IDX_0.title }}</h1>

    <h2>Ingredients</h2>
    <ul>
    {% for ingredient in IDX_0.ingredients %}
        <li>{{ ingredient }}</li>
    {% endfor %}
    </ul>

    <h2>Steps</h2>
    <ol>
    {% for step in IDX_0.steps %}
        <li>{{ step }}</li>
    {% endfor %}
    </ol>
</body>
</html>
```

This template uses Liquid to parse the JSON and format it with proper headings, bullet points, and numbered lists.

### Step 4: Test and Save

1. Use the **Preview** button to test how your recipe looks
2. Click **Save** to create the plugin
3. Add the plugin to your TRMNL device playlist

## Changing the Displayed Recipe

To display a different recipe:

1. Go to **Plugins → Private Plugin → Your Plugin Name**
2. Update the **Polling URL** with the new recipe `.json` URL
3. Click **Save**
4. Manually trigger a refresh on your TRMNL device, or wait for the next polling interval

**Example:** Change from `shrimp_scampi.json` to `chicken_tacos.json`

## How It Works

During the build process, the site generates both HTML and JSON versions of each recipe:

- **HTML version** (`*.html`): Full web page with navigation, images, and styling
- **JSON version** (`*.json`): Structured data with:
  - `title`: Recipe name
  - `ingredients`: Array of ingredient strings (flattened, nested items prefixed with `> ` to indicate indentation level)
  - `steps`: Array of recipe step strings

The JSON format is automatically generated from the Djot markup source files.

**Ingredient Nesting:** Nested ingredients are indicated by prefix characters:
- Top-level: `"Flour"`
- Nested once: `"> Nested ingredient"`
- Nested twice: `"> > Deeply nested ingredient"`

## Testing Locally

Before deploying, you can test the JSON output:

1. Build the site: `mise run build`
2. Serve locally: `mise run serve` (or `go run goServe/main.go -directory public`)
3. View JSON in browser: `http://localhost:8000/seafood/shrimp_scampi.json`
4. Or view raw file: `cat public/seafood/shrimp_scampi.json`

## Troubleshooting

### Recipe doesn't fit on screen
- Choose recipes with fewer ingredients or simpler steps
- Some complex recipes may require scrolling on the TRMNL display
- Adjust the font size in the markup CSS (`font-size: 14px` → smaller value)

### Formatting looks wrong
- Verify you're using the `.json` URL, not `.html`
- Check that the Liquid template is correctly parsing the JSON structure
- Ensure the JSON file was generated during build (`mise run build`)
- Test the JSON structure by viewing it directly in your browser

### Content not updating
- Check the polling interval in your TRMNL plugin settings
- Verify the polling URL is correct and accessible (test in browser)
- Manually trigger a refresh from your TRMNL device

### JSON file not generated
- Run `mise run build` to regenerate all files
- Check for build errors in the console output
- Verify the `.dj` source file exists in `content/` directory

## Advanced: Webhook Strategy

For more dynamic recipe selection, you could implement a webhook-based approach:

1. Create a simple web service that accepts recipe selection
2. Configure your TRMNL plugin with **Strategy: Webhook**
3. POST updates to your webhook URL when you want to change recipes

Example webhook payload:
```json
{
  "merge_variables": {
    "recipe_html": "<html>...</html>"
  }
}
```

## Display Specifications

- **Resolution:** 800 × 480 pixels
- **Orientation:** Landscape
- **Colors:** Black and white, 2-bit grayscale
- **Refresh Rate:** Configurable (typically 6-12 hours for static content)

## Customization

### JSON Format

To customize the JSON output format, edit the `renderDjotToJson()` function in `goBuild/build.go`:

- Add/remove fields (currently: title, ingredients, steps)
- Modify how ingredients are extracted (currently flattened with nested items)
- Change how steps are extracted
- Add metadata like rating, source URL, or notes

After making changes, rebuild with `mise run build` and redeploy.

### TRMNL Markup Styling

Customize the visual appearance in your TRMNL plugin's Markup section:

- Adjust `font-size` for readability (default: 14px body, 24px h1, 18px h2)
- Change `font-family` (sans-serif default, or use monospace)
- Modify spacing with `padding` and `margin` properties
- Customize list styling with `padding-left` and `margin-bottom`
- Add borders or other visual elements to headings

## Resources

- [TRMNL Official Docs](https://docs.usetrmnl.com)
- [TRMNL Private Plugins](https://help.usetrmnl.com/en/articles/9510536-private-plugins)
- [Recipe Site Repository](https://github.com/KyleKing/recipes)
