package main

import (
	"bytes"
	"context"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/sivukhin/godjot/djot_parser"
	"github.com/sivukhin/godjot/djot_tokenizer"
	"github.com/sivukhin/godjot/html_writer"
)

const BUILD_DIR = "public"
const IMAGE_PLACEHOLDER = "/_icons/placeholder.webp"

// Apply 'callback' to all regular files within the directory
func TraverseDirectory(directory string, cb func(string) error) error {
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
			if err := TraverseDirectory(pth, cb); err != nil {
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

func ToTitleCase(str string) string {
	words := []string{}
	for _, part := range strings.Split(str, "_") {
		if len(part) > 0 {
			word := strings.Title(part)
			words = append(words, word)
		}
	}
	return strings.Join(words, " ")
}

// Convert 'li' nodes to either tasks or unstyled
// Note: adapted without 'disable' and without \n from: https://github.com/sivukhin/godjot/pull/12
func ListItemConversion(s djot_parser.ConversionState, n func(c djot_parser.Children)) {
	class := s.Node.Attributes.Get(djot_tokenizer.DjotAttributeClassKey)
	if class == djot_parser.CheckedTaskItemClass || class == djot_parser.UncheckedTaskItemClass {
		s.Writer.InTag("li")(func() {
			s.Writer.WriteString("<input type=\"checkbox\"")
			if class == djot_parser.CheckedTaskItemClass {
				s.Writer.WriteString(" checked=\"\"")
			}
			s.Writer.WriteString("/>")
			if len(s.Node.Children) > 1 {
				n(s.Node.Children[:1])
			}
		}).WriteString("\n")
	} else {
		s.BlockNodeConverter("li", n)
	}
}

// Outer partial returns an inner converter that conditionally converts a div based on attached attributes
func FormattedDivPartial(pth string) func(djot_parser.ConversionState, func(djot_parser.Children)) {
	return func(s djot_parser.ConversionState, n func(c djot_parser.Children)) {
		rating := s.Node.Attributes.Get("rating")
		if rating != "" {
			displayedRating := rating + " / 5"
			if rating == "0" {
				displayedRating = "Not yet rated"
			}
			s.Writer.WriteString("<p>Personal rating: " + displayedRating + "</p>").WriteString("\n")
		}

		imageName := s.Node.Attributes.Get("image")
		if imageName != "" {
			if strings.Contains(imageName, ".") {
				_, absPath, found := strings.Cut(filepath.Dir(pth), "/"+BUILD_DIR+"/")
				if !found {
					defer fmt.Println(fmt.Sprintf("Warn: failed to locate '/%s/' in '%s'", BUILD_DIR, pth))
				}
				pthImage := "/" + filepath.Join(absPath, imageName)
				s.Writer.WriteString("<img class=\"image-recipe\" alt=\"" + imageName + "\" src=\"" + pthImage + "\">")
			} else {
				s.Writer.WriteString("<img class=\"image-recipe\" alt=\"Image is missing\" src=\"" + IMAGE_PLACEHOLDER + "\">")
			}
			s.Writer.WriteString("\n")
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
			djot_parser.DivNode:      FormattedDivPartial(pth),
			djot_parser.ListItemNode: ListItemConversion,
		},
	).ConvertDjotToHtml(&html_writer.HtmlWriter{}, ast...)
	return section
}

// Merges rendered HTML with overall template
func BuildHtml(pth string) (*bytes.Buffer, error) {
	html := new(bytes.Buffer)

	text, err := os.ReadFile(pth)
	if err != nil {
		return html, err
	}

	basename, _, _ := strings.Cut(filepath.Base(pth), ".")
	usePagefind := !(strings.HasSuffix(pth, "index.dj"))
	section := RenderDjot(text, pth)
	component := page(ToTitleCase(basename)+" : Recipe", usePagefind, section)
	if err := component.Render(context.Background(), html); err != nil {
		return html, err
	}

	return html, nil
}

// Replaces .dj file with templated .html one
func ReplaceDjWithHtml(pth string) error {
	if filepath.Ext(pth) != ".dj" {
		return nil
	}

	if filepath.Base(pth)[0] == '_' {
		defer fmt.Println(fmt.Sprintf("Skipping '_' prefixed page: %s", pth))
	} else {
		html, err := BuildHtml(pth)
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

func main() {
	path, err := os.Getwd()
	if err != nil {
		fmt.Println(err)
		os.Exit(1)
	}

	if err := TraverseDirectory(filepath.Join(path, BUILD_DIR), ReplaceDjWithHtml); err != nil {
		fmt.Println(err)
		os.Exit(1)
	}
}
