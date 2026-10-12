#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), verified native documentation generator.
set -eu
[ "$#" = 4 ] || { echo 'Usage: build-gi-docgen-host.sh DISTFILES HOST_PYTHON DOT NEW_WORK' >&2; exit 2; }
distfiles=$1 python=$2 dot=$3 work=$4
for item in "$distfiles" "$python" "$dot" "$work"; do
    case "$item" in /*) ;; *) echo 'Absolute paths required' >&2; exit 2;; esac
    case "$item" in *[!a-zA-Z0-9_./+-]*) echo 'Paths contain shell metacharacters' >&2; exit 2;; esac
done
[ -x "$python" ] && [ -x "$dot" ]
archive=$distfiles/gi_docgen-2026.1.tar.gz
[ "$(shasum -a 256 "$archive" | awk '{print $1}')" = 65ac3c4f2b4255d1c616fb8eae55139b6ca10071545ca2272759ffd2ccf2c7b5 ]
mkdir "$work"
"$python" --version > "$work/python-version.txt"
"$dot" -V > "$work/dot-version.txt" 2>&1
version=$(awk '{print $2}' "$work/python-version.txt" | cut -d. -f1,2)
tar -xf "$archive" -C "$work"
(cd "$work/gi_docgen-2026.1" && "$python" -m build --no-isolation --wheel) > "$work/build.log" 2>&1
set -- "$work"/gi_docgen-2026.1/dist/*.whl
[ "$#" = 1 ] && [ -f "$1" ]
"$python" -m installer --prefix "$work/prefix" "$1" > "$work/install.log" 2>&1
mv "$work/prefix/bin/gi-docgen" "$work/prefix/bin/gi-docgen.original"
cat > "$work/prefix/bin/gi-docgen" <<WRAPPER
#!/bin/sh
export PYTHONPATH='$work/prefix/lib/python$version/site-packages'
export PATH='$(dirname "$dot")':\$PATH
exec '$python' '$work/prefix/bin/gi-docgen.original' "\$@"
WRAPPER
chmod +x "$work/prefix/bin/gi-docgen"
[ "$("$work/prefix/bin/gi-docgen" --version)" = 2026.1 ]
# Generate a real SVG with the selected provider before accepting the helper.
printf '%s\n' 'digraph { generator -> documentation; }' | "$dot" -Tsvg > "$work/dot.svg"
grep -q '<svg' "$work/dot.svg"
shasum -a 256 "$archive" "$python" "$dot" "$work/prefix/bin/gi-docgen" "$work/prefix/bin/gi-docgen.original" > "$work/inputs-outputs.sha256"
echo 'PASS: native gi-docgen 2026.1 and selected Graphviz provider'
