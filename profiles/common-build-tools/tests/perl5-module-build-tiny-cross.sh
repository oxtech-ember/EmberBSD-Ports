#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake perl5-module-build-tiny-cross.sh PKGSRC MAKECONF TARGET_CC NEW_WORK
#
# Cross builds refused Module::Build::Tiny distributions because
# ExtUtils::Config and ExtUtils::Helpers read the host Config: the XS module
# took the host dlext and object suffix, InstallPaths took the host vendor
# directories and installed scripts named the host Perl. Require that the
# cross recipes accept Module::Build::Tiny and depend on the patched native
# helpers, then run Build.PL, Build and Build install with the host Perl and
# the target build context and require a target ELF module, the module and
# the script in the target vendor trees, and the target startperl.
set -eu
[ "$#" -eq 4 ] || { echo "Usage: $0 PKGSRC MAKECONF TARGET_CC NEW_WORK" >&2; exit 2; }
pkgsrc=$1 makeconf=$2 cc=$3
case "$4" in /*) ;; *) echo "$0: NEW_WORK must be absolute" >&2; exit 2;; esac
mkdir "$4"
work=$4
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
bm() { dir=$1; shift; MAKECONF=$makeconf "${BMAKE:-bmake}" -C "$pkgsrc/$dir" MAKECONF="$makeconf" "$@"; }
consumer=www/p5-HTTP-Daemon
set -- $(bm $consumer -V '${USE_CROSS_COMPILE:Uno:tl}' -V '${EMBERBSD_CROSS_BUILD_PERL}' \
	-V '${EMBERBSD_CROSS_BUILD_PYTHON}' -V '${EMBERBSD_PERL_TARGET_CONFIG}' \
	-V '${EMBERBSD_CROSS_SYSROOT}' -V '${DISTDIR}')
[ "$1" = yes ] || { echo "$0: select a MAKECONF for a cross build" >&2; exit 2; }
host=$2 python=$3 target=$4 sysroot=$5 distdir=$6
status=0
case "$(bm $consumer -V '${PKG_FAIL_REASON}')" in
*"Module::Build::Tiny"*) echo "FAIL: $consumer is refused as a cross Perl module"; status=1;;
esac
depends=" $(bm $consumer -V TOOL_DEPENDS) "
self=" $(bm devel/p5-Module-Build-Tiny -V TOOL_DEPENDS) "
for need in p5-ExtUtils-InstallPaths p5-CPAN-Requirements-Dynamic; do
	case "$self" in
	*" $need>="*) ;;
	*) echo "FAIL: cross Module::Build::Tiny does not build with native $need"; status=1;;
	esac
done
srcs=
for pkg in devel/p5-ExtUtils-Config devel/p5-ExtUtils-Helpers devel/p5-ExtUtils-InstallPaths devel/p5-Module-Build-Tiny; do
	set -- $(bm $pkg -V PKGNAME -V DISTNAME)
	case $pkg in
	*Config|*Helpers)
		case "$depends" in
		*" ${1%-*}>=${1##*-}:"*) ;;
		*) echo "FAIL: cross Module::Build::Tiny packages do not need native $1"; status=1;;
		esac;;
	esac
	tar -xzf "$distdir/$2.tar.gz" -C "$work"
	for p in "$pkgsrc/$pkg"/patches/patch-*; do
		[ -f "$p" ] && (cd "$work/$2" && patch -s -p0 < "$p")
	done
	srcs=$srcs${srcs:+:}$work/$2/lib
done
"$python" -B "$pkgsrc/lang/perl5/files/prepare-build-config.py" --host-perl "$host" \
	--target-config "$target" --sysroot "$sysroot" --cc "$cc" --ld "$cc" \
	--ar "${cc%clang}ar" --ranlib "${cc%clang}ranlib" --cflags=-O2 --ldflags= \
	--output "$work/config.json"
mkdir -p "$work/probe/lib" "$work/probe/script"
cp "$here/perl-xs/EmberProbe.xs" "$here/perl-xs/EmberProbe.pm" "$work/probe/lib/"
printf '#!perl\nuse EmberProbe;\n' > "$work/probe/script/ember-probe"
cat > "$work/probe/META.json" <<'JSON'
{"abstract":"probe","author":["EmberBSD"],"dynamic_config":0,
 "generated_by":"hand","license":["bsd"],
 "meta-spec":{"url":"http://search.cpan.org/perldoc?CPAN::Meta::Spec","version":2},
 "name":"EmberProbe","release_status":"stable","version":"0.01"}
JSON
printf 'use Module::Build::Tiny;\nBuild_PL();\n' > "$work/probe/Build.PL"
(
	cd "$work/probe"
	unset PERL5OPT PERL_MB_OPT
	PERL5LIB=$srcs EMBERBSD_PERL_BUILD_CONFIG=$work/config.json
	export PERL5LIB EMBERBSD_PERL_BUILD_CONFIG
	"$host" Build.PL --installdirs=vendor > build.log 2>&1 &&
	"$host" Build >> build.log 2>&1 &&
	"$host" Build install --destdir "$work/dest" >> build.log 2>&1
) || { echo "FAIL: Build.PL route stopped; see $work/probe/build.log"; exit 1; }
set -- $("$host" -MJSON::PP -e 'local $/; open my $f, "<", $ARGV[0] or die;
	my $c = decode_json(<$f>); print join " ", @$c{qw/installvendorarch installvendorlib installvendorscript/}' \
	"$work/config.json")
so=$work/dest$1/auto/EmberProbe/EmberProbe.so
if [ -f "$so" ]; then
	"$host" -e 'open my $f, "<:raw", $ARGV[0] or die; read $f, my $h, 20;
		my ($m, $c, $d) = unpack "a4 C C", $h; my $e = unpack "v", substr($h, 18, 2);
		exit !($m eq "\x7fELF" && $c == 2 && $d == 1 && $e == 183)' "$so" ||
		{ echo "FAIL: $so is not an aarch64 ELF module"; status=1; }
else
	echo "FAIL: no EmberProbe.so in the target vendor architecture tree"; status=1
fi
[ -f "$work/dest$1/EmberProbe.pm" ] || [ -f "$work/dest$2/EmberProbe.pm" ] ||
	{ echo "FAIL: EmberProbe.pm is not in a target vendor tree"; status=1; }
script=$work/dest$3/ember-probe
if [ -f "$script" ]; then
	want=$("$host" -MJSON::PP -e 'local $/; open my $f, "<", $ARGV[0] or die;
		print decode_json(<$f>)->{startperl}' "$work/config.json")
	[ "$(head -1 "$script")" = "$want" ] ||
		{ echo "FAIL: ember-probe starts with $(head -1 "$script"), not $want"; status=1; }
else
	echo "FAIL: ember-probe is not in the target vendor script directory"; status=1
fi
[ "$status" -eq 0 ] || exit 1
echo "PASS: cross Module::Build::Tiny builds a target XS module with the target Config"
