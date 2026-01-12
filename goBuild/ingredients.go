package goBuild

import (
	"math"
	"sort"
	"strings"
)

// Temporarily disabled - go-spacy requires C++ wrapper build
// TODO: Re-enable NLP extraction once go-spacy is properly configured
// import "github.com/am-sokolov/go-spacy"

func extractIngredientsWithNLP(rawIngredients []string) map[string]bool {
	// Using fallback extraction (Spacy NLP disabled for now)
	return extractIngredientsFallback(rawIngredients)
}

func extractIngredientsFallback(rawIngredients []string) map[string]bool {
	tokens := make(map[string]bool)
	stopWords := map[string]bool{
		"cup": true, "cups": true, "tbsp": true, "tsp": true, "oz": true, "lb": true,
		"can": true, "cans": true, "clove": true, "cloves": true,
		"chopped": true, "diced": true, "minced": true, "sliced": true, "grated": true,
		"large": true, "small": true, "medium": true, "fresh": true, "dried": true,
		"the": true, "a": true, "an": true, "of": true, "and": true,
	}

	for _, ingredient := range rawIngredients {
		lower := strings.ToLower(ingredient)
		words := strings.FieldsFunc(lower, func(r rune) bool {
			return r == ' ' || r == ',' || r == '(' || r == ')' || r == '/'
		})

		for _, word := range words {
			if !stopWords[word] && len(word) >= 3 && !isNumeric(word) {
				tokens[word] = true
			}
		}
	}

	return tokens
}

func isNumeric(s string) bool {
	for _, r := range s {
		if (r < '0' || r > '9') && r != '.' && r != '-' {
			return false
		}
	}
	return len(s) > 0
}

func calculateIDF(index IngredientIndex) map[string]float64 {
	idf := make(map[string]float64)
	df := make(map[string]int)
	n := float64(len(index))

	for _, recipeIng := range index {
		for token := range recipeIng.tokens {
			df[token]++
		}
	}

	for token, docFreq := range df {
		idf[token] = math.Log(n / float64(docFreq))
	}

	return idf
}

func calculateIngredientSimilarity(a, b RecipeIngredients, idf map[string]float64) float64 {
	var dotProduct float64
	var magnitudeA float64
	var magnitudeB float64

	for token := range a.tokens {
		weight := idf[token]
		magnitudeA += weight * weight
	}

	for token := range b.tokens {
		weight := idf[token]
		magnitudeB += weight * weight
	}

	for token := range a.tokens {
		if b.tokens[token] {
			weight := idf[token]
			dotProduct += weight * weight
		}
	}

	if magnitudeA == 0 || magnitudeB == 0 {
		return 0.0
	}

	return dotProduct / (math.Sqrt(magnitudeA) * math.Sqrt(magnitudeB))
}

func calculateTitleSimilarity(titleA, titleB string) float64 {
	tokensA := extractTitleTokens(titleA)
	tokensB := extractTitleTokens(titleB)

	if len(tokensA) == 0 || len(tokensB) == 0 {
		return 0.0
	}

	intersection := 0
	for token := range tokensA {
		if tokensB[token] {
			intersection++
		}
	}

	union := len(tokensA) + len(tokensB) - intersection
	if union == 0 {
		return 0.0
	}

	return float64(intersection) / float64(union)
}

func extractTitleTokens(title string) map[string]bool {
	stopWords := map[string]bool{
		"the": true, "a": true, "an": true, "and": true, "or": true, "with": true,
		"in": true, "on": true, "for": true, "to": true, "of": true,
	}

	tokens := make(map[string]bool)
	lower := strings.ToLower(title)
	words := strings.Fields(lower)

	for _, word := range words {
		cleaned := strings.Trim(word, ".,!?;:")
		if !stopWords[cleaned] && len(cleaned) >= 3 {
			tokens[cleaned] = true
		}
	}

	return tokens
}

func calculateCombinedSimilarity(a, b RecipeIngredients, idf map[string]float64) float64 {
	ingredientSim := calculateIngredientSimilarity(a, b, idf)
	titleSim := calculateTitleSimilarity(a.title, b.title)

	return 0.7*ingredientSim + 0.3*titleSim
}

func findRelatedRecipes(target RecipeIngredients, allRecipes IngredientIndex, idf map[string]float64, maxResults int) []RelatedRecipe {
	scores := []RelatedRecipe{}

	for filePath, candidate := range allRecipes {
		if filePath == target.filePath {
			continue
		}

		score := calculateCombinedSimilarity(target, candidate, idf)

		if score > 0.15 {
			scores = append(scores, RelatedRecipe{
				recipe:          candidate.recipe,
				similarityScore: score,
			})
		}
	}

	sort.Slice(scores, func(i, j int) bool {
		return scores[i].similarityScore > scores[j].similarityScore
	})

	if len(scores) > maxResults {
		scores = scores[:maxResults]
	}

	return scores
}
