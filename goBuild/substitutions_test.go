package goBuild

import (
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
