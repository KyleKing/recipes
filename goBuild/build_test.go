package goBuild

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"

	"testing"

	"github.com/KyleKing/recipes/goBuild/testUtils"
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

	fmt.Println("cp", "-R", contentTestDir, publicTestDir)
	cmd := exec.Command("cp", "-R", contentTestDir, publicTestDir)
	stdout, err := cmd.Output()
	if err != nil {
		return "", err
	}
	fmt.Println(string(stdout))

	return publicTestDir, nil
}

func TestReplaceDjWithHtml(t *testing.T) {
	publicTestDir, err := initTestDir()
	require.NoError(t, err)
	expectDir := filepath.Join(filepath.Dir(publicTestDir), "test_expected")

	Build(publicTestDir)

	validateFiles := func(path string, fileInfo os.FileInfo, inpErr error) error {
		// Only compare files
		stat, err := os.Stat(path)
		require.NoError(t, err)
		if !(stat.Mode().IsRegular()) {
			return nil
		}

		rel, err := filepath.Rel(publicTestDir, path)
		require.NoError(t, err)
		expectedPath := filepath.Join(expectDir, rel)
		same, err := testUtils.FileCmp(path, expectedPath, 0)
		fmt.Println(rel)
		assert.Equal(t, err, nil, fmt.Sprintf("Error comparing files %s", rel))
		assert.Equal(t, same, true, fmt.Sprintf("Error: use git to diff %s", rel))
		return nil
	}
	err = filepath.Walk(publicTestDir, validateFiles)
	require.NoError(t, err)
}
