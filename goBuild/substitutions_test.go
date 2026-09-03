package goBuild

import (
	"strings"
	"testing"

	"github.com/sivukhin/godjot/djot_parser"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestParseSubstitutionHeading(t *testing.T) {
	tests := []struct {
		heading string
		amount  string
		name    string
		use     string
	}{
		{"1 cup Buttermilk", "1 cup", "Buttermilk", ""},
		{"1 cup Heavy Cream, for cooking", "1 cup", "Heavy Cream", "for cooking"},
		{"1 Egg, in baking", "1", "Egg", "in baking"},
		{"1 Tbsp Chili Powder", "1 Tbsp", "Chili Powder", ""},
		{"Garam Masala", "", "Garam Masala", ""},
	}
	for _, tt := range tests {
		t.Run(tt.heading, func(t *testing.T) {
			amount, name, use := parseSubstitutionHeading(tt.heading)
			assert.Equal(t, tt.amount, amount)
			assert.Equal(t, tt.name, name)
			assert.Equal(t, tt.use, use)
		})
	}
}

// The reference pages are the corpus the dossier reads, so parse the real ones
func TestCollectSubstitutions(t *testing.T) {
	table, err := collectSubstitutions("../content")
	require.NoError(t, err)

	brownSugar := table["brown-sugar"]
	require.Len(t, brownSugar, 1)
	assert.Equal(t, "1 cup", brownSugar[0].Amount)
	assert.Equal(t, []string{"1 cup granulated sugar", "1 Tbsp molasses"}, brownSugar[0].Items)
	assert.Contains(t, brownSugar[0].Note, "dark brown sugar")
	assert.Equal(t, "/reference/ingredient_substitutions.html#1-cup-Brown-Sugar", brownSugar[0].Href)

	// A heading the amount-plus-name pattern cannot read carries an explicit key
	assert.Len(t, table["baking-soda"], 1)
	assert.NotContains(t, table, "baking-powder-for-1-tsp-baking-soda")
}

func TestValidateIngredientRefs(t *testing.T) {
	declared := "## Ingredients\n\n- [ ] 1 cup [brown sugar]{ing=\"brown-sugar\"}\n\n## Recipe\n\n"

	assert.NoError(t, validateIngredientRefs(
		djot_parser.BuildDjotAst([]byte(declared+"1. Beat the [sugar]{ing=\"brown-sugar\"}\n")), "ok.dj"))

	err := validateIngredientRefs(
		djot_parser.BuildDjotAst([]byte(declared+"1. Beat the [butter]{ing=\"butter\"}\n")), "bad.dj")
	require.Error(t, err)
	assert.Contains(t, err.Error(), "butter")
}

func TestValidateIngredientKeyShape(t *testing.T) {
	tests := map[string]string{
		"brown-sugar":          "",
		"all-purpose-flour":    "",
		"orange-juice":         "",
		"cup-baking-soda":      "starts with a measurement word",
		"of-black-beans":       "starts with a measurement word",
		"basmati-rice-200g":    "carries a quantity",
		"juice-of-1-lemon":     "carries a quantity",
		"piece-kombu":          "starts with a measurement word",
		"boxes-chickpea-pasta": "starts with a measurement word",
		"packed-light":         "names only a qualifier",
		"steamed-brown":        "names only a qualifier",
		"sliced-pickled":       "names only a qualifier",
		"skinless":             "names only a qualifier",
	}
	for key, reason := range tests {
		assert.Equal(t, reason, malformedKey(key), key)
	}

	err := validateIngredientRefs(
		djot_parser.BuildDjotAst([]byte("## Ingredients\n\n- [ ] 1/3 [cup baking soda]{ing=\"cup-baking-soda\"}\n")), "bad.dj")
	require.Error(t, err)
	assert.Contains(t, err.Error(), "cup-baking-soda (starts with a measurement word)")
}

func TestMentionAliases(t *testing.T) {
	// Peeling stops at the first word that is not a qualifier, so a bare "sugar" never matches
	assert.Equal(t, []string{"light brown sugar", "brown sugar"}, mentionAliases("light brown sugar"))
	assert.Equal(t, []string{"raw shrimp defrosted", "shrimp defrosted"}, mentionAliases("raw shrimp; defrosted"))
	// A short lone word matches ordinary cooking prose rather than the ingredient
	assert.Equal(t, []string{"flour"}, mentionAliases("flour"))
	assert.Empty(t, mentionAliases("oil"))
	// An accented name is one word, not two split around the accent
	assert.Equal(t, []string{"jalapeño"}, mentionAliases("jalapeño"))
}

func TestValidateIngredientMentions(t *testing.T) {
	declared := "## Ingredients\n\n- [ ] 1 cup [light brown sugar]{ing=\"brown-sugar\"}\n\n## Recipe\n\n"

	assert.NoError(t, validateIngredientMentions(
		djot_parser.BuildDjotAst([]byte(declared+"1. Beat the [brown sugar]{ing=\"brown-sugar\"} in\n")), "ok.dj"))

	// A hyphenated compound is a different word, and a note is not a step
	assert.NoError(t, validateIngredientMentions(
		djot_parser.BuildDjotAst([]byte(declared+"1. Bake until golden brown\n\n## Notes\n\n- Brown sugar keeps it moist\n")), "ok.dj"))

	err := validateIngredientMentions(
		djot_parser.BuildDjotAst([]byte(declared+"1. Beat the brown sugar in\n")), "bad.dj")
	require.Error(t, err)
	assert.Contains(t, err.Error(), `"brown sugar"`)
}

func TestMentionsOnlyBindTheFirstStep(t *testing.T) {
	declared := "## Ingredients\n\n- [ ] 1 lb [asparagus]{ing=\"asparagus\"}\n\n## Recipe\n\n"

	// The second step works on what the first one already took, so it may write the name bare
	assert.NoError(t, validateIngredientMentions(
		djot_parser.BuildDjotAst([]byte(declared+
			"1. Chop the [asparagus]{ing=\"asparagus\"}\n1. Cook the asparagus 5 minutes\n")), "ok.dj"))

	// An ingredient no step ever links is still reported on the step that first names it
	err := validateIngredientMentions(
		djot_parser.BuildDjotAst([]byte(declared+
			"1. Chop the asparagus\n1. Cook the asparagus 5 minutes\n")), "bad.dj")
	require.Error(t, err)
	assert.Equal(t, 1, strings.Count(err.Error(), "asparagus\" in"))
}

func TestAShorterNameInsideALongerOneIsNotAMention(t *testing.T) {
	declared := "## Ingredients\n\n- [ ] 1/2 cup [butter]{ing=\"butter\"}\n" +
		"- [ ] 1/2 cup [peanut butter]{ing=\"peanut-butter\"}\n\n## Recipe\n\n"

	assert.NoError(t, validateIngredientMentions(
		djot_parser.BuildDjotAst([]byte(declared+
			"1. Mix in the [peanut butter]{ing=\"peanut-butter\"}\n")), "ok.dj"))

	// The dairy butter standing on its own is still caught
	err := validateIngredientMentions(
		djot_parser.BuildDjotAst([]byte(declared+
			"1. Beat the [peanut butter]{ing=\"peanut-butter\"} with the butter\n")), "bad.dj")
	require.Error(t, err)
	assert.Contains(t, err.Error(), `"butter" in`)
}

func TestALaterStepMayNotRelinkAnIngredient(t *testing.T) {
	declared := "## Ingredients\n\n- [ ] 1 lb [asparagus]{ing=\"asparagus\"}\n\n## Recipe\n\n"
	linkedTwice := declared +
		"1. Chop the [asparagus]{ing=\"asparagus\"}\n1. Cook the [asparagus]{ing=\"asparagus\"} 5 minutes\n"

	err := validateIngredientMentions(djot_parser.BuildDjotAst([]byte(linkedTwice)), "main/bad.dj")
	require.Error(t, err)
	assert.Contains(t, err.Error(), "already took")

	// The demo page draws on one ingredient twice so the browser tests can pin the behaviour
	assert.NoError(t, validateIngredientMentions(
		djot_parser.BuildDjotAst([]byte(linkedTwice)), "reference/nested_list_demo.dj"))
}
