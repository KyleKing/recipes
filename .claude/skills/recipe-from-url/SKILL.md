---
name: recipe-from-url
description: Create a recipe file from a URL by fetching content, formatting it according to the project template, and saving it to the appropriate category directory. Use when asked to add, create, or save a recipe from a URL.
allowed-tools: WebFetch, Read, Write, Glob, Grep, Bash, AskUserQuestion
---

# Recipe from URL

## Instructions

When creating a recipe from a URL, follow these steps:

### 1. Check for Existing Similar Recipes

Before creating a new recipe:

1. Use Glob/Grep to search for similar recipe names in relevant categories
2. If duplicate found, ask user to update existing, create variant, or skip
3. Only proceed if confirmed or clearly distinct

### 2. Fetch and Parse Recipe Content

Use WebFetch to retrieve recipe title, ingredients (exact measurements), steps, and notes from the URL.

### 3. Determine Category

Analyze the recipe type and select the appropriate category directory:

- **main**: Main dishes, proteins, curries, stews, casseroles, general entrees
- **dessert**: Desserts, cakes, cookies, treats, sweet items
- **pasta**: Pasta dishes
- **soup**: Soups, broths, stews (liquid-based)
- **drinks**: Cocktails, mocktails, beverages
- **breakfast**: Breakfast items, eggs, pancakes, waffles
- **poultry**: Chicken and other poultry dishes
- **sushi**: Sushi rolls and nigiri
- **seafood**: Fish, shrimp, and other seafood
- **bread**: Breads, focaccia, pretzels, baked goods
- **sides**: Side dishes
- **reference**: Guides, technique references, sauces, spice blends, how-tos

If unsure between categories, use AskUserQuestion to confirm.

### 4. Generate Filename

Convert title to snake_case (lowercase, no special chars): "Chocolate Chip Cookies" → `chocolate_chip_cookies.dj`

### 5. Format Recipe Content

Use this template structure:

```
# [Recipe Title]

Based on [URL](URL)

{ rating=0 image="None" }
:::
:::

## Ingredients

- [ ] [first ingredient used - in preparation order]
- [ ] [second ingredient used]
- [ ] [third ingredient used]

(or with grouping for distinct components:)

### [Component 1]

- [ ] [ingredient]
- [ ] [ingredient]

### [Component 2]

- [ ] [ingredient]
- [ ] [ingredient]

## Recipe

1. [Step 1]
1. [Step 2]

## Notes

- [Optional notes, tips, variations]
```

**Key Formatting Rules:**

- **Title**: Original title in Title Case
- **URL**: Truncate if very long (`https://cooking.nytimes.com/recipes/...`)
- **Metadata**: `rating=0 image="None"`
- **Ingredients**:
    - Checkbox format: `- [ ]`
    - Order in preparation order (as used in steps)
    - **Conversions (apply automatically)**:
        - Fractional characters to plain text: `½` → `1/2`, `¼` → `1/4`, `¾` → `3/4`, `⅓` → `1/3`, `⅔` → `2/3`, `⅛` → `1/8`, `⅜` → `3/8`, `⅝` → `5/8`, `⅞` → `7/8`
        - Mixed numbers: `1 ½` → `1.5`, `2 ¼` → `2.25`, `1 ⅓` → `1.33`, `2 ⅔` → `2.67`
        - "teaspoon(s)" → `tsp`
        - "tablespoon" → `Tbsp`, "tablespoons" → `Tbsps`
    - **Track quantity changes**: Note any changes to measurements/amounts to report after saving
    - Group using `### [Label]` subheaders or nested lists (2-space indent) only for distinct components
- **Recipe Steps**: Numbered lists (`1.`), preserve details, minimal rewording
- **Notes**: Include tips, variations, or important details

### 6. Writing Style

Kyle's style: Direct, concise, minimal changes. Preserve measurements and technical precision. Only adapt formatting, not content.

### 7. Save File and Report Changes

1. Write file to: `content/[category]/[filename].dj`
2. Confirm file creation
3. **Report quantity changes only**: If you modified any measurements/amounts from source (e.g., "1 cup butter" → "2 sticks butter", combined duplicate ingredients with adjusted quantities), list these changes. Standard conversions (fractional characters, unit abbreviations) don't need to be reported.

## Examples

**Simple Recipe:**

1. WebFetch URL → Extract title, ingredients (apply conversions: "½ cup" → "1/2 cup", "2 teaspoons" → "2 tsp"), steps
2. Category: `pasta`, Filename: `simple_pasta.dj`
3. Format and write to `content/pasta/simple_pasta.dj`
4. Report: "Created simple_pasta.dj" (standard conversions applied, no substantive quantity changes)

**Recipe with Quantity Changes:**
If source has "4 ounces butter" but you convert to "1 stick butter", report: "Changed '4 ounces butter' to '1 stick butter'"

## Critical Rules

- Check for duplicates first (Glob/Grep existing recipes)
- Use only source URL information (no hallucination)
- Apply automatic conversions: fractional characters (½ → 1/2, ⅛ → 1/8), mixed numbers (1 ½ → 1.5), "teaspoon(s)" → "tsp", "tablespoon(s)" → "Tbsp/Tbsps"
- Order ingredients in preparation order
- Group only when components are clearly distinct
- Report only substantive quantity/measurement changes (not standard conversions)
- No emojis in recipe files
- snake_case filenames only
