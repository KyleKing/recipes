# Build Performance Analysis and Optimization Plan

## Current State (228 recipes, 23MB content)

### Build Pipeline Overview

1. **Pass 1**: Parse .dj files, extract metadata, populate RecipeMap
2. **Pass 2**: Read files again, extract ingredients with NLP, calculate IDF, find related recipes
3. **Pass 3**: Read files third time, generate final HTML
4. Minify HTML/CSS/JS
5. Pagefind indexing

### Critical Performance Bottlenecks

#### 1. Triple Parse Problem (HIGH IMPACT)

**Issue**: Each .dj file is read and parsed 3 separate times:
- `parseDjotFiles()` (goBuild/build.go:228)
- `buildIngredientIndex()` (goBuild/related_recipes.go:78, lines 85-91)
- `generateRecipePages()` (goBuild/build.go:272, lines 277-283)

**Impact**: For 228 recipes, this means 684 file reads and Djot AST parsing operations.

**Solution**: Parse once, cache AST in memory

```go
// Proposed structure
type CachedRecipe struct {
    path       string
    ast        []djot_parser.TreeNode[djot_parser.DjotNode]
    ingredients []string
    metadata   Recipe
}

type RecipeCache struct {
    mu      sync.RWMutex
    recipes map[string]*CachedRecipe
}
```

**Expected improvement**: 66% reduction in file I/O and parsing operations

#### 2. Sequential Processing (HIGH IMPACT)

**Issue**:
- `filepath.Walk()` processes files sequentially
- NLP processing happens serially for each recipe
- Similarity calculations are serial

**Impact**: No CPU parallelization despite multi-core availability

**Solution**: Implement worker pool pattern

```go
// Proposed approach
func parallelParseDjotFiles(publicDir string, rMap RecipeMap, cache *RecipeCache) error {
    const numWorkers = runtime.NumCPU()

    filePaths := make(chan string, 100)
    errors := make(chan error, numWorkers)
    var wg sync.WaitGroup

    // Spawn workers
    for i := 0; i < numWorkers; i++ {
        wg.Add(1)
        go worker(filePaths, cache, rMap, errors, &wg)
    }

    // Walk directory and feed file paths to workers
    go func() {
        filepath.Walk(publicDir, func(path string, info os.FileInfo, err error) error {
            if filepath.Ext(path) == ".dj" {
                filePaths <- path
            }
            return nil
        })
        close(filePaths)
    }()

    wg.Wait()
    close(errors)

    // Check for errors
    for err := range errors {
        if err != nil {
            return err
        }
    }

    return nil
}
```

**Expected improvement**: Near-linear speedup with CPU core count (4-8x faster on typical machines)

#### 3. NLP Batch Processing (MEDIUM IMPACT)

**Issue**: Each recipe's ingredients are processed individually through spaCy NLP

**Current**: 228 separate NLP calls
**Solution**: Batch ingredients together

```go
func batchExtractIngredients(allIngredients [][]string) []map[string]bool {
    nlp := getNLP()
    results := make([]map[string]bool, len(allIngredients))

    // Process in batches of 50 recipes
    const batchSize = 50
    for i := 0; i < len(allIngredients); i += batchSize {
        end := i + batchSize
        if end > len(allIngredients) {
            end = len(allIngredients)
        }

        batch := allIngredients[i:end]
        // Process batch...
    }

    return results
}
```

**Expected improvement**: 20-30% faster NLP processing due to reduced CGO overhead

### Optimization Priority

#### Phase 1: AST Caching (Implement First)
- **Files to modify**: goBuild/build.go, goBuild/related_recipes.go
- **Complexity**: Medium
- **Risk**: Low
- **Expected gain**: 66% reduction in I/O

Implementation steps:
1. Create RecipeCache structure with sync.RWMutex
2. Modify parseDjotFiles() to populate cache
3. Update buildIngredientIndex() to read from cache
4. Update generateRecipePages() to read from cache
5. Add cache invalidation based on file modification time for incremental builds

#### Phase 2: Parallel Processing (Implement Second)
- **Files to modify**: goBuild/build.go, goBuild/ingredients.go
- **Complexity**: High
- **Risk**: Medium (need to handle concurrent map access)
- **Expected gain**: 4-8x speedup on multi-core systems

Implementation steps:
1. Replace filepath.Walk with worker pool pattern
2. Use sync.Map or mutex-protected RecipeMap
3. Parallelize NLP processing (per-recipe, not batch initially)
4. Add error aggregation across workers
5. Ensure deterministic output (sort keys before processing)

#### Phase 3: Incremental Builds (Future Enhancement)
- Track file modification times
- Only rebuild changed recipes
- Cache similarity calculations
- Store build artifacts with checksums

### Benchmarking Plan

Add timing instrumentation:

```go
// In Build()
start := time.Now()
log.Printf("Starting build for %d recipes...", len(rMap))

// After each phase
log.Printf("Phase 1 (parse): %v", time.Since(start))
parseTime := time.Since(start)

log.Printf("Phase 2 (ingredients): %v", time.Since(start))
ingredientTime := time.Since(start) - parseTime

log.Printf("Phase 3 (generate): %v", time.Since(start))
generateTime := time.Since(start) - ingredientTime - parseTime

log.Printf("Total build time: %v", time.Since(start))
```

### Memory Considerations

**Current**: Minimal memory usage, files parsed on-demand
**With caching**: Estimated 50-100MB for AST cache (228 recipes × ~200-400KB parsed AST)
**Trade-off**: Acceptable for build-time tool, significant performance gain

### Additional Optimizations (Lower Priority)

1. **String Builder**: Replace `+=` string concatenation with `strings.Builder`
2. **Buffer Pooling**: Use `sync.Pool` for byte buffers in HTML generation
3. **Similarity Calculation**: Parallelize the similarity score loop in `findRelatedRecipes()`
4. **Template Caching**: Cache compiled templ components
5. **File I/O**: Use `bufio.Reader` for large file reads

## Implementation Results

### Phase 1: AST Caching (COMPLETED)

**Implementation Date**: 2026-01-12

**Changes Made**:
- Added `RecipeCache` struct with thread-safe Get/Set methods (goBuild/schemas.go)
- Modified `parseDjotFiles()` to populate cache on first pass (goBuild/build.go:229)
- Updated `generateRecipePages()` to read from cache (goBuild/build.go:284)
- Updated `buildIngredientIndex()` to read from cache (goBuild/related_recipes.go:78)
- Added timing instrumentation to all build phases (goBuild/build.go:396)

**Build Timing (227 recipes)**:
```
Starting build for directory: /Users/kyleking/Developer/kyleking/recipes/public
[TIMING] Pass 1 (parse & cache): 75.89ms (227 recipes)
[TIMING] Pass 2 (ingredients & related): 14.55s
[TIMING] Pass 3 (generate HTML): 56.18ms
[TIMING] Index generation: 1.77ms
[TIMING] Total build time: 14.68s
```

**Performance Breakdown**:
- Pass 1: 0.5% of total time
- Pass 2: 99.1% of total time (NLP processing dominates)
- Pass 3: 0.4% of total time (cache hit rate: ~100%)

**Gains from Caching**:
- Pass 3 is now ~56ms instead of ~76ms + AST parsing overhead
- Eliminated redundant file reads (reduced from 681 to 227 file reads)
- Pass 3 speedup: Estimated 2-3x faster

**Test Results**: All tests passing with 63.6% coverage

### Next Steps

#### Phase 2: Parallel NLP Processing (RECOMMENDED)

Since Pass 2 (NLP) dominates at 99% of build time, parallelization would provide the biggest gains:

**Option 2A: Parallel per-recipe NLP** (Lower risk)
- Process each recipe's ingredients in parallel goroutines
- Expected gain: 4-8x speedup (on 8-core machine)
- Estimated total build time: 2-4 seconds

**Option 2B: Batch NLP processing** (Medium risk)
- Group ingredients into batches of 50 recipes
- Process batches in parallel
- Reduce CGO overhead
- Expected gain: 5-10x speedup
- Estimated total build time: 1.5-3 seconds

**Implementation complexity**: Medium-High
**Risk**: Medium (need careful goroutine management)
**Files to modify**: goBuild/ingredients.go, goBuild/related_recipes.go

#### Phase 3: Parallel Similarity Calculations (Optional)

After NLP optimization, similarity calculations in `findRelatedRecipes()` could be parallelized:
- Expected gain: 10-20% additional speedup
- Lower priority since NLP currently dominates

#### Phase 4: Incremental Builds (Future)

If full builds are still slow after parallelization:
- Track file modification times
- Only rebuild changed recipes
- Cache similarity calculations

## Measurement Baseline

Profiling commands for deeper analysis:

```bash
# Measure current build time
time mise run build

# Profile CPU usage
go build -o build-profiled ./
./build-profiled -cpuprofile=cpu.prof
go tool pprof cpu.prof

# Profile memory
./build-profiled -memprofile=mem.prof
go tool pprof mem.prof
```

## Summary

**Phase 1 Status**: ✅ Complete
- AST caching successfully eliminates redundant file I/O
- Build pipeline is now instrumented with detailed timing
- Tests passing, no regressions

**Key Finding**: NLP processing is the clear bottleneck (99% of build time)

**Recommended Next Action**: Implement Phase 2 (parallel NLP processing) for 4-8x speedup
