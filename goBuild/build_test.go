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

// updateSnapshots replaces test_expected/ with actual build output on mismatch.
// The test still fails; set FREEZE_SNAPSHOTS=1 to skip the update entirely.
func updateSnapshots(expectDir, publicTestDir string) {
	os.RemoveAll(expectDir)
	cmd := exec.Command("cp", "-R", publicTestDir+"/", expectDir+"/")
	if out, err := cmd.Output(); err != nil {
		fmt.Println("Error updating snapshots:", cmd, out, err)
	}
	fmt.Println("Snapshots updated — review with git diff before committing")
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

func TestValidateInternalLinks(t *testing.T) {
	publicDir := t.TempDir()
	require.NoError(t, os.MkdirAll(filepath.Join(publicDir, "main"), 0o755))
	require.NoError(t, os.WriteFile(filepath.Join(publicDir, "main", "target.html"), []byte("ok"), 0o644))
	require.NoError(t, os.WriteFile(filepath.Join(publicDir, "main", "photo.jpg"), []byte("ok"), 0o644))

	write := func(t *testing.T, body string) {
		t.Helper()
		require.NoError(t, os.WriteFile(filepath.Join(publicDir, "main", "page.html"), []byte(body), 0o644))
	}

	t.Run("resolvable references pass", func(t *testing.T) {
		write(t, `<a href="target.html">x</a><a href="/main/target.html">y</a><img src="photo.jpg"/>`)
		assert.NoError(t, validateInternalLinks(publicDir))
	})

	t.Run("off-site and generated references are skipped", func(t *testing.T) {
		write(t, `<a href="https://example.com/missing.html">x</a><a href="#anchor">y</a>`+
			`<a href="mailto:a@b.c">z</a><script src="/pagefind/pagefind.js"></script>`)
		assert.NoError(t, validateInternalLinks(publicDir))
	})

	t.Run("missing relative href fails", func(t *testing.T) {
		write(t, `<a href="gone.html">x</a>`)
		err := validateInternalLinks(publicDir)
		require.Error(t, err)
		assert.Contains(t, err.Error(), "gone.html")
	})

	t.Run("missing root-relative href fails", func(t *testing.T) {
		write(t, `<a href="/main/gone.html">x</a>`)
		err := validateInternalLinks(publicDir)
		require.Error(t, err)
		assert.Contains(t, err.Error(), "/main/gone.html")
	})

	t.Run("missing image src fails", func(t *testing.T) {
		write(t, `<img src="/main/None.jpeg"/>`)
		err := validateInternalLinks(publicDir)
		require.Error(t, err)
		assert.Contains(t, err.Error(), "None.jpeg")
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
		detailedDiff := getDetailedDiff(expectDir, publicTestDir)
		if os.Getenv("FREEZE_SNAPSHOTS") != "1" {
			updateSnapshots(expectDir, publicTestDir)
		}
		t.Errorf("Build output differs from expected:\n%s\nDetailed differences:\n%s", string(out), detailedDiff)
	}
	assert.Equal(t, "", string(out), "Build output should match expected (run 'git diff' to see changes)")
	require.NoError(t, err, "Build verification failed - see detailed diff above")
}

// getDetailedDiff runs unified diff on directories to show actual differences
func getDetailedDiff(expectDir, publicTestDir string) string {
	// Run unified diff to show actual content differences
	cmd := exec.Command("diff", "-ur", expectDir+"/", publicTestDir+"/")
	out, _ := cmd.Output()

	if len(out) == 0 {
		return "No detailed differences found"
	}

	// Limit output to first 5000 characters to avoid overwhelming test output
	maxLen := 5000
	result := string(out)
	if len(result) > maxLen {
		result = result[:maxLen] + fmt.Sprintf("\n... (truncated, %d more characters)", len(result)-maxLen)
	}

	return result
}
