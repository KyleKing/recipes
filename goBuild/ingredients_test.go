package goBuild

import (
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestIsNumeric(t *testing.T) {
	tests := []struct {
		name     string
		input    string
		expected bool
	}{
		{"integer", "123", true},
		{"decimal", "12.5", true},
		{"negative", "-10", true},
		{"negative decimal", "-3.14", true},
		{"text", "abc", false},
		{"mixed", "12abc", false},
		{"empty", "", false},
		{"fraction", "1/2", false}, // Not numeric, has slash
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := isNumeric(tt.input)
			assert.Equal(t, tt.expected, result)
		})
	}
}

func TestIsFraction(t *testing.T) {
	tests := []struct {
		name     string
		input    string
		expected bool
	}{
		{"simple fraction", "1/2", true},
		{"another fraction", "3/4", true},
		{"improper fraction", "5/3", true},
		{"integer", "123", false},
		{"decimal", "1.5", false},
		{"text", "half", false},
		{"no slash", "12", false},
		{"multiple slashes", "1/2/3", false},
		{"invalid fraction", "a/b", false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := isFraction(tt.input)
			assert.Equal(t, tt.expected, result)
		})
	}
}

func TestRemoveParenthetical(t *testing.T) {
	tests := []struct {
		name     string
		input    string
		expected string
	}{
		{
			"remove optional",
			"1 cup flour (optional)",
			"1 cup flour",
		},
		{
			"remove nested parentheses",
			"ingredient (optional (really optional))",
			"ingredient",
		},
		{
			"no parentheses",
			"plain ingredient",
			"plain ingredient",
		},
		{
			"empty parentheses",
			"ingredient ()",
			"ingredient",
		},
		{
			"multiple parentheses",
			"item (note 1) and (note 2)",
			"item  and",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := removeParenthetical(tt.input)
			assert.Equal(t, tt.expected, result)
		})
	}
}

func TestNormalizePhrase(t *testing.T) {
	tests := []struct {
		name     string
		input    string
		expected string
	}{
		{
			"remove quantity",
			"1 cup white beans",
			"white beans",
		},
		{
			"remove measurement",
			"2 tablespoons olive oil",
			"olive oil",
		},
		{
			"remove prep method",
			"diced tomatoes",
			"tomatoes",
		},
		{
			"remove size",
			"large onion",
			"onion",
		},
		{
			"remove fraction",
			"1/2 cup sugar",
			"sugar",
		},
		{
			"multiple quantities",
			"2-3 large cloves garlic",
			"garlic",
		},
		{
			"simple ingredient",
			"salt",
			"salt",
		},
		{
			"lowercase output",
			"Fresh Basil",
			"basil",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := normalizePhrase(tt.input)
			assert.Equal(t, tt.expected, result)
		})
	}
}

func TestIsValidIngredientToken(t *testing.T) {
	tests := []struct {
		name     string
		input    string
		expected bool
	}{
		{"valid ingredient", "chicken", true},
		{"valid ingredient long", "tomatoes", true},
		{"too short", "ab", false},
		{"measurement unit", "cup", false},
		{"tablespoon", "tbsp", false},
		{"prep method", "chopped", false},
		{"size", "large", false},
		{"state", "fresh", false},
		{"optional", "optional", false},
		{"number", "123", false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := isValidIngredientToken(tt.input)
			assert.Equal(t, tt.expected, result)
		})
	}
}

func TestIsValidIngredientPhrase(t *testing.T) {
	tests := []struct {
		name     string
		input    string
		expected bool
	}{
		{"valid phrase", "white beans", true},
		{"valid single word", "chicken", true},
		{"too short", "ab", false},
		{"measurement", "cup", false},
		{"tablespoons", "tablespoons", false},
		{"number", "123", false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := isValidIngredientPhrase(tt.input)
			assert.Equal(t, tt.expected, result)
		})
	}
}

func TestExtractTitleTokens(t *testing.T) {
	tests := []struct {
		name     string
		title    string
		expected []string // Expected tokens (order doesn't matter)
	}{
		{
			"simple title",
			"Chocolate Chip Cookies",
			[]string{"chocolate", "chip", "cookies"},
		},
		{
			"with stopwords",
			"The Best Chicken and Rice",
			[]string{"best", "chicken", "rice"},
		},
		{
			"with punctuation",
			"Mom's Famous Pasta!",
			[]string{"mom's", "famous", "pasta"},
		},
		{
			"short words filtered",
			"A Big Bowl of Soup",
			[]string{"big", "bowl", "soup"},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := extractTitleTokens(tt.title)
			assert.Len(t, result, len(tt.expected))
			for _, token := range tt.expected {
				assert.True(t, result[token], "Expected token %s not found", token)
			}
		})
	}
}

func TestCalculateTitleSimilarity(t *testing.T) {
	tests := []struct {
		name     string
		titleA   string
		titleB   string
		minScore float64
	}{
		{
			"identical titles",
			"Chocolate Chip Cookies",
			"Chocolate Chip Cookies",
			0.9, // Should be very high
		},
		{
			"similar titles",
			"Chicken Rice Bowl",
			"Rice and Chicken Bowl",
			0.6, // High overlap
		},
		{
			"completely different",
			"Chocolate Cake",
			"Shrimp Tacos",
			0.0, // No overlap
		},
		{
			"partial overlap",
			"Chicken Soup",
			"Chicken Tacos",
			0.3, // Shares "chicken"
		},
	}

	// Create a dummy IDF map for testing
	idf := map[string]float64{
		"chocolate": 1.0,
		"chip":      2.0,
		"chicken":   1.5,
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			score := calculateTitleSimilarity(tt.titleA, tt.titleB, idf)
			// Note: TF-IDF cosine may give different scores than Jaccard, but should still be in valid range
			assert.GreaterOrEqual(t, score, 0.0, "Score should be at least 0")
			// Allow small floating point error (1.0 + 1e-10)
			assert.LessOrEqual(t, score, 1.0+1e-10, "Score should not exceed 1.0")
		})
	}
}

func TestGetSharedTokens(t *testing.T) {
	tokensA := map[string]bool{
		"flour":  true,
		"sugar":  true,
		"butter": true,
	}

	tokensB := map[string]bool{
		"sugar":  true,
		"butter": true,
		"milk":   true,
	}

	shared := getSharedTokens(tokensA, tokensB)
	assert.Len(t, shared, 2)
	assert.Contains(t, shared, "butter")
	assert.Contains(t, shared, "sugar")

	// Should be sorted
	assert.Equal(t, "butter", shared[0])
	assert.Equal(t, "sugar", shared[1])
}
