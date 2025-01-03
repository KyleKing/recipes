#!/bin/bash -e

if [ -n "$GITHUB_ACTIONS" ]; then
    echo "'templ generate' is expected to be up to date when run in GitHub Actions"
else
    templ generate
fi

rm -rf public/
cp -R docs/ public/
rm public/_icons/*.sketch

go run .

# Using: github.com/tdewolff/minify/v2/cmd/minify
minify --recursive --output ./ ./public

# Initialize search index
npm run pagefind

cp CNAME public/CNAME

# https://github.com/c-w/ghp-import/blob/5219f00fc83606ff426b978a9920ea746923dcb7/ghp_import.py#L157-L164
touch public/.nojekyll
