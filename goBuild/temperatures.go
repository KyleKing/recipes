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

// `130 °F medium-rare (recommended)` -> the reading the recipe pages hint inline
var (
	temperatureReadingRe = regexp.MustCompile(`^\d+(?:\.\d+)?\s*°\s*[FC]`)
	recommendedSuffix    = "(recommended)"
)

type Temperature struct {
	Name        string   `json:"name"`
	Recommended string   `json:"recommended,omitempty"`
	Levels      []string `json:"levels"`
	Note        string   `json:"note,omitempty"`
	Href        string   `json:"href"`
}

// A temperature entry answers to every key its subject is written under across the corpus,
// so `salmon` and `skinless-salmon-filets` reach the same chart
func headingIngredientKeys(heading djot_parser.TreeNode[djot_parser.DjotNode]) []string {
	var keys []string
	for _, child := range heading.Children {
		if child.Type == djot_parser.SpanNode {
			keys = append(keys, ingredientKeysOf(child)...)
		}
	}
	return keys
}

func parseTemperatureSection(section djot_parser.TreeNode[djot_parser.DjotNode], href string) (Temperature, []string, bool) {
	entry := Temperature{}
	var keys []string
	for _, child := range section.Children {
		switch child.Type {
		case djot_parser.HeadingNode:
			if child.Attributes.Get(djot_parser.HeadingLevelKey) != "###" {
				return entry, nil, false
			}
			entry.Name = nodeText(child)
			keys = headingIngredientKeys(child)
		case djot_parser.UnorderedListNode:
			for _, item := range child.Children {
				line := nodeText(item)
				entry.Levels = append(entry.Levels, strings.TrimSpace(strings.Replace(line, recommendedSuffix, "", 1)))
				if strings.Contains(line, recommendedSuffix) {
					entry.Recommended = temperatureReadingRe.FindString(line)
				}
			}
		case djot_parser.ParagraphNode:
			entry.Note = nodeText(child)
		}
	}
	if entry.Name == "" || len(entry.Levels) == 0 {
		return entry, nil, false
	}
	if len(keys) == 0 {
		keys = []string{IngredientKey(entry.Name)}
	}
	entry.Href = href + "#" + section.Attributes.Get(djot_parser.IdKey)
	return entry, keys, true
}

func collectTemperatures(contentDir string) (map[string]Temperature, error) {
	referenceDir := filepath.Join(contentDir, "reference")
	if _, err := os.Stat(referenceDir); os.IsNotExist(err) {
		return map[string]Temperature{}, nil
	}
	paths, err := filepath.Glob(filepath.Join(referenceDir, "*cooking_temperatures*.dj"))
	if err != nil {
		return nil, err
	}
	if len(paths) == 0 {
		return nil, fmt.Errorf("no cooking temperature reference page found under %s", referenceDir)
	}
	sort.Strings(paths)

	table := map[string]Temperature{}
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
				entry, keys, ok := parseTemperatureSection(section, href)
				if !ok {
					continue
				}
				for _, key := range keys {
					if existing, clash := table[key]; clash {
						return nil, fmt.Errorf("%s: ingredient %q is claimed by both %q and %q", path, key, existing.Name, entry.Name)
					}
					table[key] = entry
				}
			}
		}
	}
	return table, nil
}

// An alias no recipe declares can never surface, so it is a typo rather than a spare
func validateTemperatureKeys(table map[string]Temperature, declared map[string]bool) error {
	var orphans []string
	for key := range table {
		if !declared[key] {
			orphans = append(orphans, key)
		}
	}
	if len(orphans) == 0 {
		return nil
	}
	sort.Strings(orphans)
	return fmt.Errorf("cooking temperatures name ingredients no recipe declares: %s", strings.Join(orphans, ", "))
}

func writeTemperatures(publicDir string, contentDir string, declared map[string]bool) error {
	table, err := collectTemperatures(contentDir)
	if err != nil {
		return err
	}
	if err := validateTemperatureKeys(table, declared); err != nil {
		return err
	}
	return writeJson(filepath.Join(publicDir, "_static", "temperatures.json"), table)
}
