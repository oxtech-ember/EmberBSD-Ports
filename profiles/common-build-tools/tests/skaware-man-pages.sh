#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). The skarnet packages install their man pages
# with the selected install tool instead of overriding it with GNU install.
set -eu
[ "$#" = 2 ] || { echo "Usage: $0 EXPORTED_PKGSRC NEW_WORK" >&2; exit 2; }
pkgsrc=$1 work=$2
: "${BMAKE:?Set the native BSD make executable}"
mkdir "$work"
for pkgpath in lang/execline misc/s6-portable-utils net/s6-networking \
    net/shibari sysutils/s6 www/tipidee; do
    "$BMAKE" -C "$pkgsrc/$pkgpath" -V '${SUBST_SED.skaman}' \
        > "$work/sed" 2> "$work/query.log" ||
        { cat "$work/query.log" >&2; echo "Cannot query $pkgpath" >&2; exit 1; }
done
# The install rules of the skarnet man page Makefiles.
mkdir -p "$work/src/man1" "$work/src/man7"
: > "$work/src/man1/a.1"; : > "$work/src/man1/b.1"; : > "$work/src/man7/c.7"
tab=$(printf '\t')
cat > "$work/src/Makefile" <<MAKEFILE
DESTDIR  =
MAN_DIR ?= /share/man
man1_dir = \$(MAN_DIR)/man1
man7_dir = \$(MAN_DIR)/man7
man1_targets = a.1 b.1
man7_targets = c.7
install:
${tab}cd man1; install -D -m 0644 -t \${DESTDIR}\${man1_dir} \$(man1_targets)
${tab}cd man7; install -D -m 0644 -t \${DESTDIR}\${man7_dir} \$(man7_targets)
MAKEFILE
eval "sed $(cat "$work/sed")" < "$work/src/Makefile" > "$work/src/Makefile.new"
mv "$work/src/Makefile.new" "$work/src/Makefile"
! grep -q 'install -D' "$work/src/Makefile" ||
    { echo 'GNU install options are left in the man page rules' >&2; exit 1; }
"$BMAKE" -C "$work/src" DESTDIR="$work/dest" install
for page in man1/a.1 man1/b.1 man7/c.7; do
    [ -f "$work/dest/share/man/$page" ] ||
        { echo "The $page man page is not installed" >&2; exit 1; }
done
echo 'PASS: the skarnet man pages install with the selected install tool.'
