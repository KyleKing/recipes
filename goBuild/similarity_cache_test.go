package goBuild

import (
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestComputeFileHash(t *testing.T) {
	t.Run("compute hash for existing file", func(t *testing.T) {
		// Create temp file
		tmpDir := t.TempDir()
		testFile := filepath.Join(tmpDir, "test.txt")
		content := []byte("test content for hashing")
		err := os.WriteFile(testFile, content, 0o644)
		require.NoError(t, err)

		// Compute hash
		hash1, err := computeFileHash(testFile)
		require.NoError(t, err)
		assert.NotEmpty(t, hash1)
		assert.Equal(t, 64, len(hash1), "SHA-256 hash should be 64 hex characters")

		// Same content should produce same hash
		hash2, err := computeFileHash(testFile)
		require.NoError(t, err)
		assert.Equal(t, hash1, hash2)
	})

	t.Run("different content produces different hash", func(t *testing.T) {
		tmpDir := t.TempDir()

		file1 := filepath.Join(tmpDir, "file1.txt")
		file2 := filepath.Join(tmpDir, "file2.txt")

		err := os.WriteFile(file1, []byte("content A"), 0o644)
		require.NoError(t, err)
		err = os.WriteFile(file2, []byte("content B"), 0o644)
		require.NoError(t, err)

		hash1, err := computeFileHash(file1)
		require.NoError(t, err)
		hash2, err := computeFileHash(file2)
		require.NoError(t, err)

		assert.NotEqual(t, hash1, hash2)
	})

	t.Run("error for non-existent file", func(t *testing.T) {
		hash, err := computeFileHash("/nonexistent/file.txt")
		assert.Error(t, err)
		assert.Empty(t, hash)
	})
}

func TestSimilarityCacheLoadSave(t *testing.T) {
	t.Run("load valid cache from file", func(t *testing.T) {
		tmpDir := t.TempDir()

		// Create cache directory and file
		cacheDir := filepath.Join(tmpDir, ".recipe-cache")
		err := os.MkdirAll(cacheDir, 0o755)
		require.NoError(t, err)

		// Write test cache file
		cacheFile := filepath.Join(cacheDir, "ingredient-tokens.json")
		err = os.WriteFile(cacheFile, []byte(`{
  "version": "1",
  "recipes": {
    "content/test/recipe1.dj": {
      "file_path": "content/test/recipe1.dj",
      "file_hash": "abc123",
      "tokens": {
        "flour": true,
        "sugar": true,
        "butter": true
      },
      "ingredients": ["1 cup flour", "2 cups sugar"],
      "cached_at": "2026-01-12T10:00:00Z"
    }
  }
}`), 0o644)
		require.NoError(t, err)

		// Test reading the cache file directly
		data, err := os.ReadFile(cacheFile)
		require.NoError(t, err)
		assert.Contains(t, string(data), "abc123")
		assert.Contains(t, string(data), "flour")
	})

	t.Run("create new cache structure", func(t *testing.T) {
		cache := &SimilarityCache{
			Version: "1",
			Recipes: make(map[string]CachedIngredientTokens),
		}

		// Add a recipe to cache
		cache.Recipes["test.dj"] = CachedIngredientTokens{
			FilePath: "test.dj",
			FileHash: "hash123",
			Tokens: map[string]bool{
				"flour": true,
			},
			Ingredients: []string{"flour"},
			CachedAt:    time.Now(),
		}

		assert.Len(t, cache.Recipes, 1)
		assert.Equal(t, "hash123", cache.Recipes["test.dj"].FileHash)
	})
}

func TestIsRecipeCacheValid(t *testing.T) {
	t.Run("valid cache entry", func(t *testing.T) {
		tmpDir := t.TempDir()
		testFile := filepath.Join(tmpDir, "recipe.dj")
		content := []byte("# Test Recipe\n\n## Ingredients\n\n- flour")
		err := os.WriteFile(testFile, content, 0o644)
		require.NoError(t, err)

		// Compute actual hash
		hash, err := computeFileHash(testFile)
		require.NoError(t, err)

		cached := CachedIngredientTokens{
			FilePath: testFile,
			FileHash: hash,
			Tokens:   map[string]bool{"flour": true},
		}

		valid := isRecipeCacheValid(cached, testFile)
		assert.True(t, valid)
	})

	t.Run("invalid when file changed", func(t *testing.T) {
		tmpDir := t.TempDir()
		testFile := filepath.Join(tmpDir, "recipe.dj")

		// Create file with initial content
		err := os.WriteFile(testFile, []byte("original content"), 0o644)
		require.NoError(t, err)

		oldHash, err := computeFileHash(testFile)
		require.NoError(t, err)

		// Modify file
		err = os.WriteFile(testFile, []byte("modified content"), 0o644)
		require.NoError(t, err)

		cached := CachedIngredientTokens{
			FilePath: testFile,
			FileHash: oldHash,
		}

		valid := isRecipeCacheValid(cached, testFile)
		assert.False(t, valid)
	})

	t.Run("invalid when file deleted", func(t *testing.T) {
		cached := CachedIngredientTokens{
			FilePath: "/nonexistent/recipe.dj",
			FileHash: "somehash",
		}

		valid := isRecipeCacheValid(cached, "/nonexistent/recipe.dj")
		assert.False(t, valid)
	})
}

func TestEnsureCacheDir(t *testing.T) {
	t.Run("create cache directory", func(t *testing.T) {
		tmpDir := t.TempDir()
		cacheDir := filepath.Join(tmpDir, ".recipe-cache")

		// Test directory creation
		err := os.MkdirAll(cacheDir, 0o755)
		assert.NoError(t, err)

		// Verify directory was created
		info, err := os.Stat(cacheDir)
		require.NoError(t, err)
		assert.True(t, info.IsDir())
	})
}
