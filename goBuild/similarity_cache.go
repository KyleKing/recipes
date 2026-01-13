package goBuild

import (
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"os"
	"path/filepath"
	"time"
)

const CACHE_DIR = ".recipe-cache"
const CACHE_FILE = "ingredient-tokens.json"

type CachedIngredientTokens struct {
	FilePath    string          `json:"file_path"`
	FileHash    string          `json:"file_hash"`
	Tokens      map[string]bool `json:"tokens"`
	Ingredients []string        `json:"ingredients"`
	CachedAt    time.Time       `json:"cached_at"`
}

type SimilarityCache struct {
	Version string                            `json:"version"`
	Recipes map[string]CachedIngredientTokens `json:"recipes"`
}

func getCacheFilePath() string {
	return filepath.Join(CACHE_DIR, CACHE_FILE)
}

func ensureCacheDir() error {
	return os.MkdirAll(CACHE_DIR, 0o755)
}

func computeFileHash(filePath string) (string, error) {
	file, err := os.Open(filePath)
	if err != nil {
		return "", err
	}
	defer file.Close()

	hash := sha256.New()
	if _, err := io.Copy(hash, file); err != nil {
		return "", err
	}

	return fmt.Sprintf("%x", hash.Sum(nil)), nil
}

func loadSimilarityCache() *SimilarityCache {
	cachePath := getCacheFilePath()

	data, err := os.ReadFile(cachePath)
	if err != nil {
		if !os.IsNotExist(err) {
			log.Printf("Warning: Failed to read cache file: %v", err)
		}
		return &SimilarityCache{
			Version: "1",
			Recipes: make(map[string]CachedIngredientTokens),
		}
	}

	var cache SimilarityCache
	if err := json.Unmarshal(data, &cache); err != nil {
		log.Printf("Warning: Failed to parse cache file: %v", err)
		return &SimilarityCache{
			Version: "1",
			Recipes: make(map[string]CachedIngredientTokens),
		}
	}

	return &cache
}

func saveSimilarityCache(cache *SimilarityCache) error {
	if err := ensureCacheDir(); err != nil {
		return fmt.Errorf("failed to create cache directory: %w", err)
	}

	cache.Version = "1"

	data, err := json.MarshalIndent(cache, "", "  ")
	if err != nil {
		return fmt.Errorf("failed to marshal cache: %w", err)
	}

	cachePath := getCacheFilePath()
	if err := os.WriteFile(cachePath, data, 0o644); err != nil {
		return fmt.Errorf("failed to write cache file: %w", err)
	}

	return nil
}

func isRecipeCacheValid(cached CachedIngredientTokens, djFilePath string) bool {
	// Check if file still exists
	if _, err := os.Stat(djFilePath); err != nil {
		return false
	}

	// Compute current file hash
	currentHash, err := computeFileHash(djFilePath)
	if err != nil {
		return false
	}

	// Compare hashes
	return cached.FileHash == currentHash
}
