package goBuild

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"testing"

	"github.com/sivukhin/godjot/djot_parser"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestToTitleCase(t *testing.T) {
	title := toTitleName("C:/home/words__word_phrase.dj")
	assert.Equal(t, "Words Word Phrase", title)
}

// Minimal version of `build.sh`
func initTestDir() (string, error) {
	cwd, err := os.Getwd()
	ExitOnError(err)

	contentTestDir := filepath.Join(cwd, "test_content")
	publicTestDir := filepath.Join(cwd, "test_public")

	os.RemoveAll(publicTestDir)

	cmd := exec.Command("cp", "-R", contentTestDir+"/", publicTestDir+"/")
	_, err = cmd.Output()
	if err != nil {
		return "", err
	}

	return publicTestDir, nil
}

// Replace expected directory with output from test for comparison in git
func gitDiffChanges(expectDir, publicTestDir string) {
	cmd := exec.Command("mv", expectDir+"/", expectDir+"-backup/")
	out, err := cmd.Output()
	if err != nil {
		fmt.Println("Error running:", cmd, out, err)
	}

	cmd = exec.Command("cp", "-R", publicTestDir+"/", expectDir+"/")
	out, err = cmd.Output()
	if err != nil {
		fmt.Println("Error running:", cmd, out, err)
	}
	fmt.Println("See git diff for changes")
}

func TestValidateNoDuplicateHeaders(t *testing.T) {
	t.Run("valid file with unique headers", func(t *testing.T) {
		content := []byte(`# Main Title

## Section 1

Content here

## Section 2

More content
`)
		ast := djot_parser.BuildDjotAst(content)
		err := validateNoDuplicateHeaders(ast, "test.dj")
		assert.NoError(t, err)
	})

	t.Run("duplicate headers detected", func(t *testing.T) {
		content := []byte(`# Main Title

## Ingredients

- Item 1

## Recipe

- Step 1

## Ingredients

- Item 2
`)
		ast := djot_parser.BuildDjotAst(content)
		err := validateNoDuplicateHeaders(ast, "test.dj")
		assert.Error(t, err)
		assert.Contains(t, err.Error(), "duplicate header found")
		assert.Contains(t, err.Error(), "Ingredients")
	})

	t.Run("nested headers with same text", func(t *testing.T) {
		content := []byte(`# Main Title

## Section

### Details

## Section

More content
`)
		ast := djot_parser.BuildDjotAst(content)
		err := validateNoDuplicateHeaders(ast, "test.dj")
		assert.Error(t, err)
		assert.Contains(t, err.Error(), "Section")
	})
}

func TestBuild(t *testing.T) {
	publicTestDir, errInit := initTestDir()
	require.NoError(t, errInit)
	expectDir := filepath.Join(filepath.Dir(publicTestDir), "test_expected")

	Build(publicTestDir)

	// Verify content matches expected using diff (https://stackoverflow.com/a/1644641/3219667)
	cmd := exec.Command("diff", "-arq", expectDir+"/", publicTestDir+"/")
	out, err := cmd.Output()
	if err != nil {
		gitDiffChanges(expectDir, publicTestDir)
	}
	assert.Equal(t, "", string(out))
	require.NoError(t, err)
}
