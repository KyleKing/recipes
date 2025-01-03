package main

import (
	"fmt"
	"log"
	"os"
	"path/filepath"
	"strings"

	"github.com/sivukhin/godjot/djot_parser"
	"github.com/sivukhin/godjot/html_writer"
)

// type FileCache struct {
// 	cache map[string][]byte
// }
//
// func (fc *FileCache) ReadFile(pth string) ([]byte, error) {
// 	cachedFile, ok := fc.cache[pth]
// 	if ok {
// 		return cachedFile, nil
// 	}
//
// 	data, err := os.ReadFile(pth)
// 	if err != nil {
// 		log.Printf("Error reading file %s: %v", pth, err)
// 		return nil, err
// 	}
// 	fc.cache[pth] = data
// 	return data, nil
// }
// fc := FileCache{cache: make(map[string][]byte)}

func TraverseDirectory(directory string, cb func(string) error) error {
	paths, err := filepath.Glob(directory + "/*")
	if err != nil {
		return err
	}

	for _, pth := range paths {
		stat, err := os.Stat(pth)
		if err != nil {
			fmt.Println(err)
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

func GetBasename(path string) string {
	basename := filepath.Base(path)
	if len(basename) > 0 && basename[len(basename)-1] == '.' {
		basename = basename[:len(basename)-1]
	}
	return basename
}

func ToTitleCase(str string) string {
	words := []string{}
	for _, part := range strings.Split(str, "_") {
		if len(part) > 0 && part[0] == '_' || part[len(part)-1] == '.' {
			continue
		}
		if len(words) > 0 {
			words = append(words, part)
		} else if len(part) > 0 {
			words = []string{part}
		}
	}

	titles := make([]string, 0, len(words))
	for _, word := range words {
		titles = append(titles, strings.ToUpper(string(word[0]))+strings.ToLower(string(word[1:])))
	}

	return strings.Join(titles, " ")
}

func WriteDjotToHtml(pth string) error {
	if filepath.Ext(pth) != ".dj" {
		return nil
	}
	baseName := GetBasename(pth)
	if baseName[0] == '_' || baseName[len(baseName)-1] == '.' {
		fmt.Println(fmt.Sprintf("Skipping '_' prefixed page: %s", pth))
		if err := os.Remove(pth); err != nil {
			return err
		}
		return nil
	}

	header, err := os.ReadFile("templates/header.html")
	if err != nil {
		log.Printf("Error reading file %s: %v", "templates/header.html", err)
		return err
	}
	// header = strings.ReplaceAll(header, "{TITLE}", `Recipe: ${ToTitleCase(baseName)}`)

	footer, err := os.ReadFile("templates/footer.html")
	if err != nil {
		log.Printf("Error reading file %s: %v", "templates/footer.html", err)
		return err
	}

	text, err := os.ReadFile(pth)
	if err != nil {
		return err
	}
	ast := djot_parser.BuildDjotAst(text)
	section := djot_parser.NewConversionContext(
		"html",
		djot_parser.DefaultConversionRegistry,
		map[djot_parser.DjotNode]djot_parser.Conversion{
			/*
				   You can overwrite default conversion rules with custom map
				   djot_parser.ImageNode: func(state djot_parser.ConversionState, next func(c djot_parser.Children)) {
					   state.Writer.
					       OpenTag("figure").
					       OpenTag("img", state.Node.Attributes.Entries()...).
					       OpenTag("figcaption").
					       WriteString(state.Node.Attributes.Get(djot_parser.ImgAltKey)).
					       CloseTag("figcaption").
					       CloseTag("figure")
				   }
			*/
		},
	).ConvertDjotToHtml(&html_writer.HtmlWriter{}, ast...)
	html := fmt.Sprintf("%s\n%s\n%s", header, section, footer)

	newPth := strings.TrimSuffix(pth, filepath.Ext(pth)) + ".html"
	if err := os.WriteFile(newPth, []byte(html), 0644); err != nil {
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
		log.Println(err)
		os.Exit(1)
	}
	if err := TraverseDirectory(filepath.Join(path, "public"), WriteDjotToHtml); err != nil {
		fmt.Println(err)
		os.Exit(1)
	}
}
