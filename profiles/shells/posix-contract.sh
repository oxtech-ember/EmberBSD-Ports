#!/bin/sh
# Exercise common shell behavior with isolated files and explicit assertions.
set -eu
: "${SHELL_TEST_TMP:?Set SHELL_TEST_TMP to a private empty directory}"
cd "$SHELL_TEST_TMP"
count=0
check() {
    count=$((count + 1))
    "$@" || { printf 'FAIL: contract %s\n' "$count" >&2; exit 1; }
}
value='one two *'
check test "$value" = 'one two *'
check test "$((3 * 7 + 2))" -eq 23
set -- a 'b c' d
check test "$#" -eq 3
check test "$2" = 'b c'
check test "$(printf '%s\n' one two | tail -n 1)" = two
printf '%s\n' 'literal $value' > data
IFS= read -r line < data
check test "$line" = 'literal $value'
check test "$(cat <<'END'
literal $value
END
)" = 'literal $value'
check test "${value%% *}" = one
check test "${missing-default}" = default
case abc in a?c) result=yes ;; *) result=no ;; esac
check test "$result" = yes
if false; then exit 1; fi
check test "$(false || printf recovery)" = recovery
f() { printf '%s' "$1"; }
check test "$(f function)" = function
outer=retained
(outer=changed; test "$outer" = changed)
check test "$outer" = retained
(trap 'printf cleaned > trap-result' 0; exit 0)
check test "$(cat trap-result)" = cleaned
printf '%s\n' redirected 3>fd-result >&3
check test "$(cat fd-result)" = redirected
check test "$(printf '%s\n' data | while IFS= read -r name; do cat "$name"; done)" = 'literal $value'
printf 'PASS: %s POSIX contracts\n' "$count"
