# recipes

Kyle and Alex's Personal Recipes

Documentation can be found on [GitHub (./docs)](./docs), [PyPi](https://pypi.org/project/recipes/), or [Hosted](https://recipes.kyleking.me/)!

## Experimental migration to djot

```sh
fd . docs/ --extension=md | xargs -I {} bash -c "(pandoc {} -f gfm -t json | npx @djot/djot -f pandoc -t djot --width 0) > {}.dj" {/}

fd --type=file | sad --exact --commit '\{' '{'
fd --type=file | sad --exact --commit '\}' '}'
fd --type=file | sad --exact --commit 'name\_image' 'name_image'

brew install rename
trash docs/**/*.md
fd . docs/ --extension=dj | rename 's/\.md\.dj$/.dj/'
```

Separately, had to remove escaped underscores from only comments. Could have likely found a more programmatic way, but ran:

```sh
fd --type=file | sad --exact --commit '\_' '_'
fd --type=file | sad --exact --commit '{{% {cte} %}}' '{% [cte] %}'
fd --type=file | sad --exact --commit '{cts}' '[cts]'
```
