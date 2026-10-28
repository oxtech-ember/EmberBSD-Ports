#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Emacs builds without native compilation
# by default, so it needs no GCC libgccjit with the Clang toolchain.
set -eu
[ "$#" = 1 ] || { echo "Usage: $0 EXPORTED_PKGSRC" >&2; exit 2; }
pkgsrc=$1
bmake=${BMAKE:-bmake}
fail=0
for pkgpath in editors/emacs29 editors/emacs30 editors/emacs31; do
    options=$("$bmake" -C "$pkgsrc/$pkgpath" show-var VARNAME=PKG_OPTIONS) ||
        { echo "Cannot query $pkgpath" >&2; exit 1; }
    case " $options " in
        *' libgccjit '*) echo "$pkgpath enables libgccjit by default" >&2; fail=1 ;;
    esac
    deps=$("$bmake" -C "$pkgsrc/$pkgpath" show-depends-pkgpaths) ||
        { echo "Cannot query $pkgpath" >&2; exit 1; }
    if printf '%s\n' "$deps" | grep -E '^lang/gcc[0-9]'; then
        echo "$pkgpath depends on a GCC package" >&2; fail=1
    fi
done
[ "$fail" = 0 ]
echo 'PASS: emacs29, emacs30 and emacs31 build without native compilation.'
