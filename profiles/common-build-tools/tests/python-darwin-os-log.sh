#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD, AI-assisted extraction of CPython's Darwin os_log guard.
# Check that GCC on Darwin skips os/log.h, which needs a Clang-only builtin.
set -eu
[ "$#" -eq 3 ] || { echo "Usage: $0 PATCHED_PYTHON PRISTINE_PYTHON NEW_WORK" >&2; exit 2; }
[ "$(uname -s)" = Darwin ] || { echo "SKIP: needs a Darwin SDK" >&2; exit 0; }
: "${GCC_CC:?set GCC_CC to the GCC driver under test}"
mkdir "$3"
work=$(CDPATH= cd -- "$3" && pwd)
patched=$1 pristine=$2
for tree in patched pristine; do
    eval "src=\$$tree"
    awk '/^#if defined\(__APPLE__\)$/ { take=1 } take { print } \
        take && /^#endif$/ { exit }' "$src/Python/pylifecycle.c" > "$work/$tree.c"
    grep -q 'include <os/log.h>' "$work/$tree.c"
    cat >> "$work/$tree.c" <<'C'
#if HAS_APPLE_SYSTEM_LOG
/* The same call shape as CPython's apple_log_write_impl(). */
void apple_log_write(const char *text);
void
apple_log_write(const char *text)
{
    os_log_with_type(OS_LOG_DEFAULT, OS_LOG_TYPE_DEFAULT, "%{public}s", text);
}
#endif
int
main(void)
{
    return HAS_APPLE_SYSTEM_LOG;
}
C
done
# The patched guard compiles cleanly and disables the Clang-only logger.
"$GCC_CC" -std=gnu11 -Wall -Wextra -Werror -fanalyzer \
    "$work/patched.c" -o "$work/patched" > "$work/patched.log" 2>&1
"$work/patched"
# Control: the pristine guard still includes os/log.h and fails with GCC.
if "$GCC_CC" -std=gnu11 -c "$work/pristine.c" -o "$work/pristine.o" \
    > "$work/pristine.log" 2>&1; then
    echo "FAIL: pristine CPython guard unexpectedly compiled" >&2
    exit 1
fi
grep -q 'os_log' "$work/pristine.log"
echo PASS
