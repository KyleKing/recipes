#!/bin/bash -e

rm -rf public/
cp -R docs/ public/

files=$(find ./public -type f -name "*.dj")
for file in $files; do
    html_path=${file%.dj}.html
    cat templates/header.html > "$html_path"
    (npx --yes @djot/djot@0.3.2 -f djot -t html "$file" | sed 's/ disabled=""//g') >> "$html_path"
    cat templates/footer.html >> "$html_path"
done

rm public/**/*.dj
