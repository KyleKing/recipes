---
name: recipe-from-url
description: Create a recipe file from a URL by fetching content, formatting it according to the project template, and saving it to the appropriate category directory. Use when asked to add, create, or save a recipe from a URL.
allowed-tools: WebFetch, Read, Write, Glob, Grep, Bash, AskUserQuestion
---

# Recipe from URL

## Instructions

When creating a recipe from a URL, follow these steps:

### 1. Check for Existing Similar Recipes

Before creating a new recipe, verify that a similar recipe doesn't already exist:

1. **Extract recipe name**: Determine the likely recipe name from the URL or use WebFetch to get the title
2. **Search for similar recipes**:
   - Use Glob to list existing recipe files in relevant category directories
   - Use Grep to search for similar recipe names/titles across all recipe files
   - Check for recipes with similar ingredients or titles
3. **Handle duplicates**:
   - If a similar recipe exists, ask the user whether to:
     - Update/enhance the existing recipe
     - Create a new variant (e.g., "instant_pot_beef_stew" vs "slow_cooker_beef_stew")
     - Skip creation entirely
   - Only proceed with creating a new recipe if confirmed by user or clearly distinct

### 2. Fetch and Parse Recipe Content

1. Use WebFetch to retrieve the recipe from the provided URL
2. Extract the following information:
   - Recipe title
   - Ingredients list (preserve exact measurements and quantities)
   - Recipe steps/instructions (preserve exact details)
   - Any additional notes, tips, or variations

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

1. Convert recipe title to snake_case
2. Remove special characters, keep only letters, numbers, underscores
3. Use lowercase throughout
4. Examples:
   - "Chocolate Chip Cookies" → `chocolate_chip_cookies.dj`
   - "Baked Tofu With Peanut Sauce" → `baked_tofu_with_peanut_sauce.dj`

### 5. Format Recipe Content

Use this template structure:

```
# [Recipe Title]

Based on [URL](URL)

{ rating=0 image="None.jpeg" }
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

**Formatting Guidelines:**

- **Title**: Use the original recipe title, Title Case
- **URL**: If URL is very long, truncate middle or end with "..." (e.g., `https://cooking.nytimes.com/recipes/...`)
- **Metadata**: Always start with `rating=0` and `image="None.jpeg"` for new recipes
- **Ingredients**:
  - Use checkbox format: `- [ ]`
  - **Order ingredients in preparation order** (order they are used in recipe steps)
  - Preserve exact measurements and quantities from source
  - Keep original ingredient names and details
  - **Group when appropriate** if recipe has distinct components:
    - Use `### [Label]` subheaders for clear sections (e.g., `### Chicken`, `### White sauce`, `### For serving`)
    - OR use nested lists with one level of indentation (indent with 2 spaces) with descriptive parent item:
      ```
      - In a small bowl, whisk together
        - [ ] ingredient 1
        - [ ] ingredient 2
      ```
  - Use grouping sparingly - only when components are clearly distinct
  - Avoid deep nesting beyond one level
- **Recipe Steps**:
  - Use numbered lists: `1.`
  - Preserve step details and order from source
  - Use nested lists (indented) for sub-steps
  - Minimal rewording—keep original instructions intact
- **Notes**:
  - Include tips, variations, or important details from source
  - Can reference related recipes using markdown links
  - Use numbered or bulleted lists as appropriate

### 6. Writing Style

Follow Kyle's style:
- Direct and concise
- Minimal changes to source material
- Do not hallucinate or modify measurements, ingredients, or steps
- Do not add emojis or unnecessary commentary
- Preserve technical precision from original recipe
- Only adapt formatting to match template, not content

### 7. Save File

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
4. **Order ingredients in preparation order** and group if recipe has distinct components:
   - If source clearly separates components (e.g., marinade, sauce, rice), use `###` subheaders
   - If ingredients are used together in a step, consider nested list grouping
   - If recipe is linear without distinct sections, use single ordered list
5. Write to `content/main/baked_tofu_with_peanut_sauce_and_coconut_lime_rice.dj`

## Important Reminders

- **Check for duplicates first**: Always search for existing similar recipes before creating a new one
- **Do not hallucinate**: Only use information from the source URL
- **Preserve measurements**: Keep exact quantities and units
- **Order ingredients in preparation order**: List ingredients in the order they are used in recipe steps
- **Group appropriately**: Use subheaders or nested lists only when recipe has clearly distinct components
- **Minimal adaptation**: Only change formatting to match template, not content
- **No emojis**: Never add emojis to recipe files
- **Check category**: If unsure, ask user to confirm category
- **Verify filename**: Ensure snake_case and no special characters
