package goBuild

import (
	"path/filepath"
	"sync"
	"time"

	"github.com/sivukhin/godjot/djot_parser"
)

type Subdir struct {
	url  string
	name string
}

func NewSubdir(key string) Subdir {
	return Subdir{url: key, name: toTitleName(key)}
}

type Recipe struct {
	dirUrl           string
	imagePath        string
	name             string
	url              string
	rating           int
	createdAt        time.Time
	modifiedAt       time.Time
	category         string
	relatedRecipes   []RelatedRecipe
	ingredientTokens []string
	totalRecipeCount int
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

type RelatedRecipe struct {
	recipe            Recipe
	similarityScore   float64
	sharedIngredients []string
	sharedTitleWords  []string
	ingredientScore   float64
	titleScore        float64
}

type RecipeIngredients struct {
	filePath    string
	recipe      Recipe
	title       string
	ingredients []string
	tokens      map[string]bool
}

type IngredientIndex map[string]RecipeIngredients

type FilterData struct {
	NotYet           []Recipe
	RandomByCategory map[string][]Recipe
	RecentlyAdded    []Recipe
	LeastUpdated     []Recipe
	HighestRated     []Recipe
	LowestRated      []Recipe
}

type CachedRecipe struct {
	path        string
	content     []byte
	ast         []djot_parser.TreeNode[djot_parser.DjotNode]
	ingredients []string
}

type RecipeCache struct {
	mu      sync.RWMutex
	recipes map[string]*CachedRecipe
}

func NewRecipeCache() *RecipeCache {
	return &RecipeCache{
		recipes: make(map[string]*CachedRecipe),
	}
}

func (c *RecipeCache) Get(path string) (*CachedRecipe, bool) {
	c.mu.RLock()
	defer c.mu.RUnlock()
	recipe, exists := c.recipes[path]
	return recipe, exists
}

func (c *RecipeCache) Set(path string, recipe *CachedRecipe) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.recipes[path] = recipe
}
