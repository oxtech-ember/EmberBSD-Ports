#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), unchanged upstream installed spell checks.
set -eu
[ "$#" = 2 ] || { echo 'Usage: spell-runtime.sh VERIFIED_FIXTURES NEW_OUTPUT' >&2; exit 2; }
runner=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
fixtures=$(CDPATH= cd -- "$1" && pwd)
umask 077
mkdir "$2"
work=$(CDPATH= cd -- "$2" && pwd)
PATH=/usr/pkg/bin:/usr/pkg/sbin:/usr/bin:/usr/sbin:/bin:/sbin; export PATH
unset LD_LIBRARY_PATH LD_PRELOAD
PERL5LIB="$fixtures/test-perl/lib"; export PERL5LIB
perl -MIPC::System::Simple -e 'exit 0'
ulimit -c 0
mkdir "$work/home" "$work/data"
HOME="$work/home"; export HOME
# Upstream Markdown uses diff -u -Z; the base diff lacks -Z. Exercise the
# text-only adapter with positive and negative controls before any test uses it.
mkdir "$work/test-tools" "$work/tmp"
cp "$runner/diff-trailing-space.sh" "$work/test-tools/diff"
chmod +x "$work/test-tools/diff"
TMPDIR="$work/tmp"; export TMPDIR
printf 'same \t\r\n' > "$work/diff-a"
printf 'same\n' > "$work/diff-b"
"$work/test-tools/diff" -u -Z "$work/diff-a" "$work/diff-b"
printf 'different\n' > "$work/diff-b"
result=0
"$work/test-tools/diff" -u -Z "$work/diff-a" "$work/diff-b" > "$work/diff-negative.log" || result=$?
[ "$result" = 1 ]
result=0
"$work/test-tools/diff" --unsupported > "$work/diff-invalid.log" 2>&1 || result=$?
[ "$result" = 2 ]
sysctl kern.boottime > "$work/boot.before"
for package in aspell hunspell; do
    pkg_info -e "$package" >> "$work/packages.txt"
    ldd "/usr/pkg/bin/$package" > "$work/$package.ldd"
    ! grep -q 'not found' "$work/$package.ldd"
done
cp -R "$fixtures/aspell-test" "$work/aspell-test"
cp -R "$fixtures/aspell-dict" "$work/aspell-dict"
cp -R "$fixtures/hunspell-tests" "$work/hunspell-tests"
# Build dictionary data with the installed target tool, not target C/C++ code.
ASPELL_CONF="dict-dir $work/data; local-data-dir $work/data"; export ASPELL_CONF
cp "$work/aspell-test/en_phonet.dat" "$work/aspell-dict/en_phonet.dat"
(
    cd "$work/aspell-dict"
    cp ./*.dat "$work/data/"
    sh ./configure
    make datadir="$work/data" dictdir="$work/data" install
) > "$work/dictionary.log" 2>&1
cp "$work/aspell-test/en.dat" "$work/aspell-test/en.prepl" \
    "$work/aspell-test/en_repl.dat" "$work/aspell-test/en_phonet.dat" "$work/data/"
printf 'add en_US.multi\nadd en.prepl\n' > "$work/data/en_US-w_repl.multi"
(
    cd "$work/aspell-test"
    mkdir tmp
    timeout -k 5 120 sh ./sanity > "$work/aspell-sanity.log" 2>&1
    PATH="$work/test-tools:$PATH" timeout -k 5 120 perl ./filter-test /usr/pkg/bin/aspell < markdown.dat > "$work/aspell-markdown.log" 2>&1
    timeout -k 5 60 ./wide_test_valid > "$work/aspell-wide-valid.log" 2>&1
    timeout -k 5 60 ./wide_test_secure > "$work/aspell-wide-secure.log" 2>&1
    result=0
    timeout -k 5 60 ./wide_test_invalid > "$work/aspell-wide-invalid.log" 2>&1 || result=$?
    [ "$result" != 0 ] && [ "$result" != 124 ] && [ "$result" != 137 ]
    grep -q 'Null-terminated wide-character strings unsupported when used this way.' "$work/aspell-wide-invalid.log"
)
# Exercise the actual installed dictionary dispatch; unknown formats still fail.
mkdir "$work/suffixes"
for extension in spcl special; do
    printf 'add en_US.multi\n' > "$work/suffixes/fixture.$extension"
    printf 'swimmer\n' | aspell -d "$work/suffixes/fixture.$extension" -a > "$work/suffixes/$extension.log" 2>&1
    grep -qx '\*' "$work/suffixes/$extension.log"
done
printf 'add en_US.multi\n' > "$work/suffixes/fixture.unknown"
result=0
printf 'swimmer\n' | aspell -d "$work/suffixes/fixture.unknown" -a > "$work/suffixes/unknown.log" 2>&1 || result=$?
[ "$result" != 0 ]
grep -q 'not in the proper format' "$work/suffixes/unknown.log"
# Only replace the launcher for upstream's /bin/bash; preserve the test body.
mv "$work/hunspell-tests/test.sh" "$work/hunspell-tests/upstream-test.sh"
cat > "$work/hunspell-tests/test.sh" <<'BASH'
#!/bin/sh
exec /usr/pkg/bin/bash "$(dirname "$0")/upstream-test.sh" "$@"
BASH
chmod +x "$work/hunspell-tests/test.sh"
# Installed executables do not need libtool's build-tree library selection.
cat > "$work/installed-exec" <<'EXEC'
#!/bin/sh
set -eu
[ "$1" = --mode=execute ] || exit 2
shift
exec "$@"
EXEC
chmod +x "$work/installed-exec"
HUNSPELL=/usr/pkg/bin/hunspell ANALYZE=/usr/pkg/bin/hunspell-analyze
CHMORPH=/usr/pkg/bin/chmorph LIBTOOL="$work/installed-exec"
export HUNSPELL ANALYZE CHMORPH LIBTOOL
passed=0 skipped=0 failed=0
mkdir "$work/hunspell-results"
while read -r testname; do
    result=0
    (
        cd "$work/hunspell-tests"
        case "$testname" in
            *.dic) timeout -k 5 90 bash ./upstream-test.sh "$testname" ;;
            *) timeout -k 5 90 sh "./$testname" ;;
        esac
    ) > "$work/hunspell-results/$testname.log" 2>&1 || result=$?
    printf '%s\n' "$result" > "$work/hunspell-results/$testname.status"
    case "$result" in
        0) passed=$((passed + 1)) ;;
        77) skipped=$((skipped + 1)) ;;
        *) failed=$((failed + 1)); printf 'FAIL %s (%s)\n' "$testname" "$result" ;;
    esac
done < "$fixtures/hunspell-tests.list"
printf 'Hunspell: %s pass, %s skip, %s fail\n' "$passed" "$skipped" "$failed"
sysctl kern.boottime > "$work/boot.after"
cmp "$work/boot.before" "$work/boot.after"
[ "$failed" = 0 ]
echo 'PASS: installed Aspell upstream sanity/Markdown/wide API checks and Hunspell upstream suites'
