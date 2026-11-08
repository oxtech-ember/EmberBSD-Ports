#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake GMAKE=gmake netpbm-cross-scripts.sh PKGSRC MAKECONF
#
# The cross recipe omits the top-level manweb script. It passed SCRIPTS= on
# the make command line, which also emptied the script lists of the
# subdirectories, so anytopnm, pnmflip and the other PLIST scripts were not
# installed. Configure the recipe and evaluate SCRIPTS with the recipe's
# make flags at the top level and in converter/other and editor.
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 PKGSRC MAKECONF" >&2; exit 2; }
recipe=$1/graphics/netpbm makeconf=$2
work=$(cd "$(mktemp -d "${TMPDIR:-/tmp}/netpbm-scripts.XXXXXX")" && pwd -P)
trap 'rm -rf "$work"' EXIT
bm() {
	MAKECONF=$makeconf "${BMAKE:-bmake}" -C "$recipe" MAKECONF="$makeconf" \
	    WRKOBJDIR="$work/objects" SKIP_DEPENDS=yes "$@"
}
[ "$(bm -V '${USE_CROSS_COMPILE:Uno:tl}')" = yes ] ||
	{ echo "$0: select a MAKECONF for a cross build" >&2; exit 2; }
bm configure >"$work/configure.log" 2>&1 ||
	{ cat "$work/configure.log"; echo "FAIL: configure"; exit 1; }
wrksrc=$(bm -V '${WRKSRC}')
eval "set -- $(bm -V '${MAKE_FLAGS}')"
scripts() {
	dir=$1; shift
	"${GMAKE:-gmake}" -s -C "$wrksrc/$dir" -f "$wrksrc/$dir/$makefile" \
	    SRCDIR="$wrksrc" BUILDDIR="$wrksrc" "$@" \
	    --eval 'ember-scripts: ; @echo $(SCRIPTS)' ember-scripts
}
status=0
makefile=GNUmakefile
top=$(scripts . "$@")
case " $top " in *" manweb "*) echo "FAIL: top level installs manweb"; status=1 ;; esac
makefile=Makefile
for check in converter/other:anytopnm editor:pnmflip; do
	dir=${check%%:*} script=${check#*:}
	list=$(scripts "$dir" "$@")
	case " $list " in
	*" $script "*) ;;
	*) echo "FAIL: $dir does not install $script (SCRIPTS='$list')"; status=1 ;;
	esac
done
[ "$status" -eq 0 ] && echo "PASS: cross Netpbm installs its scripts except manweb"
exit "$status"
