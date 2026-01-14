# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Personal recipe collection site built with Go and templ, generating static HTML from Djot markup files. Hosted at https://recipes.kyleking.me.

## Development Commands

All commands use `mise` task runner. Common tasks:

```bash
mise run build      # Build website (format → go run . → minify → pagefind index)
mise run format     # Format code (templ generate → templ fmt → go fmt)
mise run lint       # Run testifylint (depends on format)
mise run test       # Run tests with coverage (depends on format, lint)
mise run coverage   # View test coverage from most recent test run
mise run serve      # Serve built site on port 8000
```

Additional utilities:

```bash
mise run compress <path>   # Compress images (optimize-images -mh 900)
mise run update           # Update dependencies (mise, go modules)
./check_links.py          # Check/fix recipe links, add Wayback archive links
./check_links.py --dry-run --file content/main/recipe.dj  # Preview changes for single file
```

### Environment Setup

After running `./setup-spacy.sh` to build the C++ wrapper, source the generated `.env` file:

```bash
source .env  # Required for local development - sets CGO_LDFLAGS and library paths
```

This file is auto-generated and contains platform-specific flags needed to link against the spaCy C++ wrapper.

### Testing

```bash
go test -coverprofile=coverage.out -coverpkg=./... ./...  # Run all tests
go test ./goBuild -run TestSpecificTest                    # Run single test
```

## Architecture

### Build Pipeline

1. **Copy content/** → **public/** (includes `.dj` files, images, `_static/`, `styles.css`)
2. **Generate Go code**: `templ generate` creates `templates_templ.go` from `templates.templ`
3. **Build**: `go run .` executes build pipeline:
   - Parse `.dj` files (Djot markup) to AST
   - Convert AST to HTML with custom node converters
   - Wrap HTML in templ components
   - Generate category index pages (`/main/index.html`, etc.)
   - Generate home page (`/index.html`)
   - Skip files prefixed with `_` (templates)
4. **Minify**: HTML/CSS/JS minification
5. **Index**: Pagefind creates search index

### Key Components

**goBuild/build.go** - Core build orchestration:
- `Build(publicDir)`: Entry point, writes static pages, walks directory tree
- `replaceDjWithHtml()`: Converts `.dj` → `.html`, populates `RecipeMap`
- `renderDjot()`: Parses Djot with custom node converters
- `formattedDivPartial()`: Extracts metadata (`rating=X image="file.jpg"`)
- `listItemConversion()`: Renders checkboxes for task lists
- `writeIndexes()`: Generates all index pages from `RecipeMap`

**goBuild/schemas.go** - Data structures:
- `Recipe`: `{dirUrl, imagePath, name, url}`
- `Subdir`: `{url, name}` for category directories
- `RecipeMap`: `map[string]Recipe` keyed by file path

**goBuild/templates.templ** - HTML generation (templ syntax):
- `page()`: Base layout with nav, conditionally loads Pagefind
- `recipePage()`: Individual recipe wrapper
- `dirIndexPage()`: Category index with image grid
- `homePage()`: Site home with category links

**goBuild/helpers.go**:
- `toTitleCase()`: `"chocolate_chip_cookies"` → `"Chocolate Chip Cookies"`
- `withHtmlExt()`: Replace extension with `.html`

### Recipe File Format (.dj)

Djot markup with custom metadata:

```
# Recipe Title

Based on [URL](URL)

{ rating=0 image="None" }
:::
:::

## Ingredients

- [ ] Ingredient with measurement (ordered in preparation order)
- [ ] Next ingredient

### Optional Grouping (if recipe has distinct components)

- [ ] Grouped ingredient 1
- [ ] Grouped ingredient 2

## Recipe

1. Step instructions

## Notes

- Optional tips
```

**Metadata extraction** (goBuild/build.go:42-83):
- `rating`: Integer 0-5 (0 = "Not yet rated", 1-5 = "X / 5")
- `image`: Filename (with extension) or `"None"` for placeholder

**Ingredient ordering**:
- List ingredients in preparation order (order they are used in recipe steps)
- Group related ingredients when recipe has distinct components using either:
  - Subheaders: `### Component Name` (e.g., `### Chicken`, `### White sauce`)
  - Nested lists: One level of indentation with descriptive parent item (e.g., `- In a small bowl, whisk together`)
- Use grouping sparingly - only when components are clearly distinct

**Categories**: Subdirectories in `content/`:
- `main/`, `dessert/`, `pasta/`, `soup/`, `drinks/`, `breakfast/`, `poultry/`, `sushi/`, `seafood/`, `bread/`, `sides/`, `reference/`

### Common Patterns

**Adding a new recipe**:
1. **Check for duplicates**: Search for existing similar recipes first
   - Use Glob to list files in relevant category directories
   - Use Grep to search for similar recipe names/titles in existing files
   - If a similar recipe exists, either update the existing one or confirm with user that a new variant is warranted
2. Create `content/<category>/<recipe_name>.dj` following template
3. Use `snake_case` for filenames
4. Optionally add matching image (same basename, `.jpeg`/`.jpg`/`.png`)
5. Run `mise run build` to generate HTML

**Modifying build logic**:
1. Edit `.templ` files for HTML structure changes
2. Edit `build.go` for Djot processing or metadata handling
3. Run `mise run format` (regenerates `templates_templ.go`)
4. Run `mise run test` to verify

**Custom Djot node conversion**:
- Registered in `renderDjot()` via `map[djot_parser.DjotNode]djot_parser.Conversion`
- Example: `DivNode` → `formattedDivPartial()` extracts metadata
- Example: `ListItemNode` → `listItemConversion()` renders checkboxes

## TODOs from README

- Validate no duplicate headers (commit 23822717)
- Better error messages on test failures for test file commits (commit 2c206a8c)

## Recipe Link Maintenance

Use `check_links.py` (Python script with uv inline dependencies) to:
- Verify recipe source URLs are still available
- Add Wayback Machine archive links for working URLs
- Replace dead links with archive versions
- Flag unavailable links

Run before committing recipe changes to ensure link integrity.
