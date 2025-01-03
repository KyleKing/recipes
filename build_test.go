package main

import (
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestToTitleCase(t *testing.T) {
	title := ToTitleCase("words__word_phrase")
	assert.Equal(t, title, "Words Word Phrase")
}

func TestBuildHtml(t *testing.T) {
	html, err := BuildHtml("_recipe_template.dj")
	require.Nil(t, err)
	assert.Contains(t, html, "PLACEHOLDER")
}
