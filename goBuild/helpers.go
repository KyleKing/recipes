package goBuild

import (
	"log"
	"os"
	"path/filepath"
	"strings"
)

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

func toTitleName(path string) string {
	basename, _, _ := strings.Cut(filepath.Base(path), ".")
	return toTitleCase(basename)
}

func withHtmlExt(path string) string {
	return strings.TrimSuffix(path, filepath.Ext(path)) + ".html"
}

func ExitOnError(err error) {
	if err != nil {
		log.Fatal(err)
		os.Exit(1)
	}
}
