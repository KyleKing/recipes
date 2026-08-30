package goBuild

import (
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"

	"github.com/sivukhin/godjot/djot_parser"
)

// `1 cup Heavy Cream, for cooking` -> amount `1 cup`, name `Heavy Cream`, use `for cooking`.
// A heading the pattern cannot read needs an explicit `{ing="..."}` on the heading
var substitutionHeadingRe = regexp.MustCompile(`^(?:(\d[\d./]*(?:\s+(?:cups?|tsp|Tbsp|tbsp|oz|lb|g|ml))?)\s+)?(.+)$`)

type Substitution struct {
	Key    string   `json:"key"`
	Amount string   `json:"amount"`
	Name   string   `json:"name"`
	Use    string   `json:"use,omitempty"`
	Items  []string `json:"items"`
	Note   string   `json:"note,omitempty"`
	Href   string   `json:"href"`
}

func parseSubstitutionHeading(heading string) (amount string, name string, use string) {
	if idx := strings.Index(heading, ","); idx != -1 {
		use = strings.TrimSpace(heading[idx+1:])
		heading = heading[:idx]
	}
	match := substitutionHeadingRe.FindStringSubmatch(strings.TrimSpace(heading))
	return match[1], strings.TrimSpace(match[2]), use
}

// A heading whose subject the amount-plus-name pattern cannot read names it with an inline
// span instead, as in `### Baking Powder for 1 tsp [Baking Soda]{ing="baking-soda"}`
func headingIngredientKey(heading djot_parser.TreeNode[djot_parser.DjotNode]) string {
	for _, child := range heading.Children {
		if child.Type == djot_parser.SpanNode {
			if keys := ingredientKeysOf(child); len(keys) > 0 {
				return keys[0]
			}
		}
	}
	return ""
}

func nodeText(node djot_parser.TreeNode[djot_parser.DjotNode]) string {
	return strings.TrimSpace(strings.ReplaceAll(string(node.FullText()), "\n", " "))
}

func parseSubstitutionSection(section djot_parser.TreeNode[djot_parser.DjotNode], href string) (Substitution, bool) {
	entry := Substitution{}
	for _, child := range section.Children {
		switch child.Type {
		case djot_parser.HeadingNode:
			if child.Attributes.Get(djot_parser.HeadingLevelKey) != "###" {
				return entry, false
			}
			entry.Amount, entry.Name, entry.Use = parseSubstitutionHeading(nodeText(child))
			entry.Key = headingIngredientKey(child)
		case djot_parser.UnorderedListNode:
			for _, item := range child.Children {
				entry.Items = append(entry.Items, nodeText(item))
			}
		case djot_parser.ParagraphNode:
			entry.Note = nodeText(child)
		}
	}
	if entry.Name == "" || len(entry.Items) == 0 {
		return entry, false
	}
	if entry.Key == "" {
		entry.Key = IngredientKey(entry.Name)
	}
	entry.Href = href + "#" + section.Attributes.Get(djot_parser.IdKey)
	return entry, true
}

// Read the reference pages into a key-indexed table the dossier can look up client-side
func collectSubstitutions(contentDir string) (map[string][]Substitution, error) {
	referenceDir := filepath.Join(contentDir, "reference")
	if _, err := os.Stat(referenceDir); os.IsNotExist(err) {
		return map[string][]Substitution{}, nil
	}
	paths, err := filepath.Glob(filepath.Join(referenceDir, "*substitutions*.dj"))
	if err != nil {
		return nil, err
	}
	if len(paths) == 0 {
		return nil, fmt.Errorf("no substitution reference pages found under %s", referenceDir)
	}
	sort.Strings(paths)

	table := map[string][]Substitution{}
	for _, path := range paths {
		text, err := os.ReadFile(path)
		if err != nil {
			return nil, err
		}
		rel, err := filepath.Rel(contentDir, path)
		if err != nil {
			return nil, err
		}
		href := "/" + withHtmlExt(rel)
		for _, node := range djot_parser.BuildDjotAst(text) {
			for _, section := range node.Children {
				if entry, ok := parseSubstitutionSection(section, href); ok {
					table[entry.Key] = append(table[entry.Key], entry)
				}
			}
		}
	}
	return table, nil
}

func writeSubstitutions(publicDir string, contentDir string) error {
	table, err := collectSubstitutions(contentDir)
	if err != nil {
		return err
	}
	return writeJson(filepath.Join(publicDir, "_static", "substitutions.json"), table)
}
