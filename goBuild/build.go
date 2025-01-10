package goBuild

import (
	"bytes"
	"context"
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

const IMAGE_PLACEHOLDER = "/_icons/placeholder.webp"

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

// Curry conditionally converting `<div>` based on attached attributes
func formattedDivPartial(path string, rMap RecipeMap) func(djot_parser.ConversionState, func(djot_parser.Children)) {
	return func(s djot_parser.ConversionState, n func(c djot_parser.Children)) {
		// TODO: use `filepath.relative` instead and replace `/public/` by passing in `publicDir`
		_, parentUrl, found := strings.Cut(filepath.Dir(path), "/public/")
		if !found {
			defer log.Println(fmt.Sprintf("Warn: failed to locate '/%s/' in '%s'", "/public/", path))
		}

		rating := s.Node.Attributes.Get("rating")
		if rating != "" {
			ratingInt, err := strconv.Atoi(rating)
			exitOnError(err)

			displayedRating := "..."
			if 1 <= ratingInt && ratingInt <= 5 {
				displayedRating = fmt.Sprintf("%d / 5", ratingInt)
			} else if ratingInt == 0 {
				displayedRating = "Not yet rated"
			} else {
				displayedRating = fmt.Sprintf("Rating is not within [0,5] (%d)", ratingInt)
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
			rMap[path] = Recipe{parentUrl: parentUrl, imagePath: imagePath, name: toTitleName(path), url: path}
		}

		if rating == "" && imageName == "" {
			s.BlockNodeConverter("div", n)
		}
	}
}

// Converts djot string to rendered HTML
func RenderDjot(text []byte, path string, rMap RecipeMap) string {
	ast := djot_parser.BuildDjotAst(text)
	section := djot_parser.NewConversionContext(
		"html",
		djot_parser.DefaultConversionRegistry,
		map[djot_parser.DjotNode]djot_parser.Conversion{
			djot_parser.DivNode:      formattedDivPartial(path, rMap),
			djot_parser.ListItemNode: listItemConversion,
		},
	).ConvertDjotToHtml(&html_writer.HtmlWriter{}, ast...)
	return section
}

// Replaces .dj file with templated .html one
func replaceDjWithHtml(rMap RecipeMap) filepath.WalkFunc {
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

			section := RenderDjot(text, path, rMap)
			template := func() templ.Component {
				return recipePage(toTitleName(path)+" : Recipe", section)
			}
			newPath := strings.TrimSuffix(path, filepath.Ext(path)) + ".html"
			writeTemplate(newPath, template)
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
	if err := os.WriteFile(writePath, html.Bytes(), 0644); err != nil {
		return err
	}
	return nil
}

// Create the nested `/*/index.html` files
func writeDirIndex(subDir string, recipes []Recipe) error {

	template := func() templ.Component {
		// Order recipes alphabetically
		sort.Slice(recipes, func(i int, j int) bool {
			r := recipes
			return sort.StringsAreSorted([]string{r[i].name, r[j].name})
		})
		return dirIndexPage(toTitleName(subDir), recipes)
	}

	return writeTemplate(filepath.Join(subDir, "index.html"), template)
}

// Create `/index.html`
func writeHome(publicDir string, subdirectories []Subdir) error {

	template := func() templ.Component {
		return homePage(subdirectories)
	}

	return writeTemplate(filepath.Join(publicDir, "index.html"), template)
}

// Write all `/**/index.html` files
func writeIndexes(publicDir string, rMap RecipeMap) error {
	dirMap := make(map[string][]Recipe)
	for _, recipe := range rMap {
		key := recipe.parentUrl
		dirMap[key] = append(dirMap[key], recipe)
	}

	var subdirectories []Subdir

	// Prepare the alphabetize directory keys
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

	err := writeHome(publicDir, subdirectories)
	exitOnError(err)

	return nil
}

func Build() {
	path, err := os.Getwd()
	exitOnError(err)

	publicDir := filepath.Join(path, "public")

	staticPages := map[string]func() templ.Component{
		"404.html":    notFoundPage,
		"search.html": searchPage,
	}
	for relPath, template := range staticPages {
		err = writeTemplate(filepath.Join(publicDir, relPath), template)
		exitOnError(err)
	}

	rMap := make(map[string]Recipe)
	err = filepath.Walk(publicDir, replaceDjWithHtml(rMap))
	exitOnError(err)

	err = writeIndexes(publicDir, rMap)
	exitOnError(err)
}
