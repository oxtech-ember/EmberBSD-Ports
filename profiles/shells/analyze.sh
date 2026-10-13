#!/bin/sh
# Analyze the compiled Linux control configuration without hiding findings.
set -eu
[ "$#" -ge 1 ] && [ "$#" -le 2 ] || {
    echo 'Usage: analyze.sh BUILD_DIRECTORY [dash|zsh|mksh|ncurses|editline]' >&2; exit 2;
}
work=$1
components=${2:-'dash zsh mksh ncurses'}
profile=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
command -v cppcheck >/dev/null
command -v timeout >/dev/null
"${CLANG:-clang}" --version > /dev/null
mkdir -p "$work/analysis"
cppcheck --version > "$work/analysis/cppcheck-version.txt"
mkdir -p "$work/analysis/config"
cc=${CC:-gcc}
"$cc" -E -Wp,-v -xc /dev/null -o /dev/null 2> "$work/analysis/config/compiler-search.txt"
sed -n '/^#include <\.\.\.> search starts here:/,/^End of search list\./{ /^ /s/^ //p; }' \
    "$work/analysis/config/compiler-search.txt" > "$work/analysis/config/includes.txt"
"$cc" -dM -E -xc /dev/null > "$work/analysis/config/compiler-defines.h"
perl "$profile/compilation-database.pl" "$work"
failed=0
for component in $components; do
    case "$component" in dash|zsh|mksh|ncurses|editline) ;; *) exit 2 ;; esac
    mkdir -p "$work/analysis/$component"
    perl "$profile/analysis-config.pl" "$work" "$component"
    if cppcheck --project="$work/analysis/$component/cppcheck_commands.json" \
        --enable=all --inconclusive --check-level=normal --platform=unix64 \
        --error-exitcode=1 --xml --xml-version=2 \
        > "$work/analysis/$component/cppcheck.stdout" \
        2> "$work/analysis/$component/cppcheck.xml"; then
        echo 0 > "$work/analysis/$component/cppcheck.status"
    else
        result=$?
        echo "$result" > "$work/analysis/$component/cppcheck.status"
        failed=1
    fi
    perl "$profile/analyze.pl" "$work" "$component" || failed=1
    perl "$profile/analyze.pl" "$work" "$component" clang || failed=1
done
exit "$failed"
