package main

import (
	"flag"
	"fmt"
	"os"
	"sort"

	"github.com/KyleKing/recipes/goBuild"
	"github.com/sivukhin/godjot/djot_parser"
)

func main() {
	// Define subcommands
	inspectCmd := flag.NewFlagSet("inspect", flag.ExitOnError)
	compareCmd := flag.NewFlagSet("compare", flag.ExitOnError)

	if len(os.Args) < 2 {
		printUsage()
		os.Exit(1)
	}

	switch os.Args[1] {
	case "inspect":
		inspectRecipe(inspectCmd, os.Args[2:])
	case "compare":
		compareRecipes(compareCmd, os.Args[2:])
	default:
		printUsage()
		os.Exit(1)
	}
}

func printUsage() {
	fmt.Println("Recipe Debugging Utility")
	fmt.Println("\nUsage:")
	fmt.Println("  recipe_debug inspect <recipe_file.dj>")
	fmt.Println("    Inspect ingredient extraction and token chunks for a recipe")
	fmt.Println("\n  recipe_debug compare <recipe1.dj> <recipe2.dj> [recipe3.dj...]")
	fmt.Println("    Compare two or more recipes and show similarity scores")
	fmt.Println("\nExamples:")
	fmt.Println("  recipe_debug inspect content/dessert/oatmeal_balls.dj")
	fmt.Println("  recipe_debug compare content/dessert/oatmeal_balls.dj content/dessert-ish/chocolate_date_energy_balls.dj")
}

func inspectRecipe(fs *flag.FlagSet, args []string) {
	if len(args) < 1 {
		fmt.Println("Error: Please provide a recipe file path")
		fmt.Println("Usage: recipe_debug inspect <recipe_file.dj>")
		os.Exit(1)
	}

	recipePath := args[0]

	// Read recipe file
	content, err := os.ReadFile(recipePath)
	if err != nil {
		fmt.Printf("Error reading file: %v\n", err)
		os.Exit(1)
	}

	// Parse recipe
	ast := djot_parser.BuildDjotAst(content)

	// Extract title
	title := goBuild.ExtractTitleFromDjot(ast)

	// Extract ingredients
	ingredients := goBuild.ExtractIngredientsFromDjot(ast)

	// Get NLP tokens
	tokens := goBuild.ExtractIngredientsWithNLP(ingredients)

	// Get NLP instance for detailed analysis
	nlp := goBuild.GetNLP()

	fmt.Printf("\n========================================\n")
	fmt.Printf("Recipe: %s\n", title)
	fmt.Printf("File: %s\n", recipePath)
	fmt.Printf("========================================\n\n")

	fmt.Printf("=== RAW INGREDIENTS ===\n")
	for i, ing := range ingredients {
		fmt.Printf("%d. %s\n", i+1, ing)
	}

	fmt.Printf("\n=== EXTRACTED TOKENS ===\n")
	tokenList := make([]string, 0, len(tokens))
	for token := range tokens {
		tokenList = append(tokenList, token)
	}
	sort.Strings(tokenList)
	for _, token := range tokenList {
		fmt.Printf("  - %s\n", token)
	}
	fmt.Printf("Total: %d tokens\n", len(tokens))

	fmt.Printf("\n=== DETAILED NLP ANALYSIS ===\n")
	for i, ing := range ingredients {
		fmt.Printf("\n[%d] %s\n", i+1, ing)

		// Tokenize
		nlpTokens := nlp.Tokenize(ing)
		fmt.Println("  Tokens:")
		for _, tok := range nlpTokens {
			fmt.Printf("    %q: POS=%s, Dep=%s, Lemma=%s\n",
				tok.Text, tok.POS, tok.Dep, tok.Lemma)
		}

		// Noun chunks
		chunks := nlp.GetNounChunks(ing)
		fmt.Printf("  Noun chunks (%d):\n", len(chunks))
		for _, chunk := range chunks {
			fmt.Printf("    %q (root: %q)\n", chunk.Text, chunk.RootText)
		}
	}

	fmt.Printf("\n=== TITLE TOKENS ===\n")
	titleTokens := goBuild.ExtractTitleTokens(title)
	titleList := make([]string, 0, len(titleTokens))
	for token := range titleTokens {
		titleList = append(titleList, token)
	}
	sort.Strings(titleList)
	for _, token := range titleList {
		fmt.Printf("  - %s\n", token)
	}
}

func compareRecipes(fs *flag.FlagSet, args []string) {
	if len(args) < 2 {
		fmt.Println("Error: Please provide at least two recipe file paths")
		fmt.Println("Usage: recipe_debug compare <recipe1.dj> <recipe2.dj> [recipe3.dj...]")
		os.Exit(1)
	}

	// Load all recipes
	type RecipeData struct {
		path        string
		title       string
		ingredients []string
		tokens      map[string]bool
		titleTokens map[string]bool
	}

	recipes := make([]RecipeData, 0, len(args))

	for _, recipePath := range args {
		content, err := os.ReadFile(recipePath)
		if err != nil {
			fmt.Printf("Error reading %s: %v\n", recipePath, err)
			continue
		}

		ast := djot_parser.BuildDjotAst(content)

		title := goBuild.ExtractTitleFromDjot(ast)

		ingredients := goBuild.ExtractIngredientsFromDjot(ast)
		tokens := goBuild.ExtractIngredientsWithNLP(ingredients)
		titleTokens := goBuild.ExtractTitleTokens(title)

		recipes = append(recipes, RecipeData{
			path:        recipePath,
			title:       title,
			ingredients: ingredients,
			tokens:      tokens,
			titleTokens: titleTokens,
		})
	}

	// Build a minimal index for IDF calculation
	index := make(map[string]goBuild.RecipeIngredients)
	for _, recipe := range recipes {
		index[recipe.path] = goBuild.NewRecipeIngredients(
			recipe.path,
			recipe.title,
			recipe.ingredients,
			recipe.tokens,
		)
	}

	idf := goBuild.CalculateIDF(index)

	fmt.Printf("\n========================================\n")
	fmt.Printf("Comparing %d Recipes\n", len(recipes))
	fmt.Printf("========================================\n\n")

	// Print recipe summaries
	for i, recipe := range recipes {
		fmt.Printf("[%d] %s\n", i+1, recipe.title)
		fmt.Printf("    Path: %s\n", recipe.path)
		fmt.Printf("    Ingredient tokens: %d\n", len(recipe.tokens))
		fmt.Printf("    Title tokens: %d\n", len(recipe.titleTokens))
	}

	// Compare all pairs
	fmt.Printf("\n=== PAIRWISE COMPARISONS ===\n")
	for i := 0; i < len(recipes); i++ {
		for j := i + 1; j < len(recipes); j++ {
			recipeA := recipes[i]
			recipeB := recipes[j]

			fmt.Printf("\n----------------------------------------\n")
			fmt.Printf("[%d] %s\n", i+1, recipeA.title)
			fmt.Printf("  vs\n")
			fmt.Printf("[%d] %s\n", j+1, recipeB.title)
			fmt.Printf("----------------------------------------\n")

			// Shared ingredient tokens
			sharedIngTokens := []string{}
			for token := range recipeA.tokens {
				if recipeB.tokens[token] {
					sharedIngTokens = append(sharedIngTokens, token)
				}
			}
			sort.Strings(sharedIngTokens)

			// Shared title tokens
			sharedTitleTokens := []string{}
			for token := range recipeA.titleTokens {
				if recipeB.titleTokens[token] {
					sharedTitleTokens = append(sharedTitleTokens, token)
				}
			}
			sort.Strings(sharedTitleTokens)

			// Calculate similarities
			ingA := index[recipeA.path]
			ingB := index[recipeB.path]

			ingredientSim := goBuild.CalculateIngredientSimilarity(ingA, ingB, idf)
			titleSim := goBuild.CalculateTitleSimilarity(recipeA.title, recipeB.title, idf)
			combinedSim := 0.7*ingredientSim + 0.3*titleSim

			fmt.Printf("\nShared ingredient tokens (%d): %v\n", len(sharedIngTokens), sharedIngTokens)
			fmt.Printf("Shared title tokens (%d): %v\n", len(sharedTitleTokens), sharedTitleTokens)
			fmt.Printf("\nSimilarity scores:\n")
			fmt.Printf("  Ingredient: %.4f\n", ingredientSim)
			fmt.Printf("  Title:      %.4f\n", titleSim)
			fmt.Printf("  Combined:   %.4f (70%% ingredient + 30%% title)\n", combinedSim)

			// Show IDF values for shared tokens
			if len(sharedIngTokens) > 0 {
				fmt.Printf("\nIDF values for shared ingredient tokens:\n")
				for _, token := range sharedIngTokens {
					fmt.Printf("  %s: %.4f\n", token, idf[token])
				}
			}

			if len(sharedTitleTokens) > 0 {
				fmt.Printf("\nIDF values for shared title tokens:\n")
				for _, token := range sharedTitleTokens {
					val := idf[token]
					if val == 0 {
						fmt.Printf("  %s: 1.0000 (default for title-only words)\n", token)
					} else {
						fmt.Printf("  %s: %.4f\n", token, val)
					}
				}
			}
		}
	}
}
