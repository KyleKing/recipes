package goBuild

import (
	"log"
	"math"
	"sort"
	"strings"
	"sync"

	"github.com/am-sokolov/go-spacy"
)

var (
	nlp     *spacy.NLP
	nlpOnce sync.Once
)

func getNLP() *spacy.NLP {
	nlpOnce.Do(func() {
		var err error
		nlp, err = spacy.NewNLP("en_core_web_sm")
		if err != nil {
			log.Fatalf("Failed to initialize spaCy NLP: %v", err)
		}
	})
	return nlp
}

func extractIngredientsWithNLP(rawIngredients []string) map[string]bool {
	nlp := getNLP()
	phrases := make(map[string]bool)

	for _, ingredient := range rawIngredients {
		// Preprocess: remove parenthetical content
		cleaned := removeParenthetical(ingredient)

		// Extract noun chunks (handles multi-word phrases like "white beans")
		chunks := nlp.GetNounChunks(cleaned)
		for _, chunk := range chunks {
			normalized := normalizePhrase(chunk.Text)
			if isValidIngredientPhrase(normalized) {
				phrases[normalized] = true
			}
		}

		// Also extract individual nouns for broader matching
		tokens := nlp.Tokenize(cleaned)
		for _, token := range tokens {
			if (token.POS == "NOUN" || token.POS == "PROPN") && !token.IsStop {
				lemma := strings.ToLower(token.Lemma)
				if isValidIngredientToken(lemma) {
					phrases[lemma] = true
				}
			}
		}
	}

	return phrases
}

func removeParenthetical(s string) string {
	// Remove content within parentheses
	result := ""
	parenDepth := 0
	for _, r := range s {
		if r == '(' {
			parenDepth++
			continue
		}
		if r == ')' {
			parenDepth--
			continue
		}
		if parenDepth == 0 {
			result += string(r)
		}
	}
	return strings.TrimSpace(result)
}

func normalizePhrase(phrase string) string {
	cleaned := strings.TrimSpace(phrase)
	cleaned = strings.ToLower(cleaned)

	// Split on spaces to process word by word
	words := strings.Fields(cleaned)
	if len(words) == 0 {
		return ""
	}

	// Remove leading numbers, fractions, and quantity words
	quantityPrefixes := map[string]bool{
		"cup": true, "cups": true, "tbsp": true, "tsp": true,
		"tablespoon": true, "tablespoons": true, "teaspoon": true, "teaspoons": true,
		"ounce": true, "ounces": true, "oz": true, "pound": true, "pounds": true, "lb": true,
		"can": true, "cans": true, "jar": true, "jars": true,
		"clove": true, "cloves": true, "piece": true, "pieces": true,
		"slice": true, "slices": true, "pinch": true, "dash": true,
		"large": true, "medium": true, "small": true,
		"whole": true, "half": true, "halves": true,
		"chopped": true, "diced": true, "minced": true, "sliced": true,
		"grated": true, "shredded": true, "fresh": true, "dried": true,
		"ground": true, "crushed": true, "cooked": true,
	}

	// Strip leading words that are quantities, measurements, or preparation methods
	resultWords := []string{}
	skipLeading := true
	for _, word := range words {
		// Remove fractions and numbers
		if isNumeric(word) || isFraction(word) {
			continue
		}
		// Skip leading quantity/measurement/prep words
		if skipLeading && quantityPrefixes[word] {
			continue
		}
		skipLeading = false
		resultWords = append(resultWords, word)
	}

	return strings.Join(resultWords, " ")
}

func isFraction(s string) bool {
	// Check if string is a fraction like "1/2", "1/4", etc.
	parts := strings.Split(s, "/")
	if len(parts) != 2 {
		return false
	}
	return isNumeric(parts[0]) && isNumeric(parts[1])
}

func isValidIngredientPhrase(phrase string) bool {
	if len(phrase) < 3 {
		return false
	}

	// Skip pure measurement units
	measurementUnits := map[string]bool{
		"cup": true, "cups": true, "tbsp": true, "tsp": true,
		"tablespoon": true, "tablespoons": true, "teaspoon": true, "teaspoons": true,
		"oz": true, "ounce": true, "ounces": true, "lb": true, "pound": true, "pounds": true,
		"can": true, "cans": true, "jar": true, "jars": true,
		"piece": true, "pieces": true, "slice": true, "slices": true,
	}

	return !measurementUnits[phrase] && !isNumeric(phrase)
}

func isValidIngredientToken(token string) bool {
	if len(token) < 3 {
		return false
	}

	// Skip measurement units, preparation methods, sizes, and common non-ingredient words
	skipWords := map[string]bool{
		// Measurements
		"cup": true, "tbsp": true, "tsp": true, "tablespoon": true, "teaspoon": true,
		"ounce": true, "pound": true, "can": true, "jar": true, "oz": true, "lb": true,
		"clove": true, "piece": true, "slice": true, "pinch": true, "dash": true,
		// Preparation methods
		"chopped": true, "diced": true, "minced": true, "sliced": true,
		"grated": true, "shredded": true, "crushed": true,
		// Sizes and states
		"large": true, "medium": true, "small": true,
		"fresh": true, "dried": true, "cooked": true,
		"whole": true, "half": true,
		// Generic words
		"optional": true, "taste": true, "color": true,
		"each": true, "serving": true,
	}

	return !skipWords[token] && !isNumeric(token)
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

func getSharedTokens(a, b map[string]bool) []string {
	shared := []string{}
	for token := range a {
		if b[token] {
			shared = append(shared, token)
		}
	}
	sort.Strings(shared)
	return shared
}

func findRelatedRecipes(target RecipeIngredients, allRecipes IngredientIndex, idf map[string]float64, maxResults int) []RelatedRecipe {
	scores := []RelatedRecipe{}

	for filePath, candidate := range allRecipes {
		if filePath == target.filePath {
			continue
		}

		ingredientScore := calculateIngredientSimilarity(target, candidate, idf)
		titleScore := calculateTitleSimilarity(target.title, candidate.title)
		combinedScore := 0.7*ingredientScore + 0.3*titleScore

		if combinedScore > 0.15 {
			sharedIngredients := getSharedTokens(target.tokens, candidate.tokens)
			sharedTitleWords := getSharedTokens(
				extractTitleTokens(target.title),
				extractTitleTokens(candidate.title),
			)

			scores = append(scores, RelatedRecipe{
				recipe:            candidate.recipe,
				similarityScore:   combinedScore,
				sharedIngredients: sharedIngredients,
				sharedTitleWords:  sharedTitleWords,
				ingredientScore:   ingredientScore,
				titleScore:        titleScore,
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
