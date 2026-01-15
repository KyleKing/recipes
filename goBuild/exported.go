package goBuild

import (
	"strings"

	"github.com/am-sokolov/go-spacy"
	"github.com/sivukhin/godjot/djot_parser"
)

// Exported functions for use by cmd/recipe_debug and other tools

// GetNLP returns the NLP instance
func GetNLP() *spacy.NLP {
	return getNLP()
}

// ExtractIngredientsFromDjot extracts ingredient strings from Djot AST
func ExtractIngredientsFromDjot(ast []djot_parser.TreeNode[djot_parser.DjotNode]) []string {
	return extractIngredientsFromDjot(ast)
}

// ExtractIngredientsWithNLP extracts ingredient tokens using NLP
func ExtractIngredientsWithNLP(rawIngredients []string) map[string]bool {
	return extractIngredientsWithNLP(rawIngredients)
}

// ExtractTitleTokens extracts tokens from a recipe title
func ExtractTitleTokens(title string) map[string]bool {
	return extractTitleTokens(title)
}

// CalculateIDF calculates inverse document frequency for all tokens
func CalculateIDF(index IngredientIndex) map[string]float64 {
	return calculateIDF(index)
}

// CalculateIngredientSimilarity calculates TF-IDF weighted cosine similarity for ingredients
func CalculateIngredientSimilarity(a, b RecipeIngredients, idf map[string]float64) float64 {
	return calculateIngredientSimilarity(a, b, idf)
}

// CalculateTitleSimilarity calculates TF-IDF weighted cosine similarity for titles
func CalculateTitleSimilarity(titleA, titleB string, idf map[string]float64) float64 {
	return calculateTitleSimilarity(titleA, titleB, idf)
}

// NewRecipeIngredients creates a RecipeIngredients struct (exported constructor)
func NewRecipeIngredients(filePath, title string, ingredients []string, tokens map[string]bool) RecipeIngredients {
	return RecipeIngredients{
		filePath:    filePath,
		recipe:      Recipe{name: title},
		title:       title,
		ingredients: ingredients,
		tokens:      tokens,
	}
}

// ExtractTitleFromDjot extracts the title (level 1 heading) from Djot AST
func ExtractTitleFromDjot(ast []djot_parser.TreeNode[djot_parser.DjotNode]) string {
	title := ""

	var traverse func(djot_parser.TreeNode[djot_parser.DjotNode])
	traverse = func(node djot_parser.TreeNode[djot_parser.DjotNode]) {
		if node.Type == djot_parser.HeadingNode {
			levelStr := node.Attributes.Get(djot_parser.HeadingLevelKey)
			text := strings.TrimSpace(string(node.FullText()))

			if (levelStr == "1" || levelStr == "#") && title == "" {
				title = text
			}
		}

		for _, child := range node.Children {
			traverse(child)
		}
	}

	for _, node := range ast {
		traverse(node)
		if title != "" {
			break
		}
	}

	return title
}
