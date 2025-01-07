package goBuild

import (
	"os"

	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func testToTitleCase(t *testing.T) {
	title := toTitleCase("words__word_phrase")
	assert.Equal(t, "Words Word Phrase", title)
}

func testBuildHtml(t *testing.T) {
	html, err := buildHtml("_recipe_template.dj")
	require.NoError(t, err)

	// For debugging, write out the formatted HTML for manual review
	pthTmp := "_recipe_template.dj.html"
	err = os.WriteFile(pthTmp, html.Bytes(), 0644)
	require.NoError(t, err)

	out := string(html.Bytes())
	assert.Contains(t, out, "<title>Recipe Template : Recipe</title>")
	assert.Contains(t, out, "<p>Personal rating: Not yet rated</p>")
	assert.Contains(t, out, "<img class=\"image-recipe\" alt=\"Image is missing\" src=\"/_icons/placeholder.webp\">")

	if !t.Failed() {
		err = os.Remove(pthTmp)
		require.NoError(t, err)
	}
}
