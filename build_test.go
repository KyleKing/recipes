package main

import (
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
	assert.Contains(t, string(html.Bytes()), "<div rating=\"0\" name-image=\"None\">")
}
