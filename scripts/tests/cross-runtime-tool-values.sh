#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
# Cross builds must not record build-host tool paths in installed files.
# Configure receives bare awk, grep, egrep and sed (libgcrypt-config,
# smistrip), and after installation the cross tool map replaces build-host
# tool paths with the NetBSD target programs: the configure shell (automake's
# SHELL line), the build-host Perl (aclocal and automake shebangs), the
# build-host grep, and the tools directory. Runs the exported make code on a
# scratch destdir; does not build a package.
# Usage: cross-runtime-tool-values.sh BMAKE PREPARED_PKGSRC
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 BMAKE PREPARED_PKGSRC" >&2; exit 2; }
bmake=$1
tree=$(CDPATH= cd -- "$2" && pwd)
replace=$tree/mk/tools/replace.mk
fail() { echo "FAIL: $*" >&2; exit 1; }
scratch=$(mktemp -d "${TMPDIR:-/tmp}/cross-runtime-tools.XXXXXX")
trap 'rm -rf "$scratch"' EXIT INT TERM

# The cross block of replace.mk, evaluated by itself.
awk '/^\.if \$\{USE_CROSS_COMPILE:tl\} == "yes" && \$\{OPSYS\} != \$\{NATIVE_OPSYS\}$/ {p=1}
    p {print} p && /^\.endif$/ {exit}' "$replace" > "$scratch/values.mk"
grep -q 'TOOLS_VALUE_GNU.grep' "$scratch/values.mk" ||
    fail 'replace.mk has no cross configure tool values'
v() { "$bmake" -f "$scratch/values.mk" OPSYS=NetBSD NATIVE_OPSYS=Darwin "$@"; }
[ "$(v USE_CROSS_COMPILE=yes -V '${TOOLS_VALUE_GNU.grep}|${TOOLS_VALUE_GNU.egrep}|${TOOLS_VALUE_GNU.awk}|${TOOLS_VALUE_GNU.sed}')" = \
    'grep|grep -E|awk|sed' ] || fail 'cross configure receives build-host tool paths'
[ "$(v USE_CROSS_COMPILE=no -V '${TOOLS_VALUE_GNU.grep:U}${TOOLS_VALUE_GNU.awk:U}${EMBER_CROSS_TOOL_MAP:U}')" = '' ] ||
    fail 'native builds lost their tool command lines or map tool paths'
[ "$(v USE_CROSS_COMPILE=yes TOOLS_VALUE_GNU.grep=/pkg/grep -V '${TOOLS_VALUE_GNU.grep}')" = /pkg/grep ] ||
    fail 'a package can no longer select its grep'

# The target Perl joins the map where a perl:run package uses it.
grep -q '^EMBER_CROSS_TOOL_MAP+=	${TOOLS_PATH.perl}=${PERL5} ${TOOLS_DIR}/bin/perl=${PERL5}$' "$replace" ||
    fail 'the target Perl is not in the cross tool map'
grep -q '^post-install: ember-cross-tool-paths$' "$replace" ||
    fail 'the cross tool map does not run after installation'
printf '%s\n' 'EMBER_CROSS_TOOL_MAP+=	/host/bin/perl=/usr/pkg/bin/perl' \
    ".include \"$scratch/values.mk\"" > "$scratch/map.mk"

d=$scratch/destdir/usr/pkg
mkdir -p "$d/bin" "$d/share"
printf '#!/host/bin/perl\nprint "x";\n' > "$d/bin/plain"
printf '#!/host/bin/perl -w\nprint "y";\n' > "$d/bin/flags"; chmod 755 "$d/bin/flags"
printf '#!/host/bin/perlx\n' > "$d/bin/other"
printf "%s\n" "  \$ENV{'SHELL'} = '/host/bin/mksh' if exists \$ENV{'DJDIR'};" > "$d/bin/automake"
printf '%s\n' 'echo "$x" | /host/gnu/bin/ggrep -F y' 'SED=/w/.tools/bin/sed' > "$d/bin/config"
printf 'a\000/host/bin/mksh\n' > "$d/share/binary"
"$bmake" -f "$scratch/map.mk" USE_CROSS_COMPILE=yes OPSYS=NetBSD NATIVE_OPSYS=Darwin \
    RUN= FIND=find GREP=grep SED=sed CAT=cat RM=rm \
    DESTDIR="$scratch/destdir" PREFIX=/usr/pkg TOOLS_DIR=/w/.tools \
    CONFIG_SHELL=/host/bin/mksh TOOLS_PATH.sh=/host/bin/mksh \
    TOOLS_PATH.grep=/host/gnu/bin/ggrep TOOLS_PATH.sed=/host/bin/nbsed \
    ember-cross-tool-paths >/dev/null
[ "$(head -1 "$d/bin/plain")" = '#!/usr/pkg/bin/perl' ] || fail 'host Perl shebang kept'
[ "$(head -1 "$d/bin/flags")" = '#!/usr/pkg/bin/perl -w' ] || fail 'Perl shebang flags lost'
[ "$(sed -n 2p "$d/bin/plain")" = 'print "x";' ] || fail 'script body changed'
[ "$(head -1 "$d/bin/other")" = '#!/host/bin/perlx' ] || fail 'another program rewritten'
[ "$(cat "$d/bin/automake")" = "  \$ENV{'SHELL'} = '/bin/sh' if exists \$ENV{'DJDIR'};" ] ||
    fail 'automake keeps the build-host configure shell'
[ "$(sed -n 1p "$d/bin/config")" = 'echo "$x" | /usr/bin/grep -F y' ] || fail 'build-host grep kept'
[ "$(sed -n 2p "$d/bin/config")" = 'SED=/usr/bin/sed' ] || fail 'tools directory path kept'
[ -x "$d/bin/flags" ] || fail 'the map dropped the file mode'
[ "$(od -An -c "$d/share/binary" | tr -d ' \n')" = 'a\0/host/bin/mksh\n' ] || fail 'a binary file was rewritten'
echo 'PASS: cross builds record target runtime tools, not build-host paths'
