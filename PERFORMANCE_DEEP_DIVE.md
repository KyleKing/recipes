# Performance Deep Dive: Why Is Pass 2 So Slow?

## Current Timing Breakdown (227 recipes)

```
[TIMING] Pass 1 (parse & cache): 88.59ms (227 recipes)
[TIMING] Pass 2a (git metadata): 4.60s         ← 33% of build time
[TIMING] Pass 2b (NLP processing): 9.02s       ← 65% of build time
[TIMING] Pass 2c (similarity calculations): 130ms
[TIMING] Pass 2 TOTAL: 13.75s
[TIMING] Pass 3 (generate HTML): 59.11ms
[TIMING] Total build time: 13.90s
```

**Total similarity comparisons**: 51,302 (227 recipes × 226 comparisons each)

## Root Causes

### 1. Git Metadata Extraction (4.6s - 33% of build time)

**Current approach**:
- Calls `git log` twice per recipe (creation date + modification date)
- 227 recipes × 2 = **454 subprocess spawns**
- Each git subprocess has ~10ms overhead

**Why it's slow**:
```go
// Called 227 times
func enrichRecipeWithGitInfo(recipe *Recipe, djFilePath string) {
    created, _ := getGitCreationDate(filePath)   // git log --diff-filter=A
    modified, _ := getGitModificationDate(filePath) // git log -1
}
```

**Solution**: Single git call for all files
```bash
# Instead of 454 calls, use 1:
git log --name-only --diff-filter=A --pretty=format:"%H %aI" -- content/**/*.dj
```

**Expected gain**: 4.6s → 0.1s (45x faster)

---

### 2. NLP Processing (9.0s - 65% of build time)

**Current approach**:
- Processes each recipe serially through spaCy NLP
- Each recipe's ingredients parsed individually
- CGO overhead for each call to C++/Python wrapper

**Why it's slow**:
```go
// Called 227 times serially
func extractIngredientsWithNLP(rawIngredients []string) map[string]bool {
    nlp := getNLP()  // Singleton, but still slow per-recipe processing
    for _, ingredient := range rawIngredients {
        chunks := nlp.GetNounChunks(cleaned)     // CGO call
        tokens := nlp.Tokenize(cleaned)          // CGO call
    }
}
```

**Solutions (multiple options)**:

#### Option A: Parallel NLP Processing
```go
func buildIngredientIndexParallel(publicDir string, rMap RecipeMap, cache *RecipeCache) IngredientIndex {
    // Process recipes in parallel with worker pool
    // Expected: 9s → 1-2s (4-8x speedup on multi-core)
}
```

#### Option B: Pre-computed Token Cache
```bash
# Store ingredient tokens in content/.recipe-cache/tokens.json
# Only reprocess recipes that changed since last build
# Expected: 9s → 0.5s for unchanged recipes
```

#### Option C: Simpler Tokenization (Feature Change)
```go
// Skip spaCy entirely, use simple word splitting
// Lose: noun phrases like "white beans" → ["white", "beans"]
// Gain: 9s → 0.1s (90x faster)
// Trade-off: Lower quality related recipe matches
```

---

### 3. Similarity Calculations (130ms - 1% of build time)

**Already fast!** 51,302 comparisons in 130ms = 2.5μs per comparison

No optimization needed here.

---

## Recommended Improvements by Impact

### High Impact, Low Risk

#### 1. Batch Git Metadata Extraction (RECOMMENDED FIRST)
- **Gain**: 4.6s → 0.1s (save 4.5 seconds)
- **Complexity**: Medium
- **Risk**: Low
- **Files**: goBuild/git_info.go

**Implementation**:
```go
func getAllGitDatesAtOnce(contentDir string) map[string]gitDates {
    // Single git log call, parse all dates at once
    // Return map[filePath]gitDates
}
```

#### 2. Parallel NLP Processing
- **Gain**: 9s → 1.5-2s (save 7 seconds)
- **Complexity**: Medium
- **Risk**: Medium (goroutine management, spaCy thread safety)
- **Files**: goBuild/related_recipes.go, goBuild/ingredients.go

**Combined impact**: 13.9s → 2.1s total build time (6.5x speedup)

---

### Medium Impact, Low Risk

#### 3. Ingredient Token Caching
- **Gain**: 9s → 0.5s on unchanged recipes (save 8.5 seconds for incremental builds)
- **Complexity**: Medium
- **Risk**: Low
- **Files**: New file content/.recipe-cache/tokens.json

**Implementation**:
```go
type TokenCache struct {
    FileHash string            `json:"file_hash"`
    Tokens   []string          `json:"tokens"`
    Updated  time.Time         `json:"updated"`
}

// Load cache, check file hashes, only reprocess changed recipes
```

**Use case**: Development workflow where only a few recipes change

---

### Feature Simplification Options

#### Option 1: Make Related Recipes Optional

Add build flag:
```bash
go run . --skip-related-recipes  # Skip Pass 2b and 2c entirely
```

**Gain**: 9.1s saved during development builds
**Trade-off**: No related recipes in output

#### Option 2: Category-Scoped Similarity

Only compare recipes within the same category:
```go
// Instead of 227 × 226 = 51,302 comparisons
// Do ~20 × 19 per category = ~4,000 comparisons total
```

**Gain**: 130ms → 10ms (not significant, but cleaner semantically)
**Trade-off**: Miss cross-category matches (e.g., "Chicken Tacos" won't match "Taco Seasoning")

#### Option 3: Simplify Tokenization

Replace spaCy with simple word splitting:
```go
func simpleTokenize(ingredient string) []string {
    // Remove quantities, split on whitespace, filter stopwords
    // No noun phrase extraction, no lemmatization
}
```

**Gain**: 9s → 0.1s
**Trade-off**:
- Lose multi-word phrases: "white beans" becomes ["white", "beans"]
- Lower quality matches
- Simpler to maintain, no C++ dependency

---

## Recommended Implementation Order

### Phase 1: Batch Git (PRIORITY 1)
**Why**: Biggest single improvement for lowest risk
- Save 4.5 seconds
- No feature trade-offs
- Simple to implement

### Phase 2: Parallel NLP (PRIORITY 2)
**Why**: Large gain, keeps feature quality
- Save 7 seconds
- Maintains spaCy quality
- Medium complexity

### Phase 3: Token Caching (PRIORITY 3)
**Why**: Optimize incremental builds
- Huge gain for development workflow
- Doesn't help first build, but makes rebuilds fast

**Combined result**:
- First build: 13.9s → 2.1s (6.5x faster)
- Incremental builds: 2.1s → 0.6s (23x faster than current)

---

## Alternative: Radical Simplification

If build speed is critical and feature quality less important:

### Remove spaCy Dependency Entirely
```bash
# Remove C++ wrapper, Python dependency
rm -rf lib/ setup-spacy.sh .go-spacy-build/
```

**Implementation**:
- Replace spaCy with simple Go word tokenizer
- Keep TF-IDF similarity calculations
- Accept lower quality related recipe matches

**Gain**:
- Build time: 13.9s → 5s (no NLP overhead)
- Setup: No C++ compilation, no Python spaCy model
- Simplicity: Pure Go, no CGO

**Trade-off**:
- "1 cup white beans" → ["cup", "white", "beans"] (lose noun phrases)
- More false positives in related recipes
- Less sophisticated matching

---

## Questions to Consider

1. **Is the related recipes feature worth the build time?**
   - Could it be pre-computed once and cached?
   - Is it used enough to justify 9+ seconds of build time?

2. **Is spaCy NLP necessary?**
   - Could simple tokenization + TF-IDF work well enough?
   - Users may not notice the difference in match quality

3. **How often are full rebuilds needed?**
   - If only for production deploys, 13s is acceptable
   - If during development, incremental caching would help

4. **What's the actual developer experience pain point?**
   - Waiting for full builds?
   - CI/CD time?
   - Something else?
