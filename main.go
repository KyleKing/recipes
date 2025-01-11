package main

import (
	"os"
	"path/filepath"

	"github.com/KyleKing/recipes/goBuild"
)

func main() {
	cwd, err := os.Getwd()
	goBuild.ExitOnError(err)

	goBuild.Build(filepath.Join(cwd, "public"))
}
