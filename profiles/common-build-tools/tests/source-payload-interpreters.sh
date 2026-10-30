#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Source-only packages install upstream trees
# that consumers build with their own selected interpreters. Run the real
# pkgsrc interpreter check in cross mode on a staged payload: scripts inside
# the payload are accepted, and a script elsewhere in the package is still
# rejected. Builds and installs nothing.
# Usage: source-payload-interpreters.sh PKGSRC MAKECONF NEW_OUTPUT
set -eu
[ "$#" = 3 ] || { echo "Usage: $0 PKGSRC MAKECONF NEW_OUTPUT" >&2; exit 2; }
: "${BMAKE:?Set native bmake}"
pkgsrc=$1 conf=$2 out=$3
for path in "$@"; do
    case "$path" in /*) ;; *) echo 'Absolute paths required' >&2; exit 2 ;; esac
done
mkdir "$out"
out=$(CDPATH= cd -- "$out" && pwd -P)
fail() { echo "FAIL: $*" >&2; exit 1; }
script() { printf '#!%s\nexit 0\n' "$2" > "$1"; chmod 755 "$1"; }
count=0
for pair in devel/inspector-protocol:share/inspector-protocol \
    lang/llvm-libc-source:share/llvm-libc-source lang/v8:share/v8-source; do
    pkg=${pair%%:*} payload=${pair#*:} name=$(echo "$pkg" | tr / _)
    stage=$out/$name/stage prefix=$("$BMAKE" -C "$pkgsrc/$pkg" MAKECONF="$conf" \
        USE_CROSS_COMPILE=yes WRKOBJDIR="$out/$name/work" -V '${PREFIX}')
    mkdir -p "$stage$prefix/$payload/tools" "$stage$prefix/bin"
    script "$stage$prefix/$payload/tools/gen.py" '/usr/bin/env python3'
    script "$stage$prefix/$payload/tools/run.sh" /bin/bash
    printf '%s\n' "$payload/tools/gen.py" "$payload/tools/run.sh" > "$out/$name/PLIST"
    check() {
        "$BMAKE" -C "$pkgsrc/$pkg" MAKECONF="$conf" USE_CROSS_COMPILE=yes \
            CHECK_INTERPRETER=yes WRKOBJDIR="$out/$name/work" WRKDIR="$out/$name/check" \
            DESTDIR="$stage" PLIST="$out/$name/PLIST" "$@"
    }
    check makedirs > "$out/$name/makedirs.log" 2>&1
    check _check-interpreter > "$out/$name/payload.log" 2>&1 ||
        { cat "$out/$name/payload.log" >&2; fail "$pkg rejected scripts in its source payload"; }
    # The skip names only the payload: an executable outside it is still checked.
    script "$stage$prefix/bin/escape" '/usr/bin/env python3'
    echo bin/escape >> "$out/$name/PLIST"
    rm -rf "$out/$name/check"
    check makedirs > "$out/$name/makedirs2.log" 2>&1
    if check _check-interpreter > "$out/$name/outside.log" 2>&1; then
        fail "$pkg accepted /usr/bin/env outside $payload"
    fi
    grep -F "$prefix/bin/escape" "$out/$name/outside.log" > /dev/null ||
        fail "$pkg outside check failed for another reason"
    count=$((count + 1))
done
echo "PASS: $count source-only packages skip only their payload in the pkgsrc interpreter check"
