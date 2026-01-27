package goBuild

import (
	"math/rand"
	"sort"
	"strings"
	"time"
)

const (
	randomRecipesPerCategory = 3
	maxRecentlyAdded         = 8
	maxLeastUpdated          = 8
	secondsPerDay            = 86400

	categoryDrinks    = "drinks"
	categoryReference = "reference"
)

func enrichRecipesWithMetadata(rMap RecipeMap, contentDir string) {
	for path, recipe := range rMap {
		// Convert absolute path to relative path
		// path is like: /Users/.../recipes/public/main/recipe.dj
		// We need: content/main/recipe.dj
		djFilePath := strings.Replace(path, ".html", ".dj", 1)

		// Extract the relative path after "public/"
		if idx := strings.Index(djFilePath, "/public/"); idx >= 0 {
			djFilePath = contentDir + djFilePath[idx+len("/public"):]
		} else if idx := strings.Index(djFilePath, "public/"); idx >= 0 {
			djFilePath = contentDir + djFilePath[idx+len("public"):]
		}

		enrichRecipeWithGitInfo(&recipe, djFilePath)
		rMap[path] = recipe
	}
}

func selectRandomRecipes(recipes []Recipe, count int, seed int64) []Recipe {
	if len(recipes) <= count {
		return recipes
	}

	r := rand.New(rand.NewSource(seed))
	indices := r.Perm(len(recipes))[:count]

	selected := make([]Recipe, count)
	for i, idx := range indices {
		selected[i] = recipes[idx]
	}

	return selected
}

func excludesDrinksAndReference(recipe Recipe) bool {
	categoryLower := strings.ToLower(recipe.category)
	return categoryLower != categoryDrinks && categoryLower != categoryReference
}

func filterRecipes(recipes []Recipe, predicate func(Recipe) bool) []Recipe {
	filtered := make([]Recipe, 0)
	for _, recipe := range recipes {
		if predicate(recipe) {
			filtered = append(filtered, recipe)
		}
	}
	return filtered
}

func sortByCreatedDesc(recipes []Recipe) {
	sort.Slice(recipes, func(i, j int) bool {
		if recipes[i].createdAt.IsZero() && !recipes[j].createdAt.IsZero() {
			return false
		}
		if !recipes[i].createdAt.IsZero() && recipes[j].createdAt.IsZero() {
			return true
		}
		return recipes[i].createdAt.After(recipes[j].createdAt)
	})
}

func sortByCreatedAsc(recipes []Recipe) {
	sort.Slice(recipes, func(i, j int) bool {
		if recipes[i].createdAt.IsZero() && !recipes[j].createdAt.IsZero() {
			return false
		}
		if !recipes[i].createdAt.IsZero() && recipes[j].createdAt.IsZero() {
			return true
		}
		return recipes[i].createdAt.Before(recipes[j].createdAt)
	})
}

func sortByModifiedAsc(recipes []Recipe) {
	sort.Slice(recipes, func(i, j int) bool {
		if recipes[i].modifiedAt.IsZero() && !recipes[j].modifiedAt.IsZero() {
			return false
		}
		if !recipes[i].modifiedAt.IsZero() && recipes[j].modifiedAt.IsZero() {
			return true
		}
		return recipes[i].modifiedAt.Before(recipes[j].modifiedAt)
	})
}

func limitRecipes(recipes []Recipe, max int) []Recipe {
	if len(recipes) > max {
		return recipes[:max]
	}
	return recipes
}

func generateFilterData(rMap RecipeMap) FilterData {
	allRecipes := make([]Recipe, 0, len(rMap))
	for _, recipe := range rMap {
		allRecipes = append(allRecipes, recipe)
	}

	byCategory := make(map[string][]Recipe)
	for _, recipe := range allRecipes {
		byCategory[recipe.category] = append(byCategory[recipe.category], recipe)
	}

	randomByCategory := make(map[string][]Recipe)
	seed := time.Now().Unix() / secondsPerDay
	for category, recipes := range byCategory {
		categoryLower := strings.ToLower(category)
		if categoryLower != categoryDrinks && categoryLower != categoryReference {
			randomByCategory[category] = selectRandomRecipes(recipes, randomRecipesPerCategory, seed)
		}
	}

	notYet := filterRecipes(allRecipes, func(r Recipe) bool {
		return (r.imagePath == "None" && r.rating != 0) || (r.rating == 0 && excludesDrinksAndReference(r))
	})
	sortByCreatedDesc(notYet)

	recentlyAdded := filterRecipes(allRecipes, excludesDrinksAndReference)
	sortByCreatedDesc(recentlyAdded)
	recentlyAdded = limitRecipes(recentlyAdded, maxRecentlyAdded)

	leastUpdated := filterRecipes(allRecipes, excludesDrinksAndReference)
	sortByModifiedAsc(leastUpdated)
	leastUpdated = limitRecipes(leastUpdated, maxLeastUpdated)

	return FilterData{
		NotYet:           notYet,
		RandomByCategory: randomByCategory,
		RecentlyAdded:    recentlyAdded,
		LeastUpdated:     leastUpdated,
	}
}
