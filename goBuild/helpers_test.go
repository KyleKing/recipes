package goBuild

import (
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestToTitleName(t *testing.T) {
	tests := []struct {
		name     string
		input    string
		expected string
	}{
		{
			"snake_case",
			"chocolate_chip_cookies",
			"Chocolate Chip Cookies",
		},
		{
			"with path",
			"/content/dessert/chocolate_cake.dj",
			"Chocolate Cake",
		},
		{
			"with underscores",
			"super__delicious_recipe",
			"Super Delicious Recipe",
		},
		{
			"windows path",
			"C:/recipes/main/chicken_rice.dj",
			"Chicken Rice",
		},
		{
			"single word",
			"pasta",
			"Pasta",
		},
		{
			"already titled",
			"Beef Stew",
			"Beef Stew",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := toTitleName(tt.input)
			assert.Equal(t, tt.expected, result)
		})
	}
}

func TestWithHtmlExt(t *testing.T) {
	tests := []struct {
		name     string
		input    string
		expected string
	}{
		{
			".dj file",
			"recipe.dj",
			"recipe.html",
		},
		{
			".txt file",
			"document.txt",
			"document.html",
		},
		{
			"no extension",
			"recipe",
			"recipe.html",
		},
		{
			"already .html",
			"page.html",
			"page.html",
		},
		{
			"with path",
			"/content/soup/chili.dj",
			"/content/soup/chili.html",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := withHtmlExt(tt.input)
			assert.Equal(t, tt.expected, result)
		})
	}
}
