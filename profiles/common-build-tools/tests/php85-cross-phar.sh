#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake GMAKE=gmake php85-cross-phar.sh PKGSRC MAKECONF NEW_WORK
#
# ext/phar/Makefile.frag runs PHP to make phar.php and phar.phar and prefers
# the sapi/cli/php the build has just linked. In a cross build that is a
# target executable, the build host could not run it and install stopped
# without bin/phar85.phar. Require that a cross lang/php85 depends on the
# native package of the same version as a tool and passes the TOOLBASE php
# as PHP_EXECUTABLE and PHP_PHARCMD_EXECUTABLE, and that a native build does
# not. Then run the upstream phar rules from the distfile with those values,
# a target ELF stand-in as sapi/cli/php and a native php stand-in, and
# require that phar.phar comes from the native php with the installed php
# as its interpreter line.
set -eu
[ "$#" -eq 3 ] || { echo "Usage: $0 PKGSRC MAKECONF NEW_WORK" >&2; exit 2; }
pkgsrc=$1 makeconf=$2 work=$3
[ ! -e "$work" ] || { echo "$0: $work exists" >&2; exit 2; }
pkg=$pkgsrc/lang/php85
bm() { MAKECONF=$makeconf "${BMAKE:-bmake}" -C "$pkg" MAKECONF="$makeconf" "$@"; }
[ "$(bm -V '${USE_CROSS_COMPILE:Uno:tl}')" = yes ] ||
	{ echo "$0: select a MAKECONF for a cross build" >&2; exit 2; }
status=0
toolbase=$(bm -V '${TOOLBASE}')
pkgname=$(bm -V '${PKGNAME}')
phpver=$(bm -V '${PHP_VER}')
native=$toolbase/bin/php$phpver
case " $(bm -V '${TOOL_DEPENDS}') " in
*" $pkgname:../../lang/php85 "*) ;;
*) echo "FAIL: no tool dependency on the native $pkgname"; status=1;;
esac
flags=" $(bm -V '${MAKE_FLAGS}') "
for v in PHP_EXECUTABLE PHP_PHARCMD_EXECUTABLE; do
	case $flags in *" $v=$native "*) ;;
	*) echo "FAIL: MAKE_FLAGS does not select $v=$native"; status=1;; esac
done
case " $(bm USE_CROSS_COMPILE=no -V '${TOOL_DEPENDS}') " in
*":../../lang/php85 "*) echo "FAIL: a native php85 depends on itself"; status=1;;
esac
case " $(bm USE_CROSS_COMPILE=no -V '${MAKE_FLAGS}') " in
*" PHP_EXECUTABLE="*|*" PHP_PHARCMD_EXECUTABLE="*)
	echo "FAIL: a native php85 overrides its own php"; status=1;;
esac
grep -qx 'bin/phar${PHP_VER}.phar' "$pkg/PLIST" ||
	{ echo "FAIL: PLIST lacks bin/phar\${PHP_VER}.phar"; status=1; }

distfile=$(bm -V '${DISTDIR}/${DISTFILES}')
wrksrc=$(bm -V '${WRKSRC:T}')
mkdir -p "$work/tool/bin"
tar -xJf "$distfile" -C "$work" "$wrksrc/ext/phar" "$wrksrc/build/shtool"
src=$work/$wrksrc
patch -s -d "$src" -p0 -N < "$pkg/patches/patch-ext_phar_Makefile.frag" >/dev/null ||
	{ echo "FAIL: patch-ext_phar_Makefile.frag does not apply"; exit 1; }
# The cross-linked php: present and executable, but not a host program.
mkdir -p "$src/sapi/cli"
printf '\177ELF\002\001\001\000' > "$src/sapi/cli/php"
chmod +x "$src/sapi/cli/php"
# The native php stand-in records each run and writes what the rules read.
cat > "$work/tool/bin/php$phpver" <<'STANDIN'
#!/bin/sh
echo "$*" >> "${0%/*}/runs"
out=
while [ "$#" -gt 0 ]; do
	case $1 in
	*/build_precommand.php) echo '<?php /* phar.php */';;
	-f) out=$2; shift;;
	-b) printf '#!%s\n' "$2" > "$out.bang";;
	esac
	shift
done
[ -z "$out" ] || { cat "$out.bang" > "$out"; rm -f "$out.bang"; }
STANDIN
chmod +x "$work/tool/bin/php$phpver"
set --
for w in $flags; do
	case $w in PHP_EXECUTABLE=*|PHP_PHARCMD_EXECUTABLE=*)
		set -- "$@" "${w%%=*}=$work/tool${w#*=$toolbase}";;
	esac
done
cat > "$work/Makefile" <<MK
top_srcdir = $src
top_builddir = $src
srcdir = $src/ext/phar
builddir = ext/phar
SAPI_CLI_PATH = sapi/cli/php
PHP_EXECUTABLE = \$(top_builddir)/\$(SAPI_CLI_PATH)
PHP_MODULES =
INSTALL_ROOT = /destdir
bindir = /usr/pkg/bin
program_prefix =
program_suffix = $phpver
EXEEXT =
include \$(srcdir)/Makefile.frag
MK
(cd "$src" && "${GMAKE:-gmake}" -f "$work/Makefile" ext/phar/phar.phar "$@" \
	>"$work/make.log" 2>&1) || true
[ -f "$src/ext/phar/phar.phar" ] ||
	{ echo "FAIL: no phar.phar, see $work/make.log"; exit 1; }
grep -q ' pack -f ext/phar/phar.phar ' "$work/tool/bin/runs" ||
	{ echo "FAIL: phar.phar does not come from the native php"; exit 1; }
[ "$(head -1 "$src/ext/phar/phar.phar")" = "#!/usr/pkg/bin/php$phpver" ] ||
	{ echo "FAIL: phar.phar does not start with #!/usr/pkg/bin/php$phpver"; exit 1; }
[ "$status" -eq 0 ] || exit 1
echo "PASS: cross php85 makes phar.phar with the native php"
