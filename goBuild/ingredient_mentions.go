package goBuild

import (
	"fmt"
	"regexp"
	"sort"
	"strings"

	"github.com/sivukhin/godjot/djot_parser"
)

// Words that qualify an ingredient rather than name it. Peeling them off the front of a
// declared name is what lets "light brown sugar" answer a step that writes "brown sugar".
var ingredientQualifiers = map[string]bool{
	"baby": true, "chilled": true, "chopped": true, "coarsely": true, "cold": true,
	"cooked": true, "crumbled": true, "crushed": true, "cubed": true, "diced": true,
	"dried": true, "drained": true, "dry": true, "extra": true, "finely": true,
	"firm": true, "fresh": true, "freshly": true, "frozen": true, "grated": true,
	"ground": true, "halved": true, "hot": true, "jumbo": true, "kosher": true,
	"large": true, "lean": true, "light": true, "low": true, "medium": true,
	"melted": true, "mild": true, "minced": true, "packed": true, "peeled": true,
	"plain": true, "pure": true, "raw": true, "refrigerated": true, "ripe": true,
	"roasted": true, "room": true, "salted": true, "shredded": true, "sifted": true,
	"skinless": true, "sliced": true, "small": true, "smoked": true, "soft": true,
	"softened": true, "sweetened": true, "thawed": true, "thin": true, "thinly": true,
	"toasted": true, "unbleached": true, "uncooked": true, "unsalted": true,
	"unsweetened": true, "warm": true, "whole": true,
}

var alphaWordRe = regexp.MustCompile(`[a-z][a-z']*`)

// How a step is likely to write this ingredient: the whole declared name, then the same
// name with each leading qualifier peeled off. Never a bare qualifier and never a single
// short word, both of which match ordinary cooking prose rather than an ingredient.
func mentionAliases(name string) []string {
	words := alphaWordRe.FindAllString(strings.ToLower(name), -1)
	var aliases []string
	for i := range words {
		if i > 0 && !ingredientQualifiers[words[i-1]] {
			break
		}
		rest := words[i:]
		if len(rest) > 1 || len(rest[0]) > 3 {
			aliases = append(aliases, strings.Join(rest, " "))
		}
	}
	return aliases
}

func singular(word string) string {
	switch {
	case strings.HasSuffix(word, "es") && len(word) > 4:
		return word[:len(word)-2]
	case strings.HasSuffix(word, "s") && !strings.HasSuffix(word, "ss"):
		return word[:len(word)-1]
	}
	return word
}

var mentionPatterns = map[string]*regexp.Regexp{}

// A hyphen on either side makes a different word, so "potato-shaped" is not the potatoes
func mentionPattern(alias string) *regexp.Regexp {
	if cached, ok := mentionPatterns[alias]; ok {
		return cached
	}
	parts := strings.Fields(alias)
	for i, word := range parts {
		parts[i] = regexp.QuoteMeta(singular(word)) + `e?s?`
	}
	compiled := regexp.MustCompile(`(?i)(^|[^\w-])` + strings.Join(parts, `\W+`) + `([^\w-]|$)`)
	mentionPatterns[alias] = compiled
	return compiled
}

type declaredIngredient struct {
	key  string
	name string
}

// Prose of one step with every already-linked span dropped, alongside the keys it links.
// A nested sub-step is its own step, so its text never counts twice.
func stepProse(node djot_parser.TreeNode[djot_parser.DjotNode], prose *strings.Builder, linked map[string]bool) {
	for _, child := range node.Children {
		switch {
		case isListNode(child.Type):
			continue
		case len(ingredientKeysOf(child)) > 0:
			for _, key := range ingredientKeysOf(child) {
				linked[key] = true
			}
		case child.Type == djot_parser.LinkNode || child.Type == djot_parser.ImageNode:
			continue
		case child.Type == djot_parser.TextNode:
			prose.WriteString(" ")
			prose.Write(child.FullText())
		default:
			stepProse(child, prose, linked)
		}
	}
}

func isListNode(kind djot_parser.DjotNode) bool {
	return kind == djot_parser.OrderedListNode || kind == djot_parser.UnorderedListNode ||
		kind == djot_parser.TaskListNode || kind == djot_parser.DefinitionListNode
}

// Notes and other prose sections mention ingredients as variations and asides. Linking one
// there would retire it, so only the Recipe section's steps are held to the rule.
func recipeSection(node djot_parser.TreeNode[djot_parser.DjotNode], inherited bool) bool {
	if node.Type != djot_parser.SectionNode {
		return inherited
	}
	for _, child := range node.Children {
		if child.Type != djot_parser.HeadingNode {
			continue
		}
		if len(child.Attributes.Get(djot_parser.HeadingLevelKey)) != 2 {
			return inherited
		}
		return strings.EqualFold(nodeText(child), "Recipe")
	}
	return inherited
}

func collectMentionTargets(node djot_parser.TreeNode[djot_parser.DjotNode], inTask, inRecipe, inSteps bool, declared *[]declaredIngredient, steps *[]djot_parser.TreeNode[djot_parser.DjotNode]) {
	inRecipe = recipeSection(node, inRecipe)
	if node.Type == djot_parser.HeadingNode || (node.Type == djot_parser.ListItemNode && isTaskItem(node)) {
		inTask = true
	}
	if inTask && node.Type == djot_parser.SpanNode {
		if keys := ingredientKeysOf(node); len(keys) > 0 {
			*declared = append(*declared, declaredIngredient{key: keys[0], name: nodeText(node)})
		}
	}
	if inRecipe && inSteps && node.Type == djot_parser.ListItemNode && !isTaskItem(node) {
		*steps = append(*steps, node)
	}
	for _, child := range node.Children {
		collectMentionTargets(child, inTask, inRecipe, node.Type == djot_parser.OrderedListNode, declared, steps)
	}
}

// A step that writes an ingredient's name without linking it leaves that ingredient
// unretired when the step is completed, and hides its substitutions and temperature
func validateIngredientMentions(ast []djot_parser.TreeNode[djot_parser.DjotNode], path string) error {
	var declared []declaredIngredient
	var steps []djot_parser.TreeNode[djot_parser.DjotNode]
	for _, node := range ast {
		collectMentionTargets(node, false, false, false, &declared, &steps)
	}

	var missed []string
	for _, step := range steps {
		var prose strings.Builder
		linked := map[string]bool{}
		stepProse(step, &prose, linked)
		text := prose.String()
		reported := map[string]bool{}
		for _, ingredient := range declared {
			if linked[ingredient.key] || reported[ingredient.key] {
				continue
			}
			for _, alias := range mentionAliases(ingredient.name) {
				if mentionPattern(alias).MatchString(text) {
					missed = append(missed, fmt.Sprintf("%q in %q", alias, strings.TrimSpace(text)))
					reported[ingredient.key] = true
					break
				}
			}
		}
	}
	if len(missed) == 0 {
		return nil
	}
	sort.Strings(missed)
	return fmt.Errorf("%s: steps name an ingredient without linking it: %s", path, strings.Join(missed, "; "))
}
