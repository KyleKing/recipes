#!/bin/bash

fd --extension=dj | sad --commit --flags=M '\{\% \[cts\] rating=(\d); \([^\%]+\%}\n+.+\n+\{\% \[cte\] \%}\n+\{\% \[cts\] name_image=([^;]+); \([^\%]+\%}\n+.+\n+\{\% \[cte\] \%}' '{ rating=$1 image="$2" }::::::'

python - << EOT
from pathlib import Path

for pth in Path.cwd().rglob("*.dj"):
    print(pth)
    new = pth.read_text().replace("::::::", "\n:::\n:::")
    pth.write_text(new)
EOT
