---
name: recipe-from-url
description: Create a recipe file from a URL by fetching content, formatting it according to the project template, and saving it to the appropriate category directory. Use when asked to add, create, or save a recipe from a URL.
allowed-tools: WebFetch, Read, Write, Glob, Grep, Bash, AskUserQuestion
---

# Recipe from URL

## Instructions

When creating a recipe from a URL, follow these steps:

### 1. Fetch and Parse Recipe Content

1. Use WebFetch to retrieve the recipe from the provided URL
2. Extract the following information:
   - Recipe title
   - Ingredients list (preserve exact measurements and quantities)
   - Recipe steps/instructions (preserve exact details)
   - Any additional notes, tips, or variations

### 2. Determine Category

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

### 3. Generate Filename

1. Convert recipe title to snake_case
2. Remove special characters, keep only letters, numbers, underscores
3. Use lowercase throughout
4. Examples:
   - "Chocolate Chip Cookies" → `chocolate_chip_cookies.dj`
   - "Baked Tofu With Peanut Sauce" → `baked_tofu_with_peanut_sauce.dj`

### 4. Format Recipe Content

Use this template structure:

```
# [Recipe Title]

Based on [URL](URL)

{ rating=0 image="None.jpeg" }
:::
:::

## Ingredients

- [ ] [ingredient with measurement]
- [ ] [ingredient with measurement]

## Recipe

1. [Step 1]
1. [Step 2]

## Notes

- [Optional notes, tips, variations]
```

**Formatting Guidelines:**

- **Title**: Use the original recipe title, Title Case
- **URL**: If URL is very long, truncate middle or end with "..." (e.g., `https://cooking.nytimes.com/recipes/...`)
- **Metadata**: Always start with `rating=0` and `image="None.jpeg"` for new recipes
- **Ingredients**:
  - Use checkbox format: `- [ ]`
  - Preserve exact measurements and quantities from source
  - Can group with `### [Label]` subsections if recipe has distinct preparation steps
  - Use nested lists for grouped ingredients
  - Keep original ingredient names and details
- **Recipe Steps**:
  - Use numbered lists: `1.`
  - Preserve step details and order from source
  - Use nested lists (indented) for sub-steps
  - Minimal rewording—keep original instructions intact
- **Notes**:
  - Include tips, variations, or important details from source
  - Can reference related recipes using markdown links
  - Use numbered or bulleted lists as appropriate

### 5. Writing Style

Follow Kyle's style:
- Direct and concise
- Minimal changes to source material
- Do not hallucinate or modify measurements, ingredients, or steps
- Do not add emojis or unnecessary commentary
- Preserve technical precision from original recipe
- Only adapt formatting to match template, not content

### 6. Save File

1. Write file to: `content/[category]/[filename].dj`
2. Confirm file creation with user
3. Mention that they can:
   - Add an image later (same filename with .jpeg/.jpg/.png extension)
   - Update the rating after trying the recipe
   - Edit any details as needed

## Examples

### Example 1: Simple Recipe

**User:** "Add a recipe from https://example.com/simple-pasta"

**Actions:**
1. WebFetch the URL to extract recipe details
2. Determine category: `pasta`
3. Generate filename: `simple_pasta.dj`
4. Format according to template
5. Write to `content/pasta/simple_pasta.dj`

### Example 2: Complex Recipe with Grouped Ingredients

**User:** "Create a recipe from https://cooking.nytimes.com/recipes/1020530-baked-tofu"

**Actions:**
1. WebFetch the URL
2. Determine category: `main`
3. Generate filename: `baked_tofu_with_peanut_sauce_and_coconut_lime_rice.dj`
4. Format with all ingredients in single list (or grouped if source has clear sections)
5. Write to `content/main/baked_tofu_with_peanut_sauce_and_coconut_lime_rice.dj`

## Important Reminders

- **Do not hallucinate**: Only use information from the source URL
- **Preserve measurements**: Keep exact quantities and units
- **Minimal adaptation**: Only change formatting to match template, not content
- **No emojis**: Never add emojis to recipe files
- **Check category**: If unsure, ask user to confirm category
- **Verify filename**: Ensure snake_case and no special characters
