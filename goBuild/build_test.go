package goBuild

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"testing"

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
