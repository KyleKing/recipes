package goBuild

import (
	"log"
	"os/exec"
	"strings"
	"sync"
	"time"
)

var (
	gitDateCache  map[string]gitDates
	gitCacheMutex sync.RWMutex
	gitCacheInit  sync.Once
)

type gitDates struct {
	created  time.Time
	modified time.Time
}

func initGitCache(contentDir string) {
	gitCacheInit.Do(func() {
		gitDateCache = make(map[string]gitDates)

		start := time.Now()

		// Get all modification dates in one call
		modDates := batchGetModificationDates(contentDir)

		// Get all creation dates in one call
		createDates := batchGetCreationDates(contentDir)

		// Merge results into cache
		allFiles := make(map[string]bool)
		for file := range modDates {
			allFiles[file] = true
		}
		for file := range createDates {
			allFiles[file] = true
		}

		for file := range allFiles {
			gitDateCache[file] = gitDates{
				created:  createDates[file],
				modified: modDates[file],
			}
		}

		log.Printf("Batch loaded git dates for %d files in %v", len(gitDateCache), time.Since(start))
	})
}

func batchGetModificationDates(contentDir string) map[string]time.Time {
	dates := make(map[string]time.Time)

	// Get last modification date for each file
	cmd := exec.Command("git", "log", "--name-only", "--pretty=format:%aI", "--", contentDir)
	output, err := cmd.Output()
	if err != nil {
		log.Printf("Warning: git log for modification dates failed: %v", err)
		return dates
	}

	lines := strings.Split(string(output), "\n")
	var currentDate time.Time

	for _, line := range lines {
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}

		// Try to parse as date
		if parsedDate, err := time.Parse(time.RFC3339, line); err == nil {
			currentDate = parsedDate
		} else if strings.HasPrefix(line, contentDir) {
			// It's a file path - record date if we don't have one yet
			if _, exists := dates[line]; !exists && !currentDate.IsZero() {
				dates[line] = currentDate
			}
		}
	}

	return dates
}

func batchGetCreationDates(contentDir string) map[string]time.Time {
	dates := make(map[string]time.Time)

	// Get creation date (first commit) for each file using --reverse
	cmd := exec.Command("git", "log", "--name-only", "--diff-filter=A", "--pretty=format:%aI", "--reverse", "--", contentDir)
	output, err := cmd.Output()
	if err != nil {
		log.Printf("Warning: git log for creation dates failed: %v", err)
		return dates
	}

	lines := strings.Split(string(output), "\n")
	var currentDate time.Time

	for _, line := range lines {
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}

		// Try to parse as date
		if parsedDate, err := time.Parse(time.RFC3339, line); err == nil {
			currentDate = parsedDate
		} else if strings.HasPrefix(line, contentDir) {
			// It's a file path - record date if we don't have one yet (first occurrence)
			if _, exists := dates[line]; !exists && !currentDate.IsZero() {
				dates[line] = currentDate
			}
		}
	}

	return dates
}

func getGitDatesWithCache(filePath string) (time.Time, time.Time) {
	gitCacheMutex.RLock()
	defer gitCacheMutex.RUnlock()

	if dates, exists := gitDateCache[filePath]; exists {
		return dates.created, dates.modified
	}

	return time.Time{}, time.Time{}
}

func enrichRecipeWithGitInfo(recipe *Recipe, djFilePath string) {
	created, modified := getGitDatesWithCache(djFilePath)
	recipe.createdAt = created
	recipe.modifiedAt = modified
}
