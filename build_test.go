package main

import (
    "os"

	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestToTitleCase(t *testing.T) {
	title := ToTitleCase("words__word_phrase")
	assert.Equal(t, "Words Word Phrase", title)
}

func TestBuildHtml(t *testing.T) {
	html, err := BuildHtml("_recipe_template.dj")
	require.NoError(t, err)

    // DEBUG: write out the formatted HTML for manual review
    pthTmp := "_recipe_template.dj.html"
	err = os.WriteFile(pthTmp, html.Bytes(), 0644)
	require.NoError(t, err)

    out := string(html.Bytes())
	assert.Contains(t, out, "<title>Recipe Template : Recipe</title>")
	assert.Contains(t, out, "<p>Personal rating: 0 / 5</p>")

    err = os.Remove(pthTmp)
    require.NoError(t, err)
}
