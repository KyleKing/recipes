#!/bin/bash -e

rm -rf public/
cp -R docs/ public/

node build.js

rm public/_icons/*.sketch
cp CNAME public/CNAME

# https://github.com/c-w/ghp-import/blob/5219f00fc83606ff426b978a9920ea746923dcb7/ghp_import.py#L157-L164
touch public/.nojekyll
