package goBuild

import (
	"bytes"
	"context"
	"fmt"
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

const BUILD_DIR = "public"
const IMAGE_PLACEHOLDER = "/_icons/placeholder.webp"

func toTitleCase(str string) string {
	words := []string{}
	for _, part := range strings.Split(str, "_") {
		if len(part) > 0 {
			word := strings.Title(part)
			words = append(words, word)
		}
	}
	return strings.Join(words, " ")
}

func toName(path string) string {
	basename, _, _ := strings.Cut(filepath.Base(path), ".")
	return toTitleCase(basename)
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
		}).WriteString("\n")
	} else {
		s.BlockNodeConverter("li", n)
	}
}

// TODO: flatten call depth to pass this as a parameter rather than global
var TOC *RecipeTOC = NewRecipeTOC()

// Outer partial returns an inner converter that conditionally converts a div based on attached attributes
func formattedDivPartial(path string) func(djot_parser.ConversionState, func(djot_parser.Children)) {
	return func(s djot_parser.ConversionState, n func(c djot_parser.Children)) {
		_, parentUrl, found := strings.Cut(filepath.Dir(path), "/"+BUILD_DIR+"/")
		if !found {
			defer fmt.Println(fmt.Sprintf("Warn: failed to locate '/%s/' in '%s'", BUILD_DIR, path))
		}

		rating := s.Node.Attributes.Get("rating")
		if rating != "" {
			displayedRating := "..."
			ratingInt, err := strconv.Atoi(rating)
			if err != nil {
				fmt.Println(fmt.Sprintf("Error in rating '%s' of '%s'", rating, path))
				displayedRating = fmt.Sprintf("%s in rating (%s)", err, rating)
			} else {
				if 1 <= ratingInt && ratingInt <= 5 {
					displayedRating = fmt.Sprintf("%d / 5", ratingInt)
				} else if ratingInt == 0 {
					displayedRating = "Not yet rated"
				} else {
					displayedRating = fmt.Sprintf("Rating is not within [0,5] (%d)", ratingInt)
				}
			}
			s.Writer.WriteString("<p>Personal rating: " + displayedRating + "</p>").WriteString("\n")
		}

		imagePath := ""
		imageName := s.Node.Attributes.Get("image")
		if imageName != "" {
			if strings.Contains(imageName, ".") {
				imagePath = "/" + filepath.Join(parentUrl, imageName)
				s.Writer.WriteString("<img class=\"image-recipe\" alt=\"" + imageName + "\" src=\"" + imagePath + "\">")
			} else {
				imagePath = IMAGE_PLACEHOLDER
				s.Writer.WriteString("<img class=\"image-recipe\" alt=\"Image is missing\" src=\"" + imagePath + "\">")
			}
			s.Writer.WriteString("\n")
		}

		if len(imagePath) > 0 {
			TOC.recipes = append(TOC.recipes, Recipe{parentUrl: parentUrl, imagePath: imagePath, name: toName(path)})
		}

		if rating == "" && imageName == "" {
			s.BlockNodeConverter("div", n)
		}
	}
}

// Converts djot string to rendered HTML
func RenderDjot(text []byte, path string) string {
	ast := djot_parser.BuildDjotAst(text)
	section := djot_parser.NewConversionContext(
		"html",
		djot_parser.DefaultConversionRegistry,
		map[djot_parser.DjotNode]djot_parser.Conversion{
			djot_parser.DivNode:      formattedDivPartial(path),
			djot_parser.ListItemNode: listItemConversion,
		},
	).ConvertDjotToHtml(&html_writer.HtmlWriter{}, ast...)
	return section
}

// Merges rendered HTML with overall template
func buildHtml(path string) (*bytes.Buffer, error) {
	html := new(bytes.Buffer)

	text, err := os.ReadFile(path)
	if err != nil {
		return html, err
	}

	section := RenderDjot(text, path)
	component := recipePage(toName(path)+" : Recipe", section)
	if err := component.Render(context.Background(), html); err != nil {
		return nil, err
	}

	return html, nil
}

// Replaces .dj file with templated .html one
func replaceDjWithHtml(path string, fileInfo os.FileInfo, inpErr error) error {
	if filepath.Ext(path) != ".dj" {
		return nil
	}

	if filepath.Base(path)[0] == '_' {
		defer fmt.Println(fmt.Sprintf("Skipping '_' prefixed page: %s", path))
	} else {
		html, err := buildHtml(path)
		if err != nil {
			return err
		}
		newPath := strings.TrimSuffix(path, filepath.Ext(path)) + ".html"
		// file mode (permissions), set to 0644 for read/write permissions for the owner and read permissions for others
		if err := os.WriteFile(newPath, html.Bytes(), 0644); err != nil {
			return err
		}
	}

	if err := os.Remove(path); err != nil {
		return err
	}
	return nil
}

// Create the static HTML page based on specified template
func writeStatic(writePath string, template func() templ.Component) error {
	html := new(bytes.Buffer)

	component := template()
	if err := component.Render(context.Background(), html); err != nil {
		return err
	}
	if err := os.WriteFile(writePath, html.Bytes(), 0644); err != nil {
		return err
	}

	return nil
}

// Create the TOC pages
func writeTOC(subDir string, subTOC *RecipeTOC) error {
	html := new(bytes.Buffer)

	// Order recipes alphabetically
	sort.Slice(subTOC.recipes, func(i int, j int) bool {
		r := subTOC.recipes
		return sort.StringsAreSorted([]string{r[i].name, r[j].name})
	})

	component := tocPage(subTOC)
	if err := component.Render(context.Background(), html); err != nil {
		return err
	}
	writePath := filepath.Join(subDir, "index.html")
	if err := os.WriteFile(writePath, html.Bytes(), 0644); err != nil {
		return err
	}

	return nil
}

// Create the home index.html
func writeHome(buildDir string, subdirectories *Subdirectories) error {
	html := new(bytes.Buffer)

	component := homePage(subdirectories)
	if err := component.Render(context.Background(), html); err != nil {
		return err
	}
	writePath := filepath.Join(buildDir, "index.html")
	if err := os.WriteFile(writePath, html.Bytes(), 0644); err != nil {
		return err
	}

	return nil
}

func writeTOCs(buildDir string) error {
	tocMap := make(map[string]*RecipeTOC)
	for _, recipe := range TOC.recipes {
		key := recipe.parentUrl

		switch subTOC := tocMap[key]; {
		case subTOC == nil:
			newTOC := NewRecipeTOC()
			newTOC.recipes = append(newTOC.recipes, recipe)
			tocMap[key] = newTOC
		default:
			subTOC.recipes = append(subTOC.recipes, recipe)
			tocMap[key] = subTOC
		}
	}

	subdirectories := NewSubdirectories()

	keys := make([]string, 0, len(tocMap))
	for k := range tocMap {
		keys = append(keys, k)
	}
	slices.Sort(keys)
	for _, key := range keys {
		subTOC := tocMap[key]
		fmt.Println(fmt.Sprintf("Writing index for '%s' with %d recipes", key, len(subTOC.recipes)))
		if err := writeTOC(filepath.Join(buildDir, key), subTOC); err != nil {
			return err
		}
		subdirectories.each = append(subdirectories.each, NewSubdir(key))
	}

	if err := writeHome(buildDir, subdirectories); err != nil {
		fmt.Println(err)
		os.Exit(1)
	}
	return nil
}

func Build() {
	path, err := os.Getwd()
	if err != nil {
		fmt.Println(err)
		os.Exit(1)
	}

	buildDir := filepath.Join(path, BUILD_DIR)

	staticPages := map[string]func() templ.Component{
		"404.html":    notFoundPage,
		"search.html": searchPage,
	}
	for relPath, template := range staticPages {
		if err := writeStatic(filepath.Join(buildDir, relPath), template); err != nil {
			fmt.Println(err)
			os.Exit(1)
		}
	}

	if err := filepath.Walk(buildDir, replaceDjWithHtml); err != nil {
		fmt.Println(err)
		os.Exit(1)
	}

	if err := writeTOCs(buildDir); err != nil {
		fmt.Println(err)
		os.Exit(1)
	}
}
