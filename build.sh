#!/bin/bash -e

# Prepare public directory
rm -rf public/
cp -R content/ public/
rm public/_icons/*.sketch
cp CNAME public/CNAME

# https://github.com/c-w/ghp-import/blob/5219f00fc83606ff426b978a9920ea746923dcb7/ghp_import.py#L157-L164
touch public/.nojekyll

# Generate HTML from djot recipes
go run .

# Minify web files with: github.com/tdewolff/minify/v2/cmd/minify
minify --recursive --output ./ ./public

# Create search index
pagefind --site ./public
