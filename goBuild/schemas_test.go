package goBuild

import (
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
)

func TestNewSubdir(t *testing.T) {
	t.Run("create subdir", func(t *testing.T) {
		subdir := NewSubdir("main")
		assert.Equal(t, "main", subdir.url)
		assert.Equal(t, "Main", subdir.name)
	})

	t.Run("create subdir with underscores", func(t *testing.T) {
		subdir := NewSubdir("breakfast_brunch")
		assert.Equal(t, "breakfast_brunch", subdir.url)
		assert.Equal(t, "Breakfast Brunch", subdir.name)
	})
}

func TestNewRecipe(t *testing.T) {
	t.Run("create recipe with basic info", func(t *testing.T) {
		recipe := NewRecipe("main", "public/main/chicken_rice.html", "/main/chicken_rice.jpg")

		assert.Equal(t, "main", recipe.dirUrl)
		assert.Equal(t, "/main/chicken_rice.jpg", recipe.imagePath)
		assert.Equal(t, "Chicken Rice", recipe.name)
		assert.Equal(t, "/main/chicken_rice.html", recipe.url)
		assert.Equal(t, -1, recipe.rating)
		assert.Equal(t, "Main", recipe.category)
		assert.True(t, recipe.createdAt.IsZero())
		assert.True(t, recipe.modifiedAt.IsZero())
	})

	t.Run("create recipe with nested path", func(t *testing.T) {
		recipe := NewRecipe("dessert/cakes", "public/dessert/cakes/chocolate.html", "None")

		assert.Equal(t, "dessert/cakes", recipe.dirUrl)
		assert.Equal(t, "None", recipe.imagePath)
		assert.Equal(t, "Chocolate", recipe.name)
		assert.Contains(t, recipe.url, "chocolate.html")
		// toTitleName extracts just the directory name, not the full path
		assert.Equal(t, "Cakes", recipe.category)
	})
}

func TestRecipeCacheGetSet(t *testing.T) {
	cache := NewRecipeCache()

	t.Run("get from empty cache", func(t *testing.T) {
		_, exists := cache.Get("nonexistent")
		assert.False(t, exists)
	})

	t.Run("set and get", func(t *testing.T) {
		cached := &CachedRecipe{
			path:        "content/test.dj",
			content:     []byte("test content"),
			ingredients: []string{"flour", "sugar"},
		}

		cache.Set("content/test.dj", cached)

		retrieved, exists := cache.Get("content/test.dj")
		assert.True(t, exists)
		assert.Equal(t, "content/test.dj", retrieved.path)
		assert.Equal(t, []byte("test content"), retrieved.content)
		assert.Len(t, retrieved.ingredients, 2)
	})

	t.Run("overwrite existing", func(t *testing.T) {
		cached1 := &CachedRecipe{
			path:    "content/test.dj",
			content: []byte("original"),
		}
		cache.Set("content/test.dj", cached1)

		cached2 := &CachedRecipe{
			path:    "content/test.dj",
			content: []byte("updated"),
		}
		cache.Set("content/test.dj", cached2)

		retrieved, _ := cache.Get("content/test.dj")
		assert.Equal(t, []byte("updated"), retrieved.content)
	})
}

func TestNewRecipeCache(t *testing.T) {
	cache := NewRecipeCache()
	assert.NotNil(t, cache)
	assert.NotNil(t, cache.recipes)
	assert.Empty(t, cache.recipes)
}

func TestRelatedRecipeStructure(t *testing.T) {
	recipe := Recipe{
		name: "Test Recipe",
		url:  "/test.html",
	}

	related := RelatedRecipe{
		recipe:            recipe,
		similarityScore:   0.85,
		sharedIngredients: []string{"flour", "sugar"},
		sharedTitleWords:  []string{"chocolate"},
		ingredientScore:   0.75,
		titleScore:        0.95,
	}

	assert.Equal(t, "Test Recipe", related.recipe.name)
	assert.Equal(t, 0.85, related.similarityScore)
	assert.Len(t, related.sharedIngredients, 2)
	assert.Contains(t, related.sharedIngredients, "flour")
	assert.Contains(t, related.sharedIngredients, "sugar")
	assert.Len(t, related.sharedTitleWords, 1)
	assert.Equal(t, "chocolate", related.sharedTitleWords[0])
}

func TestRecipeIngredientsStructure(t *testing.T) {
	recipe := Recipe{name: "Test"}
	tokens := map[string]bool{
		"flour": true,
		"sugar": true,
	}

	recipeIng := RecipeIngredients{
		filePath:    "content/test.dj",
		recipe:      recipe,
		title:       "Test Recipe",
		ingredients: []string{"1 cup flour", "2 cups sugar"},
		tokens:      tokens,
	}

	assert.Equal(t, "content/test.dj", recipeIng.filePath)
	assert.Equal(t, "Test", recipeIng.recipe.name)
	assert.Equal(t, "Test Recipe", recipeIng.title)
	assert.Len(t, recipeIng.ingredients, 2)
	assert.Len(t, recipeIng.tokens, 2)
	assert.True(t, recipeIng.tokens["flour"])
	assert.True(t, recipeIng.tokens["sugar"])
}

func TestFilterDataStructure(t *testing.T) {
	now := time.Now()
	recipe1 := Recipe{name: "Recipe 1", createdAt: now}
	recipe2 := Recipe{name: "Recipe 2", createdAt: now.Add(-24 * time.Hour)}

	filterData := FilterData{
		NotYet:           []Recipe{recipe1},
		RandomByCategory: map[string][]Recipe{"main": {recipe1, recipe2}},
		RecentlyAdded:    []Recipe{recipe1, recipe2},
		LeastUpdated:     []Recipe{recipe2},
		HighestRated:     []Recipe{recipe1},
		LowestRated:      []Recipe{recipe2},
	}

	assert.Len(t, filterData.NotYet, 1)
	assert.Len(t, filterData.RandomByCategory["main"], 2)
	assert.Len(t, filterData.RecentlyAdded, 2)
	assert.Len(t, filterData.LeastUpdated, 1)
	assert.Len(t, filterData.HighestRated, 1)
	assert.Len(t, filterData.LowestRated, 1)
}
