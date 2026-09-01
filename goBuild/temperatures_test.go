package goBuild

import (
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// The reference page is the corpus the dossier reads, so parse the real one
func TestCollectTemperatures(t *testing.T) {
	table, err := collectTemperatures("../content")
	require.NoError(t, err)

	salmon := table["salmon"]
	assert.Equal(t, "Salmon", salmon.Name)
	assert.Equal(t, "130 °F", salmon.Recommended)
	assert.Equal(t, "130 °F medium-rare", salmon.Levels[1])
	assert.Contains(t, salmon.Note, "Farmed salmon")
	assert.Equal(t, "/reference/cooking_temperatures.html#Salmon", salmon.Href)

	// Every name an ingredient is written under reaches the same chart
	assert.Equal(t, salmon, table["skinless-salmon-filets"])
}

// An alias no recipe declares can never surface, so it is a typo rather than a spare
func TestValidateTemperatureKeys(t *testing.T) {
	table := map[string]Temperature{"salmon": {Name: "Salmon"}, "salmn": {Name: "Salmon"}}

	assert.NoError(t, validateTemperatureKeys(table, map[string]bool{"salmon": true, "salmn": true}))

	err := validateTemperatureKeys(table, map[string]bool{"salmon": true})
	require.Error(t, err)
	assert.Contains(t, err.Error(), "salmn")
}
