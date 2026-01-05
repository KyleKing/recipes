# TRMNL E-ink Display Setup Guide

This guide explains how to display recipes from this site on your TRMNL e-ink display (800x480 pixels, landscape orientation).

## Overview

The recipe site has been optimized for TRMNL e-ink displays with:
- Compact typography and spacing for the 800x480 resolution
- Hidden navigation and images to maximize recipe content
- Black and white color scheme optimized for grayscale e-ink
- Query parameter activation (`?trmnl=1`) for easy switching

## Quick Start

### Step 1: Choose Your Recipe

1. Navigate to your deployed recipe site (e.g., `https://recipes.kyleking.me`)
2. Find the recipe you want to display on TRMNL
3. Copy the full URL of the recipe page

**Example:** `https://recipes.kyleking.me/seafood/shrimp_scampi.html`

### Step 2: Add TRMNL Query Parameter

Add `?trmnl=1` to the end of your recipe URL.

**Example:** `https://recipes.kyleking.me/seafood/shrimp_scampi.html?trmnl=1`

### Step 3: Create TRMNL Private Plugin

1. Log into your TRMNL account at [usetrmnl.com](https://usetrmnl.com)
2. Navigate to: **Plugins → Private Plugin → New**
3. Configure the plugin:
   - **Name:** "Active Recipe" (or your preferred name)
   - **Strategy:** Polling
   - **Polling URL:** Your recipe URL with `?trmnl=1` parameter
   - **Polling Verb:** GET

### Step 4: Configure the Markup

In the **Markup** section, you can use one of two approaches:

#### Option A: Direct Display (Recommended)
Leave the markup empty or use:
```html
{{ IDX_0 }}
```

This will display the fetched HTML directly with the e-ink optimizations.

#### Option B: TRMNL Framework
For more control, use TRMNL's official CSS framework:
```html
<!DOCTYPE html>
<html>
<head>
    <link rel="stylesheet" href="https://usetrmnl.com/css/latest/plugins.css">
</head>
<body>
    <div class="full">
        {{ IDX_0 }}
    </div>
</body>
</html>
```

### Step 5: Test and Save

1. Use the **Preview** button to test how your recipe looks
2. Click **Save** to create the plugin
3. Add the plugin to your TRMNL device playlist

## Changing the Displayed Recipe

To display a different recipe:

1. Go to **Plugins → Private Plugin → Your Plugin Name**
2. Update the **Polling URL** with the new recipe URL (don't forget `?trmnl=1`)
3. Click **Save**
4. Manually trigger a refresh on your TRMNL device, or wait for the next polling interval

## How It Works

The `?trmnl=1` query parameter triggers special CSS optimizations:

- **Typography:** Smaller font sizes (14px base, compact headings)
- **Spacing:** Reduced margins and padding to fit more content
- **Hidden Elements:** Navigation, images, and non-essential UI removed
- **Checkboxes:** Ingredient checkboxes converted to bullet points
- **Colors:** Pure black and white for optimal e-ink rendering
- **Links:** Simplified to black with underlines

## Testing Locally

Before deploying, you can test the e-ink display mode:

1. Build the site: `./build.sh`
2. Serve locally: `go run goServe/main.go -directory public`
3. Open a recipe with `?trmnl=1` in your browser: `http://localhost:8000/seafood/shrimp_scampi.html?trmnl=1`
4. Resize your browser window to 800x480 to simulate the TRMNL display

## Troubleshooting

### Recipe doesn't fit on screen
- Choose recipes with fewer ingredients or simpler steps
- Some complex recipes may require scrolling on the TRMNL display

### Images still showing
- Verify the `?trmnl=1` parameter is in the URL
- Check that JavaScript is enabled (required to detect the parameter)

### Formatting looks wrong
- Ensure you've rebuilt the site after making template/CSS changes
- Clear your browser cache
- Verify the generated HTML includes the TRMNL detection script

### Content not updating
- Check the polling interval in your TRMNL plugin settings
- Verify the polling URL is correct and accessible
- Manually trigger a refresh from your TRMNL device

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

## CSS Customization

The e-ink optimizations are in `content/styles.css` under the `body.trmnl-mode` selector. You can customize:

- Font sizes
- Spacing and margins
- Which elements to hide/show
- Link styling

After making changes, rebuild the site with `./build.sh` and redeploy.

## Resources

- [TRMNL Official Docs](https://docs.usetrmnl.com)
- [TRMNL Private Plugins](https://help.usetrmnl.com/en/articles/9510536-private-plugins)
- [Recipe Site Repository](https://github.com/KyleKing/recipes)
