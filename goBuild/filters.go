package goBuild

import (
	"math/rand"
	"sort"
	"strings"
	"time"
)

func enrichRecipesWithMetadata(rMap RecipeMap, contentDir string) {
	for path, recipe := range rMap {
		djFilePath := strings.Replace(path, ".html", ".dj", 1)
		djFilePath = strings.Replace(djFilePath, "public/", contentDir+"/", 1)
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

func generateFilterData(rMap RecipeMap) FilterData {
	allRecipes := make([]Recipe, 0, len(rMap))
	for _, recipe := range rMap {
		allRecipes = append(allRecipes, recipe)
	}

	notYetMade := make([]Recipe, 0)
	byCategory := make(map[string][]Recipe)

	for _, recipe := range allRecipes {
		if strings.Contains(recipe.imagePath, "None") {
			notYetMade = append(notYetMade, recipe)
		}

		byCategory[recipe.category] = append(byCategory[recipe.category], recipe)
	}

	randomByCategory := make(map[string][]Recipe)
	seed := time.Now().Unix() / 86400
	for category, recipes := range byCategory {
		randomByCategory[category] = selectRandomRecipes(recipes, 3, seed)
	}

	recentlyAdded := make([]Recipe, len(allRecipes))
	copy(recentlyAdded, allRecipes)
	sort.Slice(recentlyAdded, func(i, j int) bool {
		if recentlyAdded[i].createdAt.IsZero() && !recentlyAdded[j].createdAt.IsZero() {
			return false
		}
		if !recentlyAdded[i].createdAt.IsZero() && recentlyAdded[j].createdAt.IsZero() {
			return true
		}
		return recentlyAdded[i].createdAt.After(recentlyAdded[j].createdAt)
	})
	if len(recentlyAdded) > 20 {
		recentlyAdded = recentlyAdded[:20]
	}

	leastUpdated := make([]Recipe, len(allRecipes))
	copy(leastUpdated, allRecipes)
	sort.Slice(leastUpdated, func(i, j int) bool {
		if leastUpdated[i].modifiedAt.IsZero() && !leastUpdated[j].modifiedAt.IsZero() {
			return false
		}
		if !leastUpdated[i].modifiedAt.IsZero() && leastUpdated[j].modifiedAt.IsZero() {
			return true
		}
		return leastUpdated[i].modifiedAt.Before(leastUpdated[j].modifiedAt)
	})
	if len(leastUpdated) > 20 {
		leastUpdated = leastUpdated[:20]
	}

	highRated := make([]Recipe, 0)
	for _, recipe := range allRecipes {
		if recipe.rating >= 4 && recipe.rating <= 5 {
			highRated = append(highRated, recipe)
		}
	}
	sort.Slice(highRated, func(i, j int) bool {
		if highRated[i].modifiedAt.IsZero() && !highRated[j].modifiedAt.IsZero() {
			return false
		}
		if !highRated[i].modifiedAt.IsZero() && highRated[j].modifiedAt.IsZero() {
			return true
		}
		return highRated[i].modifiedAt.Before(highRated[j].modifiedAt)
	})
	if len(highRated) > 20 {
		highRated = highRated[:20]
	}

	lowRated := make([]Recipe, 0)
	for _, recipe := range allRecipes {
		if recipe.rating >= 0 && recipe.rating <= 2 {
			lowRated = append(lowRated, recipe)
		}
	}
	sort.Slice(lowRated, func(i, j int) bool {
		if lowRated[i].createdAt.IsZero() && !lowRated[j].createdAt.IsZero() {
			return false
		}
		if !lowRated[i].createdAt.IsZero() && lowRated[j].createdAt.IsZero() {
			return true
		}
		return lowRated[i].createdAt.Before(lowRated[j].createdAt)
	})
	if len(lowRated) > 20 {
		lowRated = lowRated[:20]
	}

	return FilterData{
		NotYetMade:       notYetMade,
		RandomByCategory: randomByCategory,
		RecentlyAdded:    recentlyAdded,
		LeastUpdated:     leastUpdated,
		HighestRated:     highRated,
		LowestRated:      lowRated,
	}
}
