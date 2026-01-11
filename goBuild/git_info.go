package goBuild

import (
	"fmt"
	"log"
	"os/exec"
	"strings"
	"sync"
	"time"
)

var (
	gitDateCache  = make(map[string]gitDates)
	gitCacheMutex sync.RWMutex
)

type gitDates struct {
	created  time.Time
	modified time.Time
}

func getGitCreationDate(filePath string) (time.Time, error) {
	cmd := exec.Command("git", "log", "--diff-filter=A", "--format=%aI", "--", filePath)
	output, err := cmd.Output()
	if err != nil {
		return time.Time{}, fmt.Errorf("git creation date command failed: %w", err)
	}

	dateStr := strings.TrimSpace(string(output))
	if dateStr == "" {
		return time.Time{}, fmt.Errorf("no creation date found for %s", filePath)
	}

	lines := strings.Split(dateStr, "\n")
	lastLine := lines[len(lines)-1]

	createdAt, err := time.Parse(time.RFC3339, lastLine)
	if err != nil {
		return time.Time{}, fmt.Errorf("failed to parse creation date: %w", err)
	}

	return createdAt, nil
}

func getGitModificationDate(filePath string) (time.Time, error) {
	cmd := exec.Command("git", "log", "-1", "--format=%aI", "--", filePath)
	output, err := cmd.Output()
	if err != nil {
		return time.Time{}, fmt.Errorf("git modification date command failed: %w", err)
	}

	dateStr := strings.TrimSpace(string(output))
	if dateStr == "" {
		return time.Time{}, fmt.Errorf("no modification date found for %s", filePath)
	}

	modifiedAt, err := time.Parse(time.RFC3339, dateStr)
	if err != nil {
		return time.Time{}, fmt.Errorf("failed to parse modification date: %w", err)
	}

	return modifiedAt, nil
}

func getGitDatesWithCache(filePath string) (time.Time, time.Time) {
	gitCacheMutex.RLock()
	if dates, exists := gitDateCache[filePath]; exists {
		gitCacheMutex.RUnlock()
		return dates.created, dates.modified
	}
	gitCacheMutex.RUnlock()

	created, createdErr := getGitCreationDate(filePath)
	if createdErr != nil {
		log.Printf("Warning: Failed to get git creation date for %s: %v", filePath, createdErr)
		created = time.Time{}
	}

	modified, modifiedErr := getGitModificationDate(filePath)
	if modifiedErr != nil {
		log.Printf("Warning: Failed to get git modification date for %s: %v", filePath, modifiedErr)
		modified = time.Time{}
	}

	gitCacheMutex.Lock()
	gitDateCache[filePath] = gitDates{created: created, modified: modified}
	gitCacheMutex.Unlock()

	return created, modified
}

func enrichRecipeWithGitInfo(recipe *Recipe, djFilePath string) {
	created, modified := getGitDatesWithCache(djFilePath)
	recipe.createdAt = created
	recipe.modifiedAt = modified
}
