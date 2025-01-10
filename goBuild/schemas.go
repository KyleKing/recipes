package goBuild

// Subdirectory

type Subdir struct {
	url  string
	name string
}

func NewSubdir(key string) *Subdir {
	return &Subdir{url: key, name: toTitleCase(key)}
}

type Subdirectories struct {
	each []Subdir
}

func NewSubdirectories() *Subdirectories {
	return &Subdirectories{
		each: make([]Subdir, 0),
	}
}

// Recipes

type Recipe struct {
	parentUrl string
	imagePath string
	name      string
}

func NewRecipe(parentUrl string, imagePath string, name string) *Recipe {
	return &Recipe{
		parentUrl: parentUrl,
		imagePath: imagePath,
		name:      name,
	}
}

type RecipeTOC struct {
	recipes []Recipe
}

func NewRecipeTOC() *RecipeTOC {
	return &RecipeTOC{
		recipes: make([]Recipe, 0),
	}
}
