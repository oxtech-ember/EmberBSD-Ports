#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Python bytecode is a host build product and must not be published.
set -eu
[ "$#" -le 1 ] || { echo "Usage: $0 [PORTS_REPOSITORY]" >&2; exit 2; }
root=${1:-$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)}
tracked=$(git -C "$root" ls-files -- '*.pyc' '*.pyo' '*/__pycache__/*')
[ -z "$tracked" ] || { printf 'Tracked Python bytecode:\n%s\n' "$tracked" >&2; exit 1; }
# Ignore the user's excludes so only the repository rules are tested.
for path in profiles/tests/__pycache__/probe.cpython-315.pyc scripts/probe.pyc scripts/probe.pyo; do
    git -C "$root" -c core.excludesFile=/dev/null check-ignore -q --no-index -- "$path" || {
        echo "Python bytecode is not ignored: $path" >&2; exit 1;
    }
done
echo 'PASS: Python bytecode is ignored and untracked'
