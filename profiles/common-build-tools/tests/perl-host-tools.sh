#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Cross Perl defaults its build-host tools
# to the selected versioned native package while retaining explicit overrides.
# Usage: perl-host-tools.sh BMAKE HOST_PERL HOST_PYTHON NEW_OUTPUT
set -eu
[ "$#" = 4 ] || { echo "Usage: $0 BMAKE HOST_PERL HOST_PYTHON NEW_OUTPUT" >&2; exit 2; }
bmake=$1 hostperl=$2 hostpython=$3 work=$4
case "$bmake$hostperl$hostpython$work" in *[!A-Za-z0-9_./+-]*) echo 'Use simple paths.' >&2; exit 2 ;; esac
case "$work" in /*) ;; *) echo 'NEW_OUTPUT must be absolute' >&2; exit 2 ;; esac
[ ! -e "$work" ] || { echo "$work exists" >&2; exit 2; }
ports=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd -P)
recipe=$ports/pkgsrc/lang/perl5
version=$(sed -n 's/^DISTNAME=[[:space:]]*perl-//p' "$recipe/Makefile.common" | head -n 1)
[ -n "$version" ] || { echo 'Could not read Perl recipe version' >&2; exit 1; }
mkdir -p "$work/prefix/libexec/perl5/$version" "$work/override path"
ln -s "$hostperl" "$work/prefix/libexec/perl5/$version/miniperl"
cat > "$work/prefix/libexec/perl5/$version/generate_uudmap" <<'EOF'
#!/bin/sh
exit 0
EOF
chmod +x "$work/prefix/libexec/perl5/$version/generate_uudmap"
ln -s "$hostperl" "$work/override path/miniperl"
cat > "$work/override path/generate_uudmap" <<'EOF'
#!/bin/sh
exit 0
EOF
chmod +x "$work/override path/generate_uudmap"
cat > "$work/override path/wrong-miniperl" <<'EOF'
#!/bin/sh
printf '%s\n' invoked > "$PERL_WRONG_MARKER"
printf 5.043000
EOF
chmod +x "$work/override path/wrong-miniperl"
cat > "$work/Makefile" <<'EOF'
INSTALLATION_DIRS=bin
.include "${CROSS_MK}"
.include "${HOST_TOOLS_MK}"
EOF
common_vars="OPSYS=NetBSD MACHINE_ARCH=aarch64 MACHINE_PLATFORM=NetBSD-11.0-aarch64 \
    USE_CROSS_COMPILE=yes TOOLBASE=$work/prefix PKGVERSION_NOREV=$version \
    DISTNAME=perl-$version PKG_OPTIONS=perl-64bitauto,threads SED=/usr/bin/sed \
    EMBERBSD_CROSS_BUILD_PERL=$hostperl EMBERBSD_CROSS_BUILD_PYTHON=$hostpython \
    EMBERBSD_CROSS_SYSROOT=$work/sysroot CROSS_DESTDIR=$work/sysroot \
    TOOLDIR=$work/tools PREFIX=$work/prefix FILESDIR=$recipe/files \
    WRKSRC=$work/source WRKDIR=$work/wrk"
value() {
    variable=$1
    shift
    # Deliberate word splitting expands the make assignments in common_vars.
    # shellcheck disable=SC2086
    CROSS_MK=$recipe/cross.mk HOST_TOOLS_MK=$recipe/host-tools.mk \
        "$bmake" -f "$work/Makefile" $common_vars "$@" -v "$variable"
}
run_pre_configure() {
    # Deliberate word splitting expands the make assignments in common_vars.
    # shellcheck disable=SC2086
    CROSS_MK=$recipe/cross.mk HOST_TOOLS_MK=$recipe/host-tools.mk \
        "$bmake" -f "$work/Makefile" $common_vars "$@" pre-configure
}
expected_miniperl=$work/prefix/libexec/perl5/$version/miniperl
expected_generate=$work/prefix/libexec/perl5/$version/generate_uudmap
[ "$(value EMBERBSD_PERL_HOST_MINIPERL)" = "$expected_miniperl" ] ||
    { echo 'Cross Perl did not select the installed versioned miniperl' >&2; exit 1; }
[ "$(value EMBERBSD_PERL_HOST_GENERATE)" = "$expected_generate" ] ||
    { echo 'Cross Perl did not select the installed native generator' >&2; exit 1; }
cross_tools=$(value TOOL_DEPENDS)
case "$cross_tools" in *'perl>=5.44.0nb13:../../lang/perl5'*) ;;
*) echo "Cross Perl does not require the native helper package revision: $cross_tools" >&2; exit 1 ;;
esac
args=$(value CONFIGURE_ARGS)
case "$args" in *"-Dhostperl=$expected_miniperl"*"-Dhostgenerate=$expected_generate"*) ;;
*) echo "Configure arguments do not use both selected tools: $args" >&2; exit 1 ;;
esac
target_hosttools=$(value PLIST.hosttools)
[ -z "$target_hosttools" ] || { echo "Cross Perl packaged host-only tools: $target_hosttools" >&2; exit 1; }
target_dirs=$(value INSTALLATION_DIRS)
[ "$target_dirs" = bin ] || { echo "Cross Perl added native tool install dirs: $target_dirs" >&2; exit 1; }
native_hosttools=$(value PLIST.hosttools USE_CROSS_COMPILE=no)
[ "$native_hosttools" = yes ] || { echo "Native Perl did not add host tools to PLIST: $native_hosttools" >&2; exit 1; }
native_dirs=$(value INSTALLATION_DIRS USE_CROSS_COMPILE=no)
[ "$native_dirs" = "bin libexec/perl5/$version" ] ||
    { echo "Native Perl did not create the versioned libexec dir: $native_dirs" >&2; exit 1; }
override_miniperl="$work/override path/miniperl"
override_generate="$work/override path/generate_uudmap"
[ "$(value EMBERBSD_PERL_HOST_MINIPERL "EMBERBSD_PERL_HOST_MINIPERL=$override_miniperl" "EMBERBSD_PERL_HOST_GENERATE=$override_generate")" = "$override_miniperl" ] ||
    { echo 'Explicit miniperl override was lost' >&2; exit 1; }
[ "$(value EMBERBSD_PERL_HOST_GENERATE "EMBERBSD_PERL_HOST_MINIPERL=$override_miniperl" "EMBERBSD_PERL_HOST_GENERATE=$override_generate")" = "$override_generate" ] ||
    { echo 'Explicit generator override was lost' >&2; exit 1; }
missing_generate=$work/not-installed-yet/generate_uudmap
[ "$(value EMBERBSD_PERL_HOST_GENERATE EMBERBSD_PERL_HOST_GENERATE=$missing_generate)" = "$missing_generate" ] ||
    { echo 'Metadata query depends on installed host generator' >&2; exit 1; }
missing_reason=$(value PKG_FAIL_REASON EMBERBSD_PERL_HOST_GENERATE=$missing_generate)
[ -z "$missing_reason" ] ||
    { echo "Missing helper was rejected during metadata evaluation: $missing_reason" >&2; exit 1; }
wrong_miniperl="$work/override path/wrong-miniperl"
wrong_marker=$work/wrong-miniperl-invoked
rm -f "$wrong_marker"
[ "$(value EMBERBSD_PERL_HOST_MINIPERL "EMBERBSD_PERL_HOST_MINIPERL=$wrong_miniperl" "PERL_WRONG_MARKER=$wrong_marker")" = "$wrong_miniperl" ] ||
    { echo 'Metadata query lost an explicit miniperl override' >&2; exit 1; }
[ ! -e "$wrong_marker" ] ||
    { echo 'Metadata evaluation executed miniperl before dependency installation' >&2; exit 1; }
if run_pre_configure EMBERBSD_PERL_HOST_GENERATE=$missing_generate >"$work/missing-helper.log" 2>&1; then
    echo 'pre-configure accepted a missing native generator' >&2
    exit 1
fi
grep -q "Perl cross build requires executable host tool: $missing_generate" "$work/missing-helper.log" ||
    grep -q "EMBERBSD_PERL_HOST_GENERATE must select an executable host tool: $missing_generate" "$work/missing-helper.log" ||
    { echo 'pre-configure did not identify the missing native generator' >&2; exit 1; }
if run_pre_configure EMBERBSD_PERL_HOST_GENERATE= >"$work/unset-helper.log" 2>&1; then
    echo 'pre-configure accepted an unset native generator' >&2
    exit 1
fi
grep -q 'EMBERBSD_PERL_HOST_GENERATE must select an absolute host tool path' "$work/unset-helper.log" ||
    { echo 'pre-configure did not reject an unset native generator' >&2; exit 1; }
if run_pre_configure EMBERBSD_PERL_HOST_GENERATE=relative/generate_uudmap >"$work/relative-helper.log" 2>&1; then
    echo 'pre-configure accepted a relative native generator path' >&2
    exit 1
fi
grep -q 'EMBERBSD_PERL_HOST_GENERATE must select an absolute host tool path' "$work/relative-helper.log" ||
    { echo 'pre-configure did not reject a relative native generator path' >&2; exit 1; }
if run_pre_configure "EMBERBSD_PERL_HOST_MINIPERL=$wrong_miniperl" "PERL_WRONG_MARKER=$wrong_marker" >"$work/wrong-version.log" 2>&1; then
    echo 'pre-configure accepted a mismatched miniperl version' >&2
    exit 1
fi
grep -Fq "EMBERBSD_PERL_HOST_MINIPERL must report Perl 5.44.0 (got 5.043000)" "$work/wrong-version.log" ||
    { echo 'pre-configure did not reject the mismatched miniperl version' >&2; exit 1; }
echo 'PASS: Perl cross metadata uses versioned native tools without early probes; pre-configure checks installed tools and version'
