package main

import (
	"testing"
)

func TestToTitleCase(t *testing.T) {
	if f := ToTitleCase("words__word_phrase"); f != "Words Word Phrase" {
		t.Errorf("ToTitleCase(...) = %s", f)
	}
}
