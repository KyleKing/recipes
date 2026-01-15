package goBuild

import (
	"sort"
	"strings"
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestMultiWordChunkNoIndividualTokens(t *testing.T) {
	tests := []struct {
		name          string
		ingredients   []string
		shouldContain []string
		shouldNotHave []string
	}{
		{
			name:          "olive oil should not extract individual words",
			ingredients:   []string{"2 Tbsp olive oil"},
			shouldContain: []string{"olive oil"},
			shouldNotHave: []string{"olive", "oil"},
		},
		{
			name:          "white beans should be lemmatized and not extract individual words",
			ingredients:   []string{"1 can white beans"},
			shouldContain: []string{"white bean"}, // Note: lemmatized to singular
			shouldNotHave: []string{"white", "beans", "bean"},
		},
		{
			name:          "single word ingredients are extracted normally",
			ingredients:   []string{"1 cup flour", "2 eggs"},
			shouldContain: []string{"flour", "egg"},
			shouldNotHave: []string{},
		},
		{
			name:          "black pepper should be kept as phrase",
			ingredients:   []string{"1/2 tsp black pepper"},
			shouldContain: []string{"black pepper"},
			shouldNotHave: []string{"black", "pepper"},
		},
		{
			name:          "mixed ingredients",
			ingredients:   []string{"2 Tbsp olive oil", "1 cup flour", "salt"},
			shouldContain: []string{"olive oil", "flour", "salt"},
			shouldNotHave: []string{"olive", "oil"},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			tokens := extractIngredientsWithNLP(tt.ingredients)

			for _, expected := range tt.shouldContain {
				assert.True(t, tokens[expected], "Expected token %q not found. Got: %v", expected, mapKeys(tokens))
			}

			for _, notExpected := range tt.shouldNotHave {
				assert.False(t, tokens[notExpected], "Token %q should not be present. Got: %v", notExpected, mapKeys(tokens))
			}
		})
	}
}

func mapKeys(m map[string]bool) []string {
	keys := make([]string, 0, len(m))
	for k := range m {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	return keys
}

type TestRecipe struct {
	name        string
	ingredients []string
}

func TestEvaluateRelatedRecipeMatching(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping evaluation test in short mode")
	}

	recipes := []TestRecipe{
		{
			name:        "Garlic Bread",
			ingredients: []string{"2-4 Garlic Cloves", "2-4 Tbsp butter", "2 Tbsp Extra-virgin Olive Oil", "1/2 tsp kosher salt", "Bread Loaf", "3 Tbsp Cheese, grated"},
		},
		{
			name:        "Bruschetta",
			ingredients: []string{"2 Roma Tomatoes", "1/2 tsp Black Pepper", "1/2 tsp Basil", "1/2 tsp Garlic Powder", "1/2 tsp Oregano", "1 tsp olive oil"},
		},
		{
			name:        "Pasta with Olive Oil",
			ingredients: []string{"1 lb pasta", "3 Tbsp olive oil", "4 garlic cloves", "red pepper flakes", "parmesan cheese"},
		},
		{
			name:        "Chicken Stir Fry",
			ingredients: []string{"1 lb chicken breast", "2 Tbsp soy sauce", "1 Tbsp sesame oil", "2 cups broccoli", "1 bell pepper"},
		},
		{
			name:        "Vegetable Stir Fry",
			ingredients: []string{"2 Tbsp soy sauce", "1 Tbsp sesame oil", "2 cups broccoli", "1 bell pepper", "1 cup snap peas"},
		},
		{
			name:        "Garlic Chicken",
			ingredients: []string{"4 chicken thighs", "6 garlic cloves", "2 Tbsp olive oil", "1 tsp thyme", "salt and pepper"},
		},
		{
			name:        "Black Bean Tacos",
			ingredients: []string{"1 can black beans", "corn tortillas", "1 avocado", "lime juice", "cilantro"},
		},
		{
			name:        "Bean and Rice Bowl",
			ingredients: []string{"1 can black beans", "2 cups rice", "1 avocado", "salsa", "sour cream"},
		},
	}

	index := buildTestIndex(recipes)
	idf := calculateIDF(index)

	t.Log("=== EXTRACTED TOKENS ===")
	for _, recipe := range recipes {
		path := recipe.name
		if ri, ok := index[path]; ok {
			t.Logf("\n%s:", recipe.name)
			t.Logf("  Ingredients: %v", recipe.ingredients)
			t.Logf("  Tokens: %v", mapKeys(ri.tokens))
		}
	}

	t.Log("\n=== IDF VALUES (higher = more distinctive) ===")
	idfPairs := make([]struct {
		token string
		idf   float64
	}, 0, len(idf))
	for token, val := range idf {
		idfPairs = append(idfPairs, struct {
			token string
			idf   float64
		}{token, val})
	}
	sort.Slice(idfPairs, func(i, j int) bool {
		return idfPairs[i].idf > idfPairs[j].idf
	})
	for _, p := range idfPairs {
		t.Logf("  %s: %.3f", p.token, p.idf)
	}

	t.Log("\n=== RELATED RECIPE MATCHES ===")
	for _, recipe := range recipes {
		path := recipe.name
		target, ok := index[path]
		if !ok {
			continue
		}

		related := findRelatedRecipes(target, index, idf, 4)
		t.Logf("\n%s:", recipe.name)
		if len(related) == 0 {
			t.Log("  No matches above threshold")
		}
		for _, r := range related {
			t.Logf("  -> %s (score: %.3f, ing: %.3f, title: %.3f)",
				r.recipe.name, r.similarityScore, r.ingredientScore, r.titleScore)
			t.Logf("     Shared ingredients: %v", r.sharedIngredients)
			t.Logf("     Shared title words: %v", r.sharedTitleWords)
		}
	}
}

func buildTestIndex(recipes []TestRecipe) IngredientIndex {
	index := make(IngredientIndex)

	for _, recipe := range recipes {
		tokens := extractIngredientsWithNLP(recipe.ingredients)
		index[recipe.name] = RecipeIngredients{
			filePath:    recipe.name,
			recipe:      Recipe{name: recipe.name, url: "/" + strings.ToLower(strings.ReplaceAll(recipe.name, " ", "_"))},
			title:       recipe.name,
			ingredients: recipe.ingredients,
			tokens:      tokens,
		}
	}

	return index
}

func TestScenarioCompareOldVsNewChunking(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping comparison test in short mode")
	}

	ingredients := []string{
		"2 Tbsp olive oil",
		"1 can white beans",
		"3 garlic cloves",
		"1/2 cup parmesan cheese",
		"fresh basil leaves",
	}

	tokensNew := extractIngredientsWithNLP(ingredients)

	t.Log("=== NEW CHUNKING (with fix) ===")
	t.Logf("Tokens: %v", mapKeys(tokensNew))

	expectedPhrases := []string{"olive oil", "white beans", "parmesan cheese"}
	notExpectedWords := []string{"olive", "oil", "white", "bean"}

	for _, phrase := range expectedPhrases {
		if tokensNew[phrase] {
			t.Logf("OK: %q found as phrase", phrase)
		} else {
			t.Logf("MISSING: %q not found", phrase)
		}
	}

	for _, word := range notExpectedWords {
		if tokensNew[word] {
			t.Logf("ISSUE: %q found as individual token (should be part of phrase)", word)
		} else {
			t.Logf("OK: %q correctly not extracted individually", word)
		}
	}
}

func TestPrintAllTokensForRealIngredients(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping real ingredient test in short mode")
	}

	realRecipes := map[string][]string{
		"Garlic Bread": {
			"~2-4 Garlic Cloves, grated or very finely diced to a paste",
			"~2-4 Tbsp butter",
			"~2 Tbsp Extra-virgin Olive Oil",
			"1/2 tsp kosher salt",
			"Bread Loaf",
			"~3 Tbsp Cheese, grated",
		},
		"Bruschetta": {
			"2 Roma Tomatoes",
			"1/2 tsp Black Pepper",
			"1/2 tsp Basil",
			"1/2 tsp Garlic Powder",
			"1/2 tsp Oregano",
			"1 tsp olive oil",
		},
		"Chicken Cacciatore": {
			"1.5 lbs chicken thighs, bone in",
			"1 Tbsp olive oil",
			"1 large onion, diced",
			"4 garlic cloves, minced",
			"1 red bell pepper, sliced",
			"28 oz crushed tomatoes",
			"1/2 cup chicken broth",
			"1/4 cup dry white wine",
			"2 tsp Italian seasoning",
			"Salt and pepper to taste",
		},
	}

	t.Log("=== TOKEN EXTRACTION FOR REAL RECIPES ===")
	for name, ingredients := range realRecipes {
		tokens := extractIngredientsWithNLP(ingredients)
		t.Logf("\n%s:", name)
		t.Logf("  Raw ingredients:")
		for _, ing := range ingredients {
			t.Logf("    - %s", ing)
		}
		t.Logf("  Extracted tokens: %v", mapKeys(tokens))
		t.Logf("  Token count: %d", len(tokens))
	}
}

func TestIngredientExtractionSamples(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping NLP test in short mode")
	}

	testCases := []struct {
		input    string
		expected []string
	}{
		{"2 Tbsp olive oil", []string{"olive oil"}},
		{"2 Tbsp Extra-virgin Olive Oil", []string{"olive oil"}},
		{"1 can white beans", []string{"white bean"}}, // lemmatized
		{"3 garlic cloves, minced", []string{"garlic"}},
		{"1/2 tsp Garlic Powder", []string{"garlic", "garlic powder"}},
		{"1 avocado", []string{"avocado"}},
		{"lime juice", []string{"lime", "lime juice"}},
		{"red pepper flakes", []string{"red pepper flake"}},        // lemmatized, no separate "red pepper"
		{"4 chicken thighs", []string{"chicken", "chicken thigh"}}, // lemmatized, chicken extracted from compound
	}

	for _, tc := range testCases {
		t.Run(tc.input, func(t *testing.T) {
			tokens := extractIngredientsWithNLP([]string{tc.input})
			for _, exp := range tc.expected {
				assert.True(t, tokens[exp], "Expected %q in tokens for %q, got %v", exp, tc.input, mapKeys(tokens))
			}
		})
	}
}
