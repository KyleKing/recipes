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

// knownIngredients are common foods that NLP may misclassify (e.g., "avocado" tagged as VERB)
var knownIngredients = map[string]bool{
	"avocado": true, "cilantro": true, "cumin": true, "paprika": true,
	"turmeric": true, "coriander": true, "quinoa": true, "tofu": true,
	"tempeh": true, "edamame": true, "sriracha": true, "tahini": true,
	"hummus": true, "feta": true, "mozzarella": true, "ricotta": true,
	"mascarpone": true, "prosciutto": true, "pancetta": true, "chorizo": true,
}

// measurementUnits are words that indicate a quantity rather than an ingredient.
// These must be hardcoded because POS tagging cannot distinguish "cup" (measurement)
// from "cup" (ingredient in "cupcake").
var measurementUnits = map[string]bool{
	"cup": true, "cups": true, "tbsp": true, "tsp": true,
	"tablespoon": true, "tablespoons": true, "teaspoon": true, "teaspoons": true,
	"ounce": true, "ounces": true, "oz": true, "pound": true, "pounds": true, "lb": true, "lbs": true,
	"can": true, "cans": true, "jar": true, "jars": true, "bottle": true, "bottles": true,
	"piece": true, "pieces": true, "slice": true, "slices": true, "pinch": true, "dash": true,
	"clove": true, "cloves": true,
}

// nonIngredientRoots are noun chunk roots that don't represent actual ingredients
var nonIngredientRoots = map[string]bool{
	"taste": true, "room": true, "temperature": true,
	"paste": true, "mixture": true,
}

// oilSimilarityThreshold is used for vector-based oil normalization
const oilSimilarityThreshold = 0.45

// baseOilTypes are the canonical oil types we normalize to
var baseOilTypes = []string{"olive oil", "sesame oil", "coconut oil", "vegetable oil"}

func extractIngredientsWithNLP(rawIngredients []string) map[string]bool {
	nlp := getNLP()
	phrases := make(map[string]bool)

	for _, ingredient := range rawIngredients {
		cleaned := removeParenthetical(ingredient)
		foundAnyToken := false

		// Strategy: Use noun chunks with dependency parsing
		// 1. RootText identifies the core ingredient noun
		// 2. Dep=compound tokens are related nouns to also extract
		// 3. Dep=amod tokens are adjective modifiers (keep in phrase)
		// 4. Handle orphaned verb modifiers (e.g., "baking" in "baking powder")

		// First, tokenize to find orphaned modifiers
		allTokens := nlp.Tokenize(cleaned)
		orphanedModifiers := findOrphanedVerbModifiers(allTokens)

		chunks := nlp.GetNounChunks(cleaned)
		for _, chunk := range chunks {
			rootLower := strings.ToLower(chunk.RootText)

			// Skip chunks where root is a measurement unit
			if measurementUnits[rootLower] {
				continue
			}

			// Skip non-ingredient roots
			if nonIngredientRoots[rootLower] {
				continue
			}

			// Build the ingredient phrase from chunk tokens using dependency info
			chunkTokens := nlp.Tokenize(chunk.Text)
			ingredientParts := extractIngredientPartsFromTokens(chunkTokens, rootLower)

			// Check if there's an orphaned modifier for this root
			rootLemma := getLemmaForRoot(chunkTokens, rootLower)
			if modifier, hasModifier := orphanedModifiers[rootLemma]; hasModifier {
				// Prepend the orphaned modifier (e.g., "baking" + "powder")
				ingredientParts = append([]string{modifier}, ingredientParts...)
			}

			if len(ingredientParts) > 0 {
				phrase := strings.Join(ingredientParts, " ")

				// Normalize oil types using vector similarity
				phrase = normalizeOilWithSimilarity(nlp, phrase)

				if len(phrase) >= 3 {
					phrases[phrase] = true
					foundAnyToken = true

					// Extract compound modifiers as separate ingredients
					// e.g., "chicken thighs" → also add "chicken"
					// Use lemmatized root for checking meaningful roots
					rootLemma := getLemmaForRoot(chunkTokens, rootLower)
					extractCompoundIngredients(chunkTokens, rootLemma, phrases)
				}
			}
		}

		// Fallback for ingredients not captured by noun chunks
		if !foundAnyToken {
			tokens := nlp.Tokenize(cleaned)
			for _, token := range tokens {
				if isIngredientPOS(token) && !token.IsStop {
					lemma := strings.ToLower(token.Lemma)
					if !measurementUnits[lemma] && len(lemma) >= 3 {
						phrases[lemma] = true
						foundAnyToken = true
					}
				}
			}
		}

		// Final fallback: check for known ingredients that NLP misclassifies
		if !foundAnyToken {
			lowerCleaned := strings.ToLower(cleaned)
			for known := range knownIngredients {
				if strings.Contains(lowerCleaned, known) {
					phrases[known] = true
				}
			}
		}
	}

	return phrases
}

// getLemmaForRoot finds the lemma for the root token
func getLemmaForRoot(tokens []spacy.Token, rootLower string) string {
	for _, tok := range tokens {
		if strings.ToLower(tok.Text) == rootLower {
			return strings.ToLower(tok.Lemma)
		}
	}
	return rootLower // fallback to original if not found
}

// findOrphanedVerbModifiers identifies verb modifiers (Dep=acl) that modify nouns but aren't in noun chunks
// Returns a map of target noun lemma → modifier text (e.g., "powder" → "baking")
func findOrphanedVerbModifiers(tokens []spacy.Token) map[string]string {
	modifiers := make(map[string]string)

	// Build a map of token index → token for lookup
	tokenMap := make(map[int]*spacy.Token)
	for i := range tokens {
		tokenMap[i] = &tokens[i]
	}

	for i, tok := range tokens {
		// Look for verb modifiers (Dep=acl) that should be part of compound ingredients
		if tok.Dep == "acl" && tok.POS == "VERB" {
			// Find the noun this verb modifies by looking at adjacent tokens
			// In "baking powder", "baking" (index i) modifies "powder" (index i+1)
			if i+1 < len(tokens) {
				nextTok := tokens[i+1]
				if nextTok.POS == "NOUN" || nextTok.POS == "PROPN" {
					targetLemma := strings.ToLower(nextTok.Lemma)
					// Use original text for verb modifiers, not lemma (keep "baking" not "bake")
					modifiers[targetLemma] = strings.ToLower(tok.Text)
				}
			}
		}
	}

	return modifiers
}

// extractIngredientPartsFromTokens builds an ingredient phrase from tokens using dependency parsing
func extractIngredientPartsFromTokens(tokens []spacy.Token, rootLower string) []string {
	parts := []string{}

	for _, tok := range tokens {
		tokLower := strings.ToLower(tok.Text)
		lemmaLower := strings.ToLower(tok.Lemma)

		// Skip based on POS (quantities, punctuation, auxiliaries, prepositions)
		if isSkippablePOS(tok.POS) {
			continue
		}

		// Skip measurement units
		if measurementUnits[tokLower] || measurementUnits[lemmaLower] {
			continue
		}

		// Skip numeric tokens
		if isNumeric(tokLower) {
			continue
		}

		// Include tokens that are:
		// - The root noun
		// - Compound modifiers (Dep=compound)
		// - Adjective modifiers (Dep=amod) that aren't sizes/prep methods
		// - Verb modifiers (Dep=acl) that are part of ingredient names (e.g., "baking" in "baking powder")
		switch tok.Dep {
		case "ROOT", "nsubj", "dobj", "pobj", "appos", "conj":
			// Core noun - use lemma for normalization (beans → bean)
			if tok.POS == "NOUN" || tok.POS == "PROPN" {
				parts = append(parts, lemmaLower)
			}
		case "compound":
			// Compound modifier (e.g., "chicken" in "chicken thighs")
			parts = append(parts, lemmaLower)
		case "amod":
			// Adjective modifier - include if it's a meaningful ingredient qualifier
			if isIngredientQualifier(tokLower) {
				parts = append(parts, tokLower)
			}
		case "acl":
			// Adjectival clause (verb acting as modifier)
			// Include verbs that are part of ingredient names (e.g., "baking" in "baking powder")
			// These appear within the noun chunk, unlike post-noun preparation methods
			if tok.POS == "VERB" {
				parts = append(parts, lemmaLower)
			}
		}
	}

	return parts
}

// extractCompoundIngredients adds compound modifiers as separate ingredients
// e.g., "chicken thighs" → also adds "chicken"
// Only extracts compounds that are meaningful standalone ingredients
func extractCompoundIngredients(tokens []spacy.Token, rootLower string, phrases map[string]bool) {
	// Roots that indicate the compound modifier is meaningful as standalone
	// e.g., "thighs" in "chicken thighs" → extract "chicken"
	// but "oil" in "olive oil" → don't extract "olive"
	meaningfulRoots := map[string]bool{
		// Protein cuts - the protein name is meaningful
		"thigh": true, "breast": true, "wing": true, "drumstick": true,
		"tenderloin": true, "loin": true, "chop": true, "rib": true,
		"shoulder": true, "belly": true,
		// Processed forms - the base ingredient is meaningful
		"powder": true, "flake": true, "puree": true,
		"extract": true, "zest": true, "juice": true,
	}

	if !meaningfulRoots[rootLower] {
		return
	}

	for _, tok := range tokens {
		if tok.Dep == "compound" {
			lemma := strings.ToLower(tok.Lemma)
			// Only add if it's a noun (not adjective used as compound)
			if (tok.POS == "NOUN" || tok.POS == "PROPN") && len(lemma) >= 3 {
				if !measurementUnits[lemma] {
					phrases[lemma] = true
				}
			}
		}
	}
}

// normalizeOilWithSimilarity normalizes oil variations using vector similarity
// Only normalizes variants of the same base oil (e.g., "extra-virgin olive oil" → "olive oil")
func normalizeOilWithSimilarity(nlp *spacy.NLP, phrase string) string {
	// Quick check: does this phrase end with "oil"?
	if !strings.HasSuffix(phrase, "oil") {
		return phrase
	}

	// Check each base oil type
	for _, baseOil := range baseOilTypes {
		if phrase == baseOil {
			return phrase // Already normalized
		}

		// Extract the oil type word (e.g., "olive" from "olive oil")
		baseOilWord := strings.TrimSuffix(baseOil, " oil")

		// Only consider normalizing if the phrase contains the same oil type word
		// This prevents "sesame oil" from matching "olive oil"
		if !strings.Contains(phrase, baseOilWord) {
			continue
		}

		sim := nlp.Similarity(phrase, baseOil)
		if sim >= oilSimilarityThreshold {
			return baseOil
		}
	}

	return phrase
}

// isIngredientPOS returns true if the token's POS indicates it could be an ingredient
func isIngredientPOS(tok spacy.Token) bool {
	return tok.POS == "NOUN" || tok.POS == "PROPN"
}

// isSkippablePOS returns true if the POS should be skipped entirely
func isSkippablePOS(pos string) bool {
	skip := map[string]bool{
		"NUM":   true, // Numbers
		"PUNCT": true, // Punctuation
		"AUX":   true, // Auxiliary verbs (can, will, etc.)
		"ADP":   true, // Prepositions (in, on, to)
		"CCONJ": true, // Coordinating conjunctions (and, or)
		"SCONJ": true, // Subordinating conjunctions
		"DET":   true, // Determiners (the, a, an)
		"PART":  true, // Particles (to in "to taste")
		"ADV":   true, // Adverbs (very, finely)
		"X":     true, // Other (often numbers or symbols)
	}
	return skip[pos]
}

// isIngredientQualifier returns true if the adjective is meaningful for ingredients
// (not a size, prep method, or generic descriptor)
func isIngredientQualifier(adj string) bool {
	// Skip sizes
	sizes := map[string]bool{
		"large": true, "medium": true, "small": true,
		"whole": true, "half": true,
	}
	if sizes[adj] {
		return false
	}

	// Skip preparation methods (past participles used as adjectives)
	prepMethods := map[string]bool{
		"chopped": true, "diced": true, "minced": true, "sliced": true,
		"grated": true, "shredded": true, "crushed": true, "cooked": true,
		"fresh": true, "dried": true, "ground": true,
	}
	if prepMethods[adj] {
		return false
	}

	// Include color/type qualifiers that distinguish ingredients
	// e.g., "white" beans, "black" pepper, "red" pepper
	return true
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

	// Words to strip from beginning or end of phrase
	stripWords := map[string]bool{
		// Measurements
		"cup": true, "cups": true, "tbsp": true, "tsp": true,
		"tablespoon": true, "tablespoons": true, "teaspoon": true, "teaspoons": true,
		"ounce": true, "ounces": true, "oz": true, "pound": true, "pounds": true, "lb": true, "lbs": true,
		"can": true, "cans": true, "jar": true, "jars": true, "bottle": true, "bottles": true,
		"piece": true, "pieces": true,
		"slice": true, "slices": true, "pinch": true, "dash": true,
		// Sizes
		"large": true, "medium": true, "small": true, "whole": true, "half": true, "halves": true,
		// Preparation methods
		"chopped": true, "diced": true, "minced": true, "sliced": true,
		"grated": true, "shredded": true, "fresh": true, "dried": true,
		"ground": true, "crushed": true, "cooked": true,
		// Trailing modifiers that indicate the base ingredient is more important
		"clove": true, "cloves": true,
	}

	// Strip leading words
	resultWords := []string{}
	skipLeading := true
	for _, word := range words {
		if isNumeric(word) || isFraction(word) {
			continue
		}
		if skipLeading && stripWords[word] {
			continue
		}
		skipLeading = false
		resultWords = append(resultWords, word)
	}

	// Strip trailing words
	for len(resultWords) > 1 && stripWords[resultWords[len(resultWords)-1]] {
		resultWords = resultWords[:len(resultWords)-1]
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

	// Skip pure measurement units and non-ingredient phrases
	skipPhrases := map[string]bool{
		// Measurement units
		"cup": true, "cups": true, "tbsp": true, "tsp": true,
		"tablespoon": true, "tablespoons": true, "teaspoon": true, "teaspoons": true,
		"oz": true, "ounce": true, "ounces": true, "lb": true, "lbs": true, "pound": true, "pounds": true,
		"can": true, "cans": true, "jar": true, "jars": true,
		"piece": true, "pieces": true, "slice": true, "slices": true,
		// Generic cooking terms that aren't ingredients
		"paste": true, "a paste": true, "mixture": true, "a mixture": true,
		"bone": true, "boneless": true, "skinless": true, "skin": true,
		"taste": true, "to taste": true, "room temperature": true,
	}

	return !skipPhrases[phrase] && !isNumeric(phrase)
}

func isValidIngredientToken(token string) bool {
	if len(token) < 3 {
		return false
	}

	// Skip measurement units, preparation methods, sizes, and common non-ingredient words
	skipWords := map[string]bool{
		// Measurements
		"cup": true, "tbsp": true, "tsp": true, "tablespoon": true, "teaspoon": true,
		"ounce": true, "pound": true, "can": true, "jar": true, "oz": true, "lb": true, "lbs": true,
		"clove": true, "cloves": true, "piece": true, "slice": true, "pinch": true, "dash": true,
		// Preparation methods
		"chopped": true, "diced": true, "minced": true, "sliced": true,
		"grated": true, "shredded": true, "crushed": true,
		// Sizes and states
		"large": true, "medium": true, "small": true,
		"fresh": true, "dried": true, "cooked": true,
		"whole": true, "half": true,
		// Generic cooking terms that aren't ingredients
		"bone": true, "boneless": true, "skinless": true, "skin": true,
		"paste": true, "mixture": true,
		// Generic words
		"optional": true, "taste": true, "color": true,
		"each": true, "serving": true,
	}

	return !skipWords[token] && !isNumeric(token)
}

func isNumeric(s string) bool {
	// Strip leading ~ or - for approximate quantities
	cleaned := strings.TrimLeft(s, "~-")
	if len(cleaned) == 0 {
		return false
	}
	for _, r := range cleaned {
		if (r < '0' || r > '9') && r != '.' && r != '-' {
			return false
		}
	}
	return true
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

func calculateTitleSimilarity(titleA, titleB string, idf map[string]float64) float64 {
	tokensA := extractTitleTokens(titleA)
	tokensB := extractTitleTokens(titleB)

	if len(tokensA) == 0 || len(tokensB) == 0 {
		return 0.0
	}

	// Use TF-IDF weighted cosine similarity (same as ingredient matching)
	// This automatically gives higher weight to distinctive words like "balls"
	var dotProduct float64
	var magnitudeA float64
	var magnitudeB float64

	for token := range tokensA {
		weight := idf[token]
		if weight == 0 {
			// Token not in ingredient IDF (title-only word), use default weight
			weight = 1.0
		}
		magnitudeA += weight * weight
	}

	for token := range tokensB {
		weight := idf[token]
		if weight == 0 {
			weight = 1.0
		}
		magnitudeB += weight * weight
	}

	for token := range tokensA {
		if tokensB[token] {
			weight := idf[token]
			if weight == 0 {
				weight = 1.0
			}
			dotProduct += weight * weight
		}
	}

	if magnitudeA == 0 || magnitudeB == 0 {
		return 0.0
	}

	return dotProduct / (math.Sqrt(magnitudeA) * math.Sqrt(magnitudeB))
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
	titleSim := calculateTitleSimilarity(a.title, b.title, idf)

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
		titleScore := calculateTitleSimilarity(target.title, candidate.title, idf)
		combinedScore := 0.7*ingredientScore + 0.3*titleScore

		sharedIngredients := getSharedTokens(target.tokens, candidate.tokens)

		// Require at least one shared ingredient AND either:
		// - Combined score > 0.10, OR
		// - At least 2 shared ingredients (even if score is lower due to common ingredients)
		if len(sharedIngredients) > 0 && (combinedScore > 0.10 || len(sharedIngredients) >= 2) {
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
