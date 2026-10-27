#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Check XZ's build shell and target shebangs.
# Requires native bmake and Autoconf. It builds no C code and installs no package.
set -eu
[ "$#" = 5 ] || {
    echo "Usage: $0 PKGSRC MAKECONF XZ_MAKEFILE XZ_SOURCE NEW_OUTPUT" >&2
    exit 2
}
: "${BMAKE:?Set native bmake}" "${AUTOCONF:?Set native Autoconf}"
pkgsrc=$1 conf=$2 recipe=$3 source=$4 out=$5
for path in "$@" "$BMAKE" "$AUTOCONF"; do
    case "$path" in /*) ;; *) echo 'Absolute paths required' >&2; exit 2 ;; esac
done
mkdir "$out"
field() { sed -n "s/^$1=//p" "$2"; }
fail() { echo "FAIL: $*" >&2; exit 1; }
make_recipe()
{
    "$BMAKE" -C "$pkgsrc/archivers/xz" -f "$recipe" MAKECONF="$conf" \
        WRKOBJDIR="$out/work" "$@"
}
for mode in no yes; do
    make_recipe USE_CROSS_COMPILE="$mode" -v PKG_FAIL_REASON \
        -v CONFIGURE_ENV -v CONFIG_SHELL -v CHECK_INTERPRETER \
        -v CROSS_DESTDIR -v CHECK_INTERPRETER_BASE_PATHS > "$out/$mode.raw"
    awk 'BEGIN {split("FAIL ENV SHELL CHECK ROOT BASE", labels)}
        {print labels[NR] "=" $0}' "$out/$mode.raw" > "$out/$mode.log"
    [ -z "$(field FAIL "$out/$mode.log")" ] || fail "$mode metadata rejected"
    [ "$(field CHECK "$out/$mode.log")" = yes ] || fail 'interpreter check disabled'
    env_value=$(field ENV "$out/$mode.log")
    if [ "$mode" = yes ]; then
        case " $env_value " in *' gl_cv_posix_shell=/bin/sh '*) ;; *) fail 'target POSIX shell not selected' ;; esac
    else
        case "$env_value" in *gl_cv_posix_shell=*) fail 'native shell discovery overridden' ;; esac
    fi
done
host_shell=$(field SHELL "$out/no.log")
[ "$(field SHELL "$out/yes.log")" = "$host_shell" ] || fail 'cross configure shell changed'
[ -x "$host_shell" ] || fail 'host configure shell not executable'
[ "$host_shell" != /bin/sh ] || fail 'use a distinct host CONFIG_SHELL to detect contamination'
# The packages-only sysroot has no base userland; the profile accepts /bin/sh.
case " $(field BASE "$out/yes.log") " in *' /bin/sh '*) ;; *) fail 'cross build rejects the target base shell' ;; esac
[ -z "$(field BASE "$out/no.log")" ] || fail 'native recursion accepts a target base shell'

# Expand the actual release macro and templates. The fixture needs no compiler.
mkdir "$out/fixture"
cp "$source/m4/posix-shell.m4" "$out/fixture/posix-shell.m4"
for name in xzdiff xzgrep xzless xzmore; do
    cp "$source/src/scripts/$name.in" "$out/fixture/$name.in"
done
cat > "$out/fixture/configure.ac" <<'AUTOCONF'
AC_INIT([XZ shell regression], [1])
m4_include([posix-shell.m4])
gl_POSIX_SHELL
AC_SUBST([enable_path_for_scripts], [])
AC_SUBST([xz], [xz])
AC_CONFIG_FILES([xzdiff xzgrep xzless xzmore])
AC_OUTPUT
AUTOCONF
(cd "$out/fixture" && "$AUTOCONF") > "$out/autoconf.log" 2>&1
for mode in no yes; do
    mkdir "$out/$mode"
    if [ "$mode" = yes ]; then
        cache=$(field ENV "$out/yes.log" | tr ' ' '\n' | sed -n 's/^gl_cv_posix_shell=//p')
        (cd "$out/$mode" && gl_cv_posix_shell="$cache" CONFIG_SHELL="$host_shell" \
            "$host_shell" "$out/fixture/configure") > "$out/configure-$mode.log" 2>&1
        expected=/bin/sh
    else
        (cd "$out/$mode" && CONFIG_SHELL="$host_shell" \
            "$host_shell" "$out/fixture/configure") > "$out/configure-$mode.log" 2>&1
        expected=$host_shell
    fi
    for name in xzdiff xzgrep xzless xzmore; do
        [ "$(head -1 "$out/$mode/$name")" = "#!$expected" ] || fail "$mode/$name shebang differs"
        sh -n "$out/$mode/$name"
    done
done

# Run the pkgsrc check, with its target base shell hook, on an isolated stage.
mkdir -p "$out/stage/usr/pkg/bin"
: > "$out/PLIST"
for name in xzdiff xzgrep xzless xzmore; do
    cp "$out/yes/$name" "$out/stage/usr/pkg/bin/$name"
    chmod +x "$out/stage/usr/pkg/bin/$name"
    printf 'bin/%s\n' "$name" >> "$out/PLIST"
done
for pair in xzdiff:xzcmp xzdiff:lzdiff xzdiff:lzcmp xzgrep:xzegrep \
    xzgrep:xzfgrep xzgrep:lzgrep xzgrep:lzegrep xzgrep:lzfgrep xzmore:lzmore xzless:lzless; do
    ln -s "${pair%:*}" "$out/stage/usr/pkg/bin/${pair#*:}"
    printf 'bin/%s\n' "${pair#*:}" >> "$out/PLIST"
done
check_stage()
{
    make_recipe USE_CROSS_COMPILE=yes WRKDIR="$out/check" \
        DESTDIR="$out/stage" PLIST="$out/PLIST" "$@"
}
check_stage makedirs > "$out/makedirs.log" 2>&1
check_stage _check-interpreter > "$out/interpreter.log" 2>&1
# The original host-path script must still be rejected by that same check.
cp "$out/no/xzdiff" "$out/stage/usr/pkg/bin/xzdiff"
chmod +x "$out/stage/usr/pkg/bin/xzdiff"
if check_stage _check-interpreter > "$out/rejected-host.log" 2>&1; then
    fail 'pkgsrc accepted a build-host interpreter in the target payload'
fi
grep -F "$host_shell" "$out/rejected-host.log" >/dev/null || fail 'negative check failed for another reason'
cp "$out/yes/xzdiff" "$out/stage/usr/pkg/bin/xzdiff"
chmod +x "$out/stage/usr/pkg/bin/xzdiff"
echo 'PASS: native discovery, target shebangs and real pkgsrc interpreter checks for 14 script names'
echo 'No C compilation, package install or target execution was performed.'
