package goBuild

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"slices"
	"sort"
	"strconv"
	"strings"

	"github.com/a-h/templ"
	"github.com/sivukhin/godjot/djot_parser"
	"github.com/sivukhin/godjot/djot_tokenizer"
	"github.com/sivukhin/godjot/html_writer"
)

const IMAGE_PLACEHOLDER = "/_static/placeholder.png"

// Convert Djot AST to JSON for TRMNL display
func renderDjotToJson(ast []djot_parser.TreeNode[djot_parser.DjotNode]) string {
	title := ""
	ingredients := []string{}
	steps := []string{}
	currentSection := ""

	var extractListItemText func(djot_parser.TreeNode[djot_parser.DjotNode]) string
	extractListItemText = func(node djot_parser.TreeNode[djot_parser.DjotNode]) string {
		var textParts []string
		for _, child := range node.Children {
			// Only extract text from paragraph and inline nodes, skip nested lists
			if child.Type != djot_parser.UnorderedListNode && child.Type != djot_parser.TaskListNode && child.Type != djot_parser.OrderedListNode {
				text := strings.TrimSpace(string(child.FullText()))
				if text != "" {
					textParts = append(textParts, text)
				}
			}
		}
		return strings.Join(textParts, " ")
	}

	var extractListItems func(djot_parser.TreeNode[djot_parser.DjotNode], int) []string
	extractListItems = func(node djot_parser.TreeNode[djot_parser.DjotNode], level int) []string {
		var items []string
		prefix := strings.Repeat("> ", level)
		for _, child := range node.Children {
			if child.Type == djot_parser.ListItemNode {
				text := extractListItemText(child)
				if text != "" {
					items = append(items, prefix+text)
				}
				// Recursively extract nested list items with increased level
				for _, nestedChild := range child.Children {
					if nestedChild.Type == djot_parser.UnorderedListNode || nestedChild.Type == djot_parser.TaskListNode || nestedChild.Type == djot_parser.OrderedListNode {
						items = append(items, extractListItems(nestedChild, level+1)...)
					}
				}
			}
		}
		return items
	}

	var traverse func(djot_parser.TreeNode[djot_parser.DjotNode])
	traverse = func(node djot_parser.TreeNode[djot_parser.DjotNode]) {
		if node.Type == djot_parser.HeadingNode {
			levelStr := node.Attributes.Get(djot_parser.HeadingLevelKey)
			text := strings.TrimSpace(string(node.FullText()))

			if (levelStr == "1" || levelStr == "#") && title == "" {
				title = text
			} else if levelStr == "2" || levelStr == "##" {
				currentSection = text
			}
		}

		for _, child := range node.Children {
			traverse(child)
		}

		if node.Type == djot_parser.UnorderedListNode || node.Type == djot_parser.TaskListNode {
			if strings.EqualFold(currentSection, "Ingredients") {
				ingredients = extractListItems(node, 0)
			}
		} else if node.Type == djot_parser.OrderedListNode {
			if strings.EqualFold(currentSection, "Recipe") {
				steps = extractListItems(node, 0)
			}
		}
	}

	for _, node := range ast {
		traverse(node)
	}

	result := map[string]interface{}{
		"title":       title,
		"ingredients": ingredients,
		"steps":       steps,
	}

	jsonBytes, err := json.Marshal(result)
	if err != nil {
		log.Printf("Error marshaling JSON: %v", err)
		return "{}"
	}

	return string(jsonBytes)
}

// Convert 'li' nodes to either tasks or unstyled
// Note: adapted without 'disable' and without \n from: https://github.com/sivukhin/godjot/pull/12
func listItemConversion(s djot_parser.ConversionState, n func(c djot_parser.Children)) {
	class := s.Node.Attributes.Get(djot_tokenizer.DjotAttributeClassKey)
	if class == djot_parser.CheckedTaskItemClass || class == djot_parser.UncheckedTaskItemClass {
		s.Writer.InTag("li")(func() {
			s.Writer.WriteString("<input type=\"checkbox\"")
			if class == djot_parser.CheckedTaskItemClass {
				s.Writer.WriteString(" checked=\"\"")
			}
			s.Writer.WriteString("/>")
			n(s.Node.Children)
		})
	} else {
		s.BlockNodeConverter("li", n)
	}
}

// Curry conditionally converting `<div>` based on attached attributes
func formattedDivPartial(publicDir string, path string, rMap RecipeMap) func(djot_parser.ConversionState, func(djot_parser.Children)) {
	return func(s djot_parser.ConversionState, n func(c djot_parser.Children)) {
		dirUrl, err := filepath.Rel(publicDir, filepath.Dir(path))
		ExitOnError(err)

		ratingInt := -1
		rating := s.Node.Attributes.Get("rating")
		if rating != "" {
			ratingInt, err = strconv.Atoi(rating)
			ExitOnError(err)

			displayedRating := "..."
			if 1 <= ratingInt && ratingInt <= 5 {
				displayedRating = fmt.Sprintf("%d / 5", ratingInt)
			} else if ratingInt == 0 {
				displayedRating = "Not yet rated"
			} else {
				log.Println(fmt.Sprintf("Rating is not within [0,5] (%d)", ratingInt))
				os.Exit(1)
			}
			s.Writer.WriteString("<p>Personal rating: " + displayedRating + "</p>")
		}

		imagePath := ""
		imageName := s.Node.Attributes.Get("image")
		if imageName != "" {
			if strings.Contains(imageName, ".") {
				imagePath = "/" + filepath.Join(dirUrl, imageName)
				s.Writer.WriteString("<img class=\"fullsize\" alt=\"" + imageName + "\" src=\"" + imagePath + "\">")
			} else {
				imagePath = IMAGE_PLACEHOLDER
				s.Writer.WriteString("<p><i>No image yet</i></p>")
			}
		}

		if len(imagePath) > 0 {
			recipe := NewRecipe(dirUrl, path, imagePath)
			recipe.rating = ratingInt
			rMap[path] = recipe
		}

		if rating == "" && imageName == "" {
			s.BlockNodeConverter("div", n)
		}
	}
}

// Validate no duplicate headers exist in the AST
func validateNoDuplicateHeaders(ast []djot_parser.TreeNode[djot_parser.DjotNode], path string) error {
	headings := make([]string, 0)
	seen := make(map[string]bool)

	var collectHeadings func(djot_parser.TreeNode[djot_parser.DjotNode])
	collectHeadings = func(node djot_parser.TreeNode[djot_parser.DjotNode]) {
		if node.Type == djot_parser.HeadingNode {
			headingText := strings.TrimSpace(string(node.FullText()))
			if headingText != "" {
				headings = append(headings, headingText)
			}
		}
	}

	for _, node := range ast {
		node.Traverse(collectHeadings)
	}

	for _, heading := range headings {
		if seen[heading] {
			return fmt.Errorf("duplicate header found in %s: \"%s\"", path, heading)
		}
		seen[heading] = true
	}

	return nil
}

// Converts djot string to rendered HTML
func renderDjot(text []byte, publicDir string, path string, rMap RecipeMap) string {
	ast := djot_parser.BuildDjotAst(text)

	err := validateNoDuplicateHeaders(ast, path)
	ExitOnError(err)

	section := djot_parser.NewConversionContext(
		"html",
		djot_parser.DefaultConversionRegistry,
		map[djot_parser.DjotNode]djot_parser.Conversion{
			djot_parser.DivNode:      formattedDivPartial(publicDir, path, rMap),
			djot_parser.ListItemNode: listItemConversion,
		},
	).ConvertDjotToHtml(&html_writer.HtmlWriter{}, ast...)
	return section
}

// Replaces .dj file with templated .html and .json files
func replaceDjWithHtml(publicDir string, rMap RecipeMap) filepath.WalkFunc {
	return func(path string, fileInfo os.FileInfo, inpErr error) error {
		if filepath.Ext(path) != ".dj" {
			return nil
		}

		if filepath.Base(path)[0] == '_' {
			defer log.Println(fmt.Sprintf("Skipping '_' prefixed page: %s", path))
		} else {
			text, err := os.ReadFile(path)
			if err != nil {
				return err
			}

			// Parse AST once for both HTML and plaintext
			ast := djot_parser.BuildDjotAst(text)
			err = validateNoDuplicateHeaders(ast, path)
			ExitOnError(err)

			// Generate HTML
			htmlSection := djot_parser.NewConversionContext(
				"html",
				djot_parser.DefaultConversionRegistry,
				map[djot_parser.DjotNode]djot_parser.Conversion{
					djot_parser.DivNode:      formattedDivPartial(publicDir, path, rMap),
					djot_parser.ListItemNode: listItemConversion,
				},
			).ConvertDjotToHtml(&html_writer.HtmlWriter{}, ast...)

			template := func() templ.Component {
				return recipePage(toTitleName(path)+" : Recipe", htmlSection)
			}
			writeTemplate(withHtmlExt(path), template)

			// Generate JSON for TRMNL
			jsonContent := renderDjotToJson(ast)
			jsonPath := strings.TrimSuffix(path, ".dj") + ".json"
			if err := os.WriteFile(jsonPath, []byte(jsonContent), 0o644); err != nil {
				return err
			}
		}

		if err := os.Remove(path); err != nil {
			return err
		}
		return nil
	}
}

// Create the HTML page based on a specified template function
func writeTemplate(writePath string, template func() templ.Component) error {
	html := new(bytes.Buffer)
	if err := template().Render(context.Background(), html); err != nil {
		return err
	}
	// file mode (permissions), set to 0644 for read/write permissions for the owner and read permissions for others
	if err := os.WriteFile(writePath, html.Bytes(), 0o644); err != nil {
		return err
	}
	return nil
}

// Create the nested `/*/index.html` files
func writeDirIndex(subDir string, recipes []Recipe) error {
	template := func() templ.Component {
		// Order recipes alphabetically
		sort.Slice(recipes, func(i, j int) bool {
			r := recipes
			return sort.StringsAreSorted([]string{r[i].name, r[j].name})
		})
		return dirIndexPage(toTitleName(subDir), recipes)
	}

	return writeTemplate(filepath.Join(subDir, "index.html"), template)
}

// Create `/index.html`
func writeHomeIndex(publicDir string, subdirectories []Subdir) error {
	template := func() templ.Component {
		return homePage(subdirectories)
	}

	return writeTemplate(filepath.Join(publicDir, "index.html"), template)
}

// Write all `/**/index.html` files
func writeIndexes(publicDir string, rMap RecipeMap) error {
	dirMap := make(map[string][]Recipe)
	for _, recipe := range rMap {
		key := recipe.dirUrl
		dirMap[key] = append(dirMap[key], recipe)
	}

	var subdirectories []Subdir

	// Prepare the alphabetized directory keys
	keys := make([]string, 0, len(dirMap))
	for k := range dirMap {
		keys = append(keys, k)
	}
	slices.Sort(keys)

	for _, key := range keys {
		recipes := dirMap[key]
		msg := fmt.Sprintf("Writing index for '%s' with %d recipes", key, len(recipes))
		log.Println(msg)

		if err := writeDirIndex(filepath.Join(publicDir, key), recipes); err != nil {
			return err
		}
		subdirectories = append(subdirectories, NewSubdir(key))
	}

	err := writeHomeIndex(publicDir, subdirectories)
	ExitOnError(err)

	return nil
}

// Public entry point
func Build(publicDir string) {
	var err error

	staticPages := map[string]func() templ.Component{
		"404.html":    notFoundPage,
		"search.html": searchPage,
	}
	for relPath, template := range staticPages {
		err = writeTemplate(filepath.Join(publicDir, relPath), template)
		ExitOnError(err)
	}

	rMap := make(map[string]Recipe)
	err = filepath.Walk(publicDir, replaceDjWithHtml(publicDir, rMap))
	ExitOnError(err)

	enrichRecipesWithMetadata(rMap, "content")
	filterData := generateFilterData(rMap)

	err = writeTemplate(filepath.Join(publicDir, "filters.html"), func() templ.Component {
		return filtersPage(filterData)
	})
	ExitOnError(err)

	err = writeIndexes(publicDir, rMap)
	ExitOnError(err)
}
