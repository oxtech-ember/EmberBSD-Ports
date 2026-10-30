#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
# A cross build gives REPLACE_BASH scripts the target Bash only when the
# package installs them. libvpx names bash:build and runs build/make/version.sh
# during the build; the target /usr/pkg/bin/bash does not exist on the build
# host, so vpx_version.h was never generated. Evaluates the exported
# replace-interpreter.mk block; does not build a package.
# Usage: cross-build-bash-scripts.sh BMAKE PREPARED_PKGSRC
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 BMAKE PREPARED_PKGSRC" >&2; exit 2; }
bmake=$1
tree=$(CDPATH= cd -- "$2" && pwd)
fail() { echo "FAIL: $*" >&2; exit 1; }
scratch=$(mktemp -d "${TMPDIR:-/tmp}/cross-build-bash.XXXXXX")
trap 'rm -rf "$scratch"' EXIT INT TERM

awk '/^\.if !empty\(REPLACE_BASH:M\*\)$/ {p=1} p {print} p && /^\.endif$/ {exit}' \
    "$tree/mk/configure/replace-interpreter.mk" > "$scratch/bash.mk"
grep -q 'REPLACE.sys-bash.new' "$scratch/bash.mk" ||
    fail 'replace-interpreter.mk has no REPLACE_BASH block'
q() { # q CROSS USE_TOOLS -> "interpreter|depends"
    "$bmake" -f "$scratch/bash.mk" REPLACE_BASH=script OPSYS=NetBSD \
        NATIVE_OPSYS=Darwin USE_CROSS_COMPILE="$1" USE_TOOLS="$2" \
        BASH=/host/bin/bash CROSS_LOCALBASE=/usr/pkg \
        -V '${REPLACE.sys-bash.new}|${DEPENDS:M*shells/bash}'
}
target='/usr/pkg/bin/bash|bash-[0-9]*:../../shells/bash'
[ "$(q yes 'gmake bash:build perl:build')" = '/host/bin/bash|' ] ||
    fail 'build-only (bash:build) scripts received the target Bash'
[ "$(q yes 'bash:pkgsrc')" = '/host/bin/bash|' ] ||
    fail 'build-only (bash:pkgsrc) scripts received the target Bash'
[ "$(q yes '')" = "$target" ] ||
    fail 'installed REPLACE_BASH scripts lost the target Bash'
[ "$(q yes 'bash:run')" = '/usr/pkg/bin/bash|' ] ||
    fail 'bash:run scripts lost the target Bash'
[ "$(q yes 'bash:build bash:run')" = '/usr/pkg/bin/bash|' ] ||
    fail 'a recipe with bash:run lost the target Bash'
[ "$(q no 'bash:build')" = '/host/bin/bash|' ] ||
    fail 'native builds changed'
# omxplayer installs a Bash launcher, so it names bash:run.
grep -q '^USE_TOOLS+=.*bash:run' "$tree/multimedia/omxplayer/Makefile" ||
    fail 'omxplayer installs a Bash launcher without bash:run'
echo 'PASS: cross build-only Bash scripts keep the host Bash'
