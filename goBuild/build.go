package goBuild

import (
	"bytes"
	"context"
	"fmt"
	"os"
	"path/filepath"
	"slices"
	"strconv"
	"strings"

	"github.com/a-h/templ"
	"github.com/sivukhin/godjot/djot_parser"
	"github.com/sivukhin/godjot/djot_tokenizer"
	"github.com/sivukhin/godjot/html_writer"
)

const BUILD_DIR = "public"
const IMAGE_PLACEHOLDER = "/_icons/placeholder.webp"

// TODO: see pathlib.Walk and WalkFunc instead of custom
// Apply 'callback' to all regular files within the directory
func traverseDirectory(directory string, cb func(string) error) error {
	paths, err := filepath.Glob(directory + "/*")
	if err != nil {
		return err
	}

	for _, pth := range paths {
		stat, err := os.Stat(pth)
		if err != nil {
			return err
		}
		switch mode := stat.Mode(); {
		case mode.IsDir():
			if err := traverseDirectory(pth, cb); err != nil {
				return err
			}
		case mode.IsRegular():
			if filepath.Ext(pth) == ".dj" {
				if err := cb(pth); err != nil {
					return err
				}
			}
		}
	}
	return nil
}

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

func toName(pth string) string {
	basename, _, _ := strings.Cut(filepath.Base(pth), ".")
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

type Recipe struct {
	parentUrl string
	imagePth  string
	name      string
}

type RecipeTOC struct {
	recipes []Recipe
}

// Initializes empty RecipeTOC
func NewRecipeTOC() *RecipeTOC {
	return &RecipeTOC{
		recipes: make([]Recipe, 0),
	}
}

type Subdir struct {
	url  string
	name string
}

type Subdirectories struct {
	each []Subdir
}

// Initializes empty Subdirectories
func NewSubdirectories() *Subdirectories {
	return &Subdirectories{
		each: make([]Subdir, 0),
	}
}

// TODO: flatten call depth to pass this as a parameter rather than global
var TOC *RecipeTOC = NewRecipeTOC()

// Outer partial returns an inner converter that conditionally converts a div based on attached attributes
func formattedDivPartial(pth string) func(djot_parser.ConversionState, func(djot_parser.Children)) {
	return func(s djot_parser.ConversionState, n func(c djot_parser.Children)) {
		_, parentUrl, found := strings.Cut(filepath.Dir(pth), "/"+BUILD_DIR+"/")
		if !found {
			defer fmt.Println(fmt.Sprintf("Warn: failed to locate '/%s/' in '%s'", BUILD_DIR, pth))
		}

		rating := s.Node.Attributes.Get("rating")
		if rating != "" {
			displayedRating := "..."
			ratingInt, err := strconv.Atoi(rating)
			if err != nil {
				fmt.Println(fmt.Sprintf("Error in rating '%s' of '%s'", rating, pth))
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

		imagePth := ""
		imageName := s.Node.Attributes.Get("image")
		if imageName != "" {
			if strings.Contains(imageName, ".") {
				imagePth = "/" + filepath.Join(parentUrl, imageName)
				s.Writer.WriteString("<img class=\"image-recipe\" alt=\"" + imageName + "\" src=\"" + imagePth + "\">")
			} else {
				imagePth = IMAGE_PLACEHOLDER
				s.Writer.WriteString("<img class=\"image-recipe\" alt=\"Image is missing\" src=\"" + imagePth + "\">")
			}
			s.Writer.WriteString("\n")
		}

		if len(imagePth) > 0 {
			TOC.recipes = append(TOC.recipes, Recipe{parentUrl: parentUrl, imagePth: imagePth, name: toName(pth)})
		}

		if rating == "" && imageName == "" {
			s.BlockNodeConverter("div", n)
		}
	}
}

// Converts djot string to rendered HTML
func RenderDjot(text []byte, pth string) string {
	ast := djot_parser.BuildDjotAst(text)
	section := djot_parser.NewConversionContext(
		"html",
		djot_parser.DefaultConversionRegistry,
		map[djot_parser.DjotNode]djot_parser.Conversion{
			djot_parser.DivNode:      formattedDivPartial(pth),
			djot_parser.ListItemNode: listItemConversion,
		},
	).ConvertDjotToHtml(&html_writer.HtmlWriter{}, ast...)
	return section
}

// Merges rendered HTML with overall template
func buildHtml(pth string) (*bytes.Buffer, error) {
	html := new(bytes.Buffer)

	text, err := os.ReadFile(pth)
	if err != nil {
		return html, err
	}

	section := RenderDjot(text, pth)
	component := recipePage(toName(pth)+" : Recipe", section)
	if err := component.Render(context.Background(), html); err != nil {
		return nil, err
	}

	return html, nil
}

// Replaces .dj file with templated .html one
func replaceDjWithHtml(pth string) error {
	if filepath.Ext(pth) != ".dj" {
		return nil
	}

	if filepath.Base(pth)[0] == '_' {
		defer fmt.Println(fmt.Sprintf("Skipping '_' prefixed page: %s", pth))
	} else {
		html, err := buildHtml(pth)
		if err != nil {
			return err
		}
		newPth := strings.TrimSuffix(pth, filepath.Ext(pth)) + ".html"
		// file mode (permissions), set to 0644 for read/write permissions for the owner and read permissions for others
		if err := os.WriteFile(newPth, html.Bytes(), 0644); err != nil {
			return err
		}
	}

	if err := os.Remove(pth); err != nil {
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
		subdirectories.each = append(subdirectories.each, Subdir{url: key, name: toTitleCase(key)})
	}

	if err := writeHome(buildDir, subdirectories); err != nil {
		fmt.Println(err)
		os.Exit(1)
	}
	return nil
}

func Build() {
	pth, err := os.Getwd()
	if err != nil {
		fmt.Println(err)
		os.Exit(1)
	}

	buildDir := filepath.Join(pth, BUILD_DIR)

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

	if err := traverseDirectory(buildDir, replaceDjWithHtml); err != nil {
		fmt.Println(err)
		os.Exit(1)
	}

	if err := writeTOCs(buildDir); err != nil {
		fmt.Println(err)
		os.Exit(1)
	}
}
