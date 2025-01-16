#!/bin/bash -e

# Prepare public directory
rm -rf public/
cp -R content/ public/
cp CNAME public/CNAME

# https://github.com/c-w/ghp-import/blob/5219f00fc83606ff426b978a9920ea746923dcb7/ghp_import.py#L157-L164
touch public/.nojekyll

# Run the first party code
go run .

# Minify web files with: github.com/tdewolff/minify/v2/cmd/minify
minify --recursive --output ./ ./public

# Create search index
pagefind --site ./public
