#!/bin/sh
# Run bounded original gettext tests against an installed tool prefix.
set -eu
if [ "$#" -lt 2 ] || [ "$#" -gt 3 ]; then
    echo "usage: $0 PAYLOAD NEW_WORK [INSTALLED_PREFIX]" >&2
    exit 2
fi
payload=$(cd "$1" && pwd -P)
work=$2
prefix=${3:-/usr/pkg}
case "$prefix" in /*) ;; *) echo 'prefix must be absolute' >&2; exit 2;; esac
# Do not fall back to base tools or cross-build host executables.
for tool in msgfmt msgcat msgmerge msgunfmt msgcmp msgattrib gettext autopoint; do
    test -x "$prefix/bin/$tool" || { echo "missing installed tool: $tool" >&2; exit 1; }
done
test ! -e "$work" && test ! -L "$work"
umask 077
mkdir "$work"
work=$(cd "$work" && pwd -P)
mkdir -p "$work/home" "$work/tmp" "$work/logs" "$work/gettext-tools/tests" "$work/gettext-tools/autotools"
PATH=$prefix/bin:/usr/bin:/bin
task_home=$work/home
TMPDIR=$work/tmp
export PATH TMPDIR
# Upstream negative tests expect basename diagnostics. Preserve argv[0], but
# prove that PATH selects each installed binary before running any test.
: > "$work/versions.log"
for tool in msgfmt msgcat msgmerge msgunfmt msgcmp msgattrib gettext autopoint; do
    test "$(command -v "$tool")" = "$prefix/bin/$tool"
    printf '%s\n' "$prefix/bin/$tool" >> "$work/versions.log"
    "$tool" --version >> "$work/versions.log"
done
srcdir=$payload/gettext/gettext-tools/tests
abs_srcdir=$srcdir
abs_top_srcdir=$payload/gettext/gettext-tools
top_srcdir=$abs_top_srcdir
top_builddir=$work/gettext-tools
export srcdir abs_srcdir abs_top_srcdir top_srcdir top_builddir
MSGFMT=msgfmt
MSGCAT=msgcat
MSGMERGE=msgmerge
MSGUNFMT=msgunfmt
MSGCMP=msgcmp
MSGATTRIB=msgattrib
GETTEXT=gettext
AUTOCONF=$prefix/bin/autoconf
AUTOM4TE=$prefix/bin/autom4te
export MSGFMT MSGCAT MSGMERGE MSGUNFMT MSGCMP MSGATTRIB GETTEXT AUTOCONF AUTOM4TE
cp "$srcdir/init-env" "$work/gettext-tools/tests/"
ln -s "$prefix/bin/autopoint" "$work/gettext-tools/autotools/autopoint"
if [ -f "$prefix/share/gettext/archive.dir.tar.xz" ]; then
    ln -s "$prefix/share/gettext/archive.dir.tar.xz" "$work/gettext-tools/autotools/archive.dir.tar.xz"
fi
pass=0
skip=0
fail=0
record() {
    name=$1
    status=$2
    case "$status" in
        0) result=PASS; pass=$((pass + 1));;
        77) result=SKIP; skip=$((skip + 1));;
        *) result=FAIL; fail=$((fail + 1));;
    esac
    printf '%s\t%s\t%s\n' "$name" "$result" "$status" >> "$work/results.tsv"
    printf '%s: %s (exit %s)\n' "$name" "$result" "$status"
}
: > "$work/results.tsv"
for option in version help; do
    status=0
    "$prefix/bin/autopoint" "--$option" > "$work/logs/autopoint-$option.log" 2>&1 || status=$?
    record "autopoint-$option" "$status"
done
cd "$work/gettext-tools/tests"
while IFS="$(printf '\t')" read -r name purpose; do
    status=0
    env HOME="$task_home" /bin/sh "$srcdir/$name" > "$work/logs/$name.log" 2>&1 || status=$?
    record "$name" "$status"
done < "$payload/cases.tsv"
status=0
env HOME="$task_home" /bin/sh "$srcdir/autopoint-2" > "$work/logs/autopoint-2.log" 2>&1 || status=$?
record autopoint-2 "$status"
status=0
env HOME="$task_home" /bin/sh "$payload/fcitx-shell.sh" "$payload" "$work/fcitx-shell" "$prefix" \
    > "$work/logs/fcitx-shell.log" 2>&1 || status=$?
record fcitx-shell "$status"
printf 'SUMMARY: PASS=%s SKIP=%s FAIL=%s\n' "$pass" "$skip" "$fail"
test "$fail" -eq 0
