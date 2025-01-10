package goBuild

// Subdirectory

type Subdir struct {
	url  string
	name string
}

func NewSubdir(key string) Subdir {
	return Subdir{url: key, name: toTitleCase(key)}
}

// Recipes

type Recipe struct {
	parentUrl string
	imagePath string
	name      string
	url       string
}

func NewRecipe(parentUrl string, imagePath string, name string, url string) *Recipe {
	return &Recipe{
		parentUrl: parentUrl,
		imagePath: imagePath,
		name:      name,
		url:       url,
	}
}

type RecipeMap map[string]Recipe

// Maybe `type ContentContext`? With pathFile, publicDir, etc.
