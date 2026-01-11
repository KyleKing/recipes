package goBuild

import (
	"path/filepath"
	"time"
)

type Subdir struct {
	url  string
	name string
}

func NewSubdir(key string) Subdir {
	return Subdir{url: key, name: toTitleName(key)}
}

type Recipe struct {
	dirUrl     string
	imagePath  string
	name       string
	url        string
	rating     int
	createdAt  time.Time
	modifiedAt time.Time
	category   string
}

func NewRecipe(dirUrl string, path string, imagePath string) Recipe {
	return Recipe{
		dirUrl:     dirUrl,
		imagePath:  imagePath,
		name:       toTitleName(path),
		url:        "/" + filepath.Join(dirUrl, withHtmlExt(filepath.Base(path))),
		rating:     -1,
		createdAt:  time.Time{},
		modifiedAt: time.Time{},
		category:   toTitleName(dirUrl),
	}
}

type RecipeMap map[string]Recipe

type FilterData struct {
	NotYetMade       []Recipe
	RandomByCategory map[string][]Recipe
	RecentlyAdded    []Recipe
	LeastUpdated     []Recipe
	HighestRated     []Recipe
	LowestRated      []Recipe
}
