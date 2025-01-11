package goBuild

import "path/filepath"

type Subdir struct {
	url  string
	name string
}

func NewSubdir(key string) Subdir {
	return Subdir{url: key, name: toTitleName(key)}
}

type Recipe struct {
	dirUrl    string
	imagePath string
	name      string
	url       string
}

func NewRecipe(dirUrl string, path string, imagePath string) Recipe {
	return Recipe{
		dirUrl:    dirUrl,
		imagePath: imagePath,
		name:      toTitleName(path),
		url:       "/" + filepath.Join(dirUrl, withHtmlExt(filepath.Base(path))),
	}
}

type RecipeMap map[string]Recipe
