package goBuild

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"

	"github.com/sivukhin/godjot/djot_parser"
	"github.com/sivukhin/godjot/djot_tokenizer"
)

const IngredientAttribute = "ing"

// One span may name several ingredients, as in `[sugars]{ing="brown-sugar white-sugar"}`
func ingredientKeysOf(node djot_parser.TreeNode[djot_parser.DjotNode]) []string {
	return strings.Fields(node.Attributes.Get(IngredientAttribute))
}

var nonSlugRe = regexp.MustCompile(`[^a-z0-9]+`)

// Stable key for an ingredient name, shared by recipe spans and substitution headings
func IngredientKey(name string) string {
	return strings.Trim(nonSlugRe.ReplaceAllString(strings.ToLower(name), "-"), "-")
}

// Render `[brown sugar]{ing="brown-sugar"}` so the client can bind steps to ingredients
func spanNodeConversion(s djot_parser.ConversionState, n func(c djot_parser.Children)) {
	keys := ingredientKeysOf(s.Node)
	if len(keys) == 0 {
		s.InlineNodeConverter("span", n)
		return
	}
	s.Writer.WriteString("<span class=\"ing-ref\" data-ing=\"" + strings.Join(keys, " ") + "\">")
	n(s.Node.Children)
	s.Writer.WriteString("</span>")
}

func isTaskItem(node djot_parser.TreeNode[djot_parser.DjotNode]) bool {
	class := node.Attributes.Get(djot_tokenizer.DjotAttributeClassKey)
	return class == djot_parser.CheckedTaskItemClass || class == djot_parser.UncheckedTaskItemClass
}

// Walk the tree tracking whether we are somewhere a key is declared rather than referenced:
// an ingredient's own task-list item, or a substitution heading naming its subject
func walkIngredientKeys(node djot_parser.TreeNode[djot_parser.DjotNode], inTask bool, declared map[string]bool, referenced map[string]bool) {
	if node.Type == djot_parser.HeadingNode || (node.Type == djot_parser.ListItemNode && isTaskItem(node)) {
		inTask = true
	}
	if node.Type == djot_parser.SpanNode {
		for _, key := range ingredientKeysOf(node) {
			if inTask {
				declared[key] = true
			} else {
				referenced[key] = true
			}
		}
	}
	for _, child := range node.Children {
		walkIngredientKeys(child, inTask, declared, referenced)
	}
}

func ingredientKeys(ast []djot_parser.TreeNode[djot_parser.DjotNode]) (declared map[string]bool, referenced map[string]bool) {
	declared, referenced = map[string]bool{}, map[string]bool{}
	for _, node := range ast {
		walkIngredientKeys(node, false, declared, referenced)
	}
	return declared, referenced
}

// A step may only reference a key that an ingredient in the same file declares, otherwise
// retirement would silently do nothing
func validateIngredientRefs(ast []djot_parser.TreeNode[djot_parser.DjotNode], path string) error {
	declared, referenced := ingredientKeys(ast)
	var unknown []string
	for key := range referenced {
		if !declared[key] {
			unknown = append(unknown, key)
		}
	}
	if len(unknown) == 0 {
		return nil
	}
	sort.Strings(unknown)
	return fmt.Errorf("%s: steps reference ingredients that no ingredient declares: %s", path, strings.Join(unknown, ", "))
}

type ingredientUse struct {
	Name string `json:"name"`
	Url  string `json:"url"`
}

// Map every declared ingredient key to the recipes that use it, for the dossier's
// "other recipes" list
func writeIngredientIndex(publicDir string, rMap RecipeMap, cache *RecipeCache) error {
	index := map[string][]ingredientUse{}
	for path, recipe := range rMap {
		cached, exists := cache.Get(path)
		if !exists {
			continue
		}
		declared, _ := ingredientKeys(cached.ast)
		for key := range declared {
			index[key] = append(index[key], ingredientUse{Name: recipe.name, Url: recipe.url})
		}
	}
	for key := range index {
		sort.Slice(index[key], func(i, j int) bool { return index[key][i].Name < index[key][j].Name })
	}
	return writeJson(filepath.Join(publicDir, "_static", "ingredient-index.json"), index)
}

func writeJson(path string, value any) error {
	encoded, err := json.Marshal(value)
	if err != nil {
		return err
	}
	return os.WriteFile(path, encoded, 0o644)
}
