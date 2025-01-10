package goBuild

import (
	"fmt"
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

func exitOnError(err error) {
	if err != nil {
		fmt.Println(err)
		os.Exit(1)
	}
}
