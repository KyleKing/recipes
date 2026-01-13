package goBuild

import (
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
)

func TestExcludesDrinksAndReference(t *testing.T) {
	tests := []struct {
		name     string
		recipe   Recipe
		expected bool
	}{
		{
			"main category - should include",
			Recipe{category: "Main"},
			true,
		},
		{
			"drinks category - should exclude",
			Recipe{category: "Drinks"},
			false,
		},
		{
			"reference category - should exclude",
			Recipe{category: "Reference"},
			false,
		},
		{
			"dessert category - should include",
			Recipe{category: "Dessert"},
			true,
		},
		{
			"case insensitive drinks",
			Recipe{category: "drinks"},
			false,
		},
		{
			"case insensitive reference",
			Recipe{category: "REFERENCE"},
			false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := excludesDrinksAndReference(tt.recipe)
			assert.Equal(t, tt.expected, result)
		})
	}
}

func TestFilterRecipes(t *testing.T) {
	recipes := []Recipe{
		{name: "Recipe 1", rating: 5},
		{name: "Recipe 2", rating: 3},
		{name: "Recipe 3", rating: 5},
		{name: "Recipe 4", rating: 1},
	}

	t.Run("filter high rated", func(t *testing.T) {
		filtered := filterRecipes(recipes, func(r Recipe) bool {
			return r.rating >= 4
		})
		assert.Len(t, filtered, 2)
		assert.Equal(t, "Recipe 1", filtered[0].name)
		assert.Equal(t, "Recipe 3", filtered[1].name)
	})

	t.Run("filter low rated", func(t *testing.T) {
		filtered := filterRecipes(recipes, func(r Recipe) bool {
			return r.rating <= 2
		})
		assert.Len(t, filtered, 1)
		assert.Equal(t, "Recipe 4", filtered[0].name)
	})
}

func TestSortByCreatedDesc(t *testing.T) {
	now := time.Now()
	recipes := []Recipe{
		{name: "Old", createdAt: now.Add(-72 * time.Hour)},
		{name: "Recent", createdAt: now.Add(-24 * time.Hour)},
		{name: "Newest", createdAt: now},
	}

	sortByCreatedDesc(recipes)

	assert.Equal(t, "Newest", recipes[0].name)
	assert.Equal(t, "Recent", recipes[1].name)
	assert.Equal(t, "Old", recipes[2].name)
}

func TestSortByCreatedAsc(t *testing.T) {
	now := time.Now()
	recipes := []Recipe{
		{name: "Recent", createdAt: now.Add(-24 * time.Hour)},
		{name: "Newest", createdAt: now},
		{name: "Old", createdAt: now.Add(-72 * time.Hour)},
	}

	sortByCreatedAsc(recipes)

	assert.Equal(t, "Old", recipes[0].name)
	assert.Equal(t, "Recent", recipes[1].name)
	assert.Equal(t, "Newest", recipes[2].name)
}

func TestSortByModifiedAsc(t *testing.T) {
	now := time.Now()
	recipes := []Recipe{
		{name: "Recently Modified", modifiedAt: now},
		{name: "Old Modified", modifiedAt: now.Add(-72 * time.Hour)},
		{name: "Medium Modified", modifiedAt: now.Add(-24 * time.Hour)},
	}

	sortByModifiedAsc(recipes)

	assert.Equal(t, "Old Modified", recipes[0].name)
	assert.Equal(t, "Medium Modified", recipes[1].name)
	assert.Equal(t, "Recently Modified", recipes[2].name)
}

func TestLimitRecipes(t *testing.T) {
	recipes := []Recipe{
		{name: "Recipe 1"},
		{name: "Recipe 2"},
		{name: "Recipe 3"},
		{name: "Recipe 4"},
		{name: "Recipe 5"},
	}

	t.Run("limit to 3", func(t *testing.T) {
		limited := limitRecipes(recipes, 3)
		assert.Len(t, limited, 3)
		assert.Equal(t, "Recipe 1", limited[0].name)
		assert.Equal(t, "Recipe 2", limited[1].name)
		assert.Equal(t, "Recipe 3", limited[2].name)
	})

	t.Run("limit exceeds length", func(t *testing.T) {
		limited := limitRecipes(recipes, 10)
		assert.Len(t, limited, 5)
	})

	t.Run("limit to 0", func(t *testing.T) {
		limited := limitRecipes(recipes, 0)
		assert.Len(t, limited, 0)
	})
}

func TestSelectRandomRecipes(t *testing.T) {
	recipes := []Recipe{
		{name: "Recipe 1"},
		{name: "Recipe 2"},
		{name: "Recipe 3"},
		{name: "Recipe 4"},
		{name: "Recipe 5"},
	}

	t.Run("select fewer than available", func(t *testing.T) {
		selected := selectRandomRecipes(recipes, 3, 12345)
		assert.Len(t, selected, 3)
	})

	t.Run("same seed produces same selection", func(t *testing.T) {
		seed := int64(12345)
		selected1 := selectRandomRecipes(recipes, 3, seed)
		selected2 := selectRandomRecipes(recipes, 3, seed)
		assert.Equal(t, selected1, selected2)
	})

	t.Run("different seeds produce different selections", func(t *testing.T) {
		selected1 := selectRandomRecipes(recipes, 3, 12345)
		selected2 := selectRandomRecipes(recipes, 3, 67890)
		// Very unlikely to be equal
		assert.NotEqual(t, selected1[0].name, selected2[0].name)
	})

	t.Run("request more than available returns all", func(t *testing.T) {
		selected := selectRandomRecipes(recipes, 10, 12345)
		assert.Len(t, selected, 5)
	})
}

func TestGenerateFilterData(t *testing.T) {
	now := time.Now()
	rMap := RecipeMap{
		"main/recipe1.html": Recipe{
			name:       "High Rated Recipe",
			category:   "Main",
			rating:     5,
			imagePath:  "/main/recipe1.jpg",
			createdAt:  now.Add(-24 * time.Hour),
			modifiedAt: now,
		},
		"dessert/recipe2.html": Recipe{
			name:       "No Image Recipe",
			category:   "Dessert",
			rating:     0,
			imagePath:  "None",
			createdAt:  now.Add(-48 * time.Hour),
			modifiedAt: now.Add(-24 * time.Hour),
		},
		"drinks/cocktail.html": Recipe{
			name:       "Cocktail",
			category:   "Drinks",
			rating:     4,
			imagePath:  "/drinks/cocktail.jpg",
			createdAt:  now,
			modifiedAt: now,
		},
		"main/lowrated.html": Recipe{
			name:       "Low Rated Recipe",
			category:   "Main",
			rating:     2,
			imagePath:  "/main/lowrated.jpg",
			createdAt:  now.Add(-72 * time.Hour),
			modifiedAt: now.Add(-72 * time.Hour),
		},
	}

	filterData := generateFilterData(rMap)

	t.Run("not yet contains unrated", func(t *testing.T) {
		assert.NotEmpty(t, filterData.NotYet)
		found := false
		for _, r := range filterData.NotYet {
			if r.name == "No Image Recipe" {
				found = true
				break
			}
		}
		assert.True(t, found)
	})

	t.Run("recently added excludes drinks", func(t *testing.T) {
		assert.NotEmpty(t, filterData.RecentlyAdded)
		for _, r := range filterData.RecentlyAdded {
			assert.NotEqual(t, "Drinks", r.category)
			assert.NotEqual(t, "Reference", r.category)
		}
	})

	t.Run("low rated contains low ratings", func(t *testing.T) {
		if len(filterData.LowestRated) > 0 {
			for _, r := range filterData.LowestRated {
				assert.LessOrEqual(t, r.rating, 2)
			}
		}
	})

	t.Run("high rated contains high ratings", func(t *testing.T) {
		if len(filterData.HighestRated) > 0 {
			for _, r := range filterData.HighestRated {
				assert.GreaterOrEqual(t, r.rating, 4)
			}
		}
	})
}
