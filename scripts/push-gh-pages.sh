#!/bin/bash -e

# Create a clean history
git checkout --orphan gh-pages
git reset .
git clean --force -d

# Move files to top-level
cd public && cp -r . .. && cd ..
rm -rf public/

# Push to gh-pages branch
git add .
git status
git commit --message="build"
git push -u origin gh-pages --force
