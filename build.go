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
func ListItemConversion(s djot_parser.ConversionState, n func(c djot_parser.Children)) {
	class := s.Node.Attributes.Get(djot_tokenizer.DjotAttributeClassKey)
	if class == djot_parser.CheckedTaskItemClass || class == djot_parser.UncheckedTaskItemClass {
		s.Writer.InTag("li")(func() {
			s.Writer.WriteString("\n")
			// Adapted without 'disable' (https://github.com/sivukhin/godjot/pull/12)
			s.Writer.WriteString("<input type=\"checkbox\"")
			if class == djot_parser.CheckedTaskItemClass {
				s.Writer.WriteString(" checked=\"\"")
			}
			s.Writer.WriteString("/>").WriteString("\n")
			if len(s.Node.Children) > 1 {
				n(s.Node.Children[:1])
			}
			s.Writer.WriteString("\n")
		}).WriteString("\n")
	} else {
		s.BlockNodeConverter("li", n)
	}
}

// Converts djot string to rendered HTML
func RenderDjot(text []byte) string {
	ast := djot_parser.BuildDjotAst(text)
	section := djot_parser.NewConversionContext(
		"html",
		djot_parser.DefaultConversionRegistry,
		map[djot_parser.DjotNode]djot_parser.Conversion{
			djot_parser.ListItemNode: ListItemConversion,
		},
	).ConvertDjotToHtml(&html_writer.HtmlWriter{}, ast...)
	return section
}

// Replaces .dj file with templated .html one
func WriteDjotToHtml(pth string) error {
	if filepath.Ext(pth) != ".dj" {
		return nil
	}
	if filepath.Base(pth)[0] == '_' {
		defer fmt.Println(fmt.Sprintf("Skipping '_' prefixed page: %s", pth))
		if err := os.Remove(pth); err != nil {
			return err
		}
		return nil
	}

	text, err := os.ReadFile(pth)
	if err != nil {
		return err
	}

	section := RenderDjot(text)
	usePagefind := !(strings.HasSuffix(pth, "index.dj"))
	basename, _, _ := strings.Cut(filepath.Base(pth), ".")
	component := page(ToTitleCase(basename)+" : Recipe", usePagefind, section)
	html := new(bytes.Buffer)
	if err := component.Render(context.Background(), html); err != nil {
		return err
	}
	newPth := strings.TrimSuffix(pth, filepath.Ext(pth)) + "html"
	// file mode (permissions), set to 0644 for read/write permissions for the owner and read permissions for others
	if err := os.WriteFile(newPth, html.Bytes(), 0644); err != nil {
		return err
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
	if err := TraverseDirectory(filepath.Join(path, "public"), WriteDjotToHtml); err != nil {
		fmt.Println(err)
		os.Exit(1)
	}
}
