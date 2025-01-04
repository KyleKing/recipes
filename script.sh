#!/bin/bash

find_and_replace() {
  for file in *dj; do
      new_content=$(cat "$file" | sed 's/::::::/\n:::\n:::/')
  echo -e "$new_content" > "$file"
  done
}

fd --extension=dj | sad --commit --flags=M '\{\% \[cts\] rating=(\d); \([^\%]+\%}\n+.+\n+\{\% \[cte\] \%}\n+\{\% \[cts\] name_image=([^;]+); \([^\%]+\%}\n+.+\n+\{\% \[cte\] \%}' '{ rating=$1 image="$2" }::::::'

find_and_replace
