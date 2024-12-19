#!/bin/bash -e

rm -rf public/
cp -R docs/ public/

# 50x faster, but pending https://github.com/sivukhin/godjot/issues/11
go install github.com/sivukhin/godjot@latest

files=$(find ./public -type f -name "*.dj")
for file in $files; do
    html_path=${file%.dj}.html
    cat templates/header.html > "$html_path"

    # (npx --yes @djot/djot@0.3.2 -f djot -t html "$file" | sed 's/ disabled=""//g') >> "$html_path"
    (godjot -from "$file" -to -) >> "$html_path"

    cat templates/footer.html >> "$html_path"
done

rm public/_icons/*.sketch
rm public/index.dj
rm public/**/*.dj
cp CNAME public/CNAME
