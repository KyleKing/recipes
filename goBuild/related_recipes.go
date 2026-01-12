package goBuild

import (
	"log"
	"os"
	"strings"

	"github.com/sivukhin/godjot/djot_parser"
)

func extractIngredientsFromDjot(ast []djot_parser.TreeNode[djot_parser.DjotNode]) []string {
	ingredients := []string{}
	currentSection := ""

	var extractListItemText func(djot_parser.TreeNode[djot_parser.DjotNode]) string
	extractListItemText = func(node djot_parser.TreeNode[djot_parser.DjotNode]) string {
		var textParts []string
		for _, child := range node.Children {
			if child.Type != djot_parser.UnorderedListNode && child.Type != djot_parser.TaskListNode && child.Type != djot_parser.OrderedListNode {
				text := strings.TrimSpace(string(child.FullText()))
				if text != "" {
					textParts = append(textParts, text)
				}
			}
		}
		return strings.Join(textParts, " ")
	}

	var extractListItems func(djot_parser.TreeNode[djot_parser.DjotNode], int) []string
	extractListItems = func(node djot_parser.TreeNode[djot_parser.DjotNode], level int) []string {
		var items []string
		for _, child := range node.Children {
			if child.Type == djot_parser.ListItemNode {
				text := extractListItemText(child)
				if text != "" {
					items = append(items, text)
				}
				for _, nestedChild := range child.Children {
					if nestedChild.Type == djot_parser.UnorderedListNode || nestedChild.Type == djot_parser.TaskListNode || nestedChild.Type == djot_parser.OrderedListNode {
						items = append(items, extractListItems(nestedChild, level+1)...)
					}
				}
			}
		}
		return items
	}

	var traverse func(djot_parser.TreeNode[djot_parser.DjotNode])
	traverse = func(node djot_parser.TreeNode[djot_parser.DjotNode]) {
		if node.Type == djot_parser.HeadingNode {
			levelStr := node.Attributes.Get(djot_parser.HeadingLevelKey)
			text := strings.TrimSpace(string(node.FullText()))

			if levelStr == "2" || levelStr == "##" {
				currentSection = text
			}
		}

		for _, child := range node.Children {
			traverse(child)
		}

		if node.Type == djot_parser.UnorderedListNode || node.Type == djot_parser.TaskListNode {
			if strings.EqualFold(currentSection, "Ingredients") {
				ingredients = extractListItems(node, 0)
			}
		}
	}

	for _, node := range ast {
		traverse(node)
	}

	return ingredients
}

func buildIngredientIndex(publicDir string, rMap RecipeMap) IngredientIndex {
	index := make(IngredientIndex)

	for path, recipe := range rMap {
		djPath := strings.Replace(path, ".html", ".dj", 1)
		djPath = strings.Replace(djPath, "public/", "content/", 1)

		text, err := os.ReadFile(djPath)
		if err != nil {
			log.Printf("Warning: Could not read %s: %v", djPath, err)
			continue
		}

		ast := djot_parser.BuildDjotAst(text)
		ingredients := extractIngredientsFromDjot(ast)

		tokens := extractIngredientsWithNLP(ingredients)

		index[path] = RecipeIngredients{
			filePath:    path,
			recipe:      recipe,
			title:       recipe.name,
			ingredients: ingredients,
			tokens:      tokens,
		}
	}

	return index
}

func calculateGlobalIDF(index IngredientIndex) map[string]float64 {
	return calculateIDF(index)
}

func enrichRecipesWithRelated(rMap RecipeMap, index IngredientIndex, idf map[string]float64) {
	for path, recipe := range rMap {
		if target, exists := index[path]; exists {
			related := findRelatedRecipes(target, index, idf, 3)
			recipe.relatedRecipes = related
			rMap[path] = recipe
		}
	}
}
