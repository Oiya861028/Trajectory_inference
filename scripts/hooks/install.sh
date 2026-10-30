#!/bin/bash
# Symlink the tracked hooks into .git/hooks, which git does not version.
#
# Run once per clone:
#     bash scripts/hooks/install.sh
#
# Uninstall:
#     rm .git/hooks/pre-commit
set -eu
PROJ="$(git rev-parse --show-toplevel)"
for h in "$PROJ"/scripts/hooks/*; do
    name="$(basename "$h")"
    [ "$name" = "install.sh" ] && continue
    [ "$name" = "README.md" ] && continue
    chmod +x "$h"
    ln -sf "../../scripts/hooks/$name" "$PROJ/.git/hooks/$name"
    echo "installed $name -> scripts/hooks/$name"
done
