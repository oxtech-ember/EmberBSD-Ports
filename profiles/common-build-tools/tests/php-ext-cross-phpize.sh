#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake php-ext-cross-phpize.sh PKGSRC MAKECONF NEW_WORK
#
# lang/php/ext.mk runs phpize and configures with --with-php-config. In a
# cross build both named the target prefix, /usr/pkg/bin/phpize85 and
# /usr/pkg/bin/php-config85, which the build host does not have, and every
# PHP extension stopped at configure with status 127. Require that a cross
# extension depends on the native php of the same version as a tool, runs
# its TOOLBASE phpize, gets the native php for build-time PHP runs, and
# configures with the target php-config from the buildlink tree, with the
# include paths in that tree and the target extension directory; a native
# build keeps the installed phpize and php-config. Then run the real
# phpize-module target of databases/php-pdo on ext/pdo from the distfile,
# with a native phpize stand-in under the TOOLBASE path and a target
# php-config made from the distfile's scripts/php-config.in.
set -eu
[ "$#" -eq 3 ] || { echo "Usage: $0 PKGSRC MAKECONF NEW_WORK" >&2; exit 2; }
pkgsrc=$1 makeconf=$2 work=$3
[ ! -e "$work" ] || { echo "$0: $work exists" >&2; exit 2; }
pkg=$pkgsrc/databases/php-pdo
bm() { MAKECONF=$makeconf "${BMAKE:-bmake}" -C "$pkg" MAKECONF="$makeconf" "$@"; }
[ "$(bm -V '${USE_CROSS_COMPILE:Uno:tl}')" = yes ] ||
	{ echo "$0: select a MAKECONF for a cross build" >&2; exit 2; }
mkdir -p "$work/tool/bin" "$work/src"
wrkdir=$work/wrk
status=0
fail() { echo "FAIL: $*"; status=1; }

bm WRKDIR="$wrkdir" -V '${TOOLBASE}' -V '${PREFIX}' -V '${PHP_VER}' \
	-V '${PHP_PKG_PREFIX}' -V '${PHP_VERSION}' -V '${PHP_API_VERS}' \
	-V '${PHP_EXTENSION_DIR}' -V '${PHPIZE}' -V '${PHP_CONFIG}' \
	-V '${BUILDLINK_DIR}' -V '${TOOL_DEPENDS}' -V '${CONFIGURE_ARGS}' \
	-V '${MAKE_FLAGS}' -V '${BUILDLINK_FILES.php85}' \
	-V '${DISTDIR}/${DISTFILES}' -V '${EXTRACT_ELEMENTS}' > "$work/values"
{
	IFS= read -r toolbase; IFS= read -r prefix; IFS= read -r phpver
	IFS= read -r phppkg; IFS= read -r phpversion; IFS= read -r apivers
	IFS= read -r extdir; IFS= read -r phpize; IFS= read -r phpconfig
	IFS= read -r buildlink; IFS= read -r tooldeps; IFS= read -r confargs
	IFS= read -r makeflags; IFS= read -r blfiles; IFS= read -r distfile
	IFS= read -r element
} < "$work/values"
case " $tooldeps " in
*" $phppkg>=$phpversion:../../lang/php$phpver "*) ;;
*) fail "no tool dependency on the native $phppkg>=$phpversion";;
esac
[ "$phpize" = "$toolbase/bin/phpize$phpver" ] ||
	fail "PHPIZE is $phpize, not the native $toolbase/bin/phpize$phpver"
case $phpconfig in
"$wrkdir"/*) ;;
*) fail "PHP_CONFIG is $phpconfig, not made in the work directory";;
esac
case " $confargs " in
*" --with-php-config=$phpconfig "*) ;;
*) fail "configure does not get --with-php-config=$phpconfig";;
esac
case " $makeflags " in
*" PHP_EXECUTABLE=$toolbase/bin/php$phpver "*) ;;
*) fail "build-time PHP runs do not use the native php";;
esac
case " $blfiles " in
*" bin/php-config$phpver "*) ;;
*) fail "the buildlink tree lacks the target bin/php-config$phpver";;
esac
nphpize=$(bm USE_CROSS_COMPILE=no -V '${PHPIZE}')
nprefix=$(bm USE_CROSS_COMPILE=no -V '${PREFIX}')
[ "$nphpize" = "$nprefix/bin/phpize$phpver" ] ||
	fail "a native extension does not run the installed phpize"
[ "$(bm USE_CROSS_COMPILE=no -V '${PHP_CONFIG}')" = "$nprefix/bin/php-config$phpver" ] ||
	fail "a native extension does not use the installed php-config"
case " $(bm USE_CROSS_COMPILE=no -V '${TOOL_DEPENDS}') " in
*":../../lang/php$phpver "*) fail "a native extension depends on a tool php";;
esac

# The extension source and the target php-config that the target php85
# installs, with the paths it records.
tar -xJf "$distfile" -C "$work/src" "$element" "${element%%/*}/scripts/php-config.in"
src=$work/src/$element
cfg=$work/src/${element%%/*}/scripts/php-config.in
patch -s -p0 -N "$cfg" < "$pkgsrc/lang/php$phpver/patches/patch-scripts_php-config.in" >/dev/null ||
	{ echo "FAIL: patch-scripts_php-config.in does not apply"; exit 1; }
mkdir -p "$buildlink/bin"
sed -e "s,@SED@,sed,g" -e "s,@prefix@,$prefix,g" -e "s,@exec_prefix@,$prefix,g" \
	-e "s,@includedir@,$prefix/include,g" -e "s,@PHP_API_VERS@,$apivers,g" \
	-e "s,@PHP_VERSION@,$phpversion,g" -e "s,@EXTENSION_DIR@,$prefix/$extdir,g" \
	-e "s,@program_suffix@,$phpver,g" -e "s,@PHP_INSTALLED_SAPIS@,cli,g" \
	-e "s,@[A-Za-z_]*@,,g" "$cfg" > "$buildlink/bin/php-config$phpver"
chmod +x "$buildlink/bin/php-config$phpver"
# The native phpize stand-in records where it runs and writes configure.
cat > "$work/tool/bin/phpize$phpver" <<'STANDIN'
#!/bin/sh
[ -r config.m4 ] || { echo "phpize: no config.m4 in $(pwd)" >&2; exit 1; }
pwd > "${0%/*}/runs"
echo '#!/bin/sh' > configure
STANDIN
chmod +x "$work/tool/bin/phpize$phpver"
case $phpize in
"$toolbase"/*) run=$work/tool${phpize#"$toolbase"};;
*) run=$phpize;;
esac
bm WRKDIR="$wrkdir" WRKSRC="$src" PHPIZE="$run" phpize-module \
	> "$work/phpize.log" 2>&1 ||
	{ sed 's/^/  /' "$work/phpize.log"; echo "FAIL: phpize-module stopped"; exit 1; }
[ "$(cat "$work/tool/bin/runs" 2>/dev/null)" = "$src" ] ||
	{ echo "FAIL: the native phpize did not run in $src"; exit 1; }
[ -x "$phpconfig" ] || { echo "FAIL: no $phpconfig"; exit 1; }
inc=$buildlink/include/php/$apivers
[ "$("$phpconfig" --include-dir)" = "$inc" ] ||
	fail "php-config --include-dir is not $inc"
case " $("$phpconfig" --includes) " in
*" -I$inc -I$inc/main -I$inc/TSRM -I$inc/Zend "*) ;;
*) fail "php-config --includes does not name $inc";;
esac
[ "$("$phpconfig" --extension-dir)" = "$prefix/$extdir" ] ||
	fail "php-config --extension-dir is not the target $prefix/$extdir"
[ "$("$phpconfig" --prefix)" = "$prefix" ] ||
	fail "php-config --prefix is not the target $prefix"
[ "$status" -eq 0 ] || exit 1
echo "PASS: cross PHP extensions run the native phpize with the target php-config"
