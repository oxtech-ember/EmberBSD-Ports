#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), build causal upstream FD-counter tests.
# Run the produced run.sh on NetBSD/AArch64; no target access is performed here.
set -eu
[ "$#" = 5 ] || { echo "Usage: $0 WAYLAND_SOURCE WAYLAND_BUILD CC SYSROOT NEW_WORK" >&2; exit 2; }
source=$1 build=$2 cc=$3 sysroot=$4 work=$5
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
for path do
    case "$path" in /*) ;; *) echo 'Absolute paths required.' >&2; exit 2;; esac
done
[ "$(shasum -a 256 "$source/tests/test-helpers.c" | awk '{print $1}')" = \
    871cc6743af1751dd0b07d1354525dc2cabfc8ef08a18ef5714be2240f17d5d3 ]
[ "$(shasum -a 256 "$source/tests/exec-fd-leak-checker.c" | awk '{print $1}')" = \
    d51b80979f547198359da7c4129e53d36e8688afc58a957bffe3ea94bc777596 ]
[ "$(shasum -a 256 "$source/tests/sanity-test.c" | awk '{print $1}')" = \
    0dd7aeead199b750ca89595f51eeecb03fb97b9ebbda2166ce349ec8eaa514d6 ]
patchfile=$root/../../pkgsrc/devel/wayland/patches/patch-tests_test-helpers.c
mkdir "$work"
mkdir -p "$work/baseline/tests" "$work/fixed/tests"
cp "$source/COPYING" "$work/COPYING"
for variant in baseline fixed; do
    cp "$source/tests/test-helpers.c" "$work/$variant/tests/"
    cp "$source/tests/test-runner.h" "$work/$variant/tests/"
    cp "$build/config.h" "$work/$variant/config.h"
done
# Keep the three upstream sanity bodies and leak checker unmodified. This
# focused runner omits the compositor cases; the full upstream suite is separate.
sed -n '1,24p' "$source/tests/sanity-test.c" > "$work/sanity-cases.h"
sed -n '/^FAIL_TEST(sanity_fd_leak)$/,/^static void$/p' \
    "$source/tests/sanity-test.c" | sed '$d' >> "$work/sanity-cases.h"
sed -n '1,24p' "$source/tests/test-runner.c" > "$work/check-fd-leaks.h"
awk '/^check_fd_leaks\(int supposed_fds\)$/ { active=1; print "void" } \
    active { print } active && /^}$/ { exit }' \
    "$source/tests/test-runner.c" >> "$work/check-fd-leaks.h"
cat > "$work/sanity-fd-cases.c" <<'EOF'
/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD (AI-assisted), direct runner for unchanged upstream cases. */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "test-runner.h"
int fd_leak_check_enabled = 1;
#include "sanity-cases.h"
#include "check-fd-leaks.h"
int main(int argc, char **argv)
{
    const struct test *tests[] = {
        &testsanity_fd_leak, &testsanity_fd_leak_exec, &testsanity_fd_exec
    };
    assert(argc == 2);
    for (unsigned i = 0; i < sizeof(tests) / sizeof(tests[0]); i++) {
        if (strcmp(argv[1], tests[i]->name) == 0) {
            int before = count_open_fds();
            tests[i]->run();
            check_fd_leaks(before);
            return 0;
        }
    }
    return 99;
}
EOF
patch -f -N -F 0 -p0 -d "$work/fixed" < "$patchfile" > "$work/patch.log"
if grep -Ei 'offset|fuzz|FAILED' "$work/patch.log"; then exit 1; fi
{
    shasum -a 256 "$source/tests/test-helpers.c" "$source/tests/test-runner.h" \
        "$source/tests/exec-fd-leak-checker.c" "$source/tests/sanity-test.c" \
        "$source/tests/test-runner.c" \
        "$build/config.h" "$cc" "$patchfile" "$0" "$root/tests/wayland-fds.c"
    "$cc" --version
} > "$work/inputs.txt"
for variant in baseline fixed; do
    "$cc" --sysroot="$sysroot" -std=c99 -D_POSIX_C_SOURCE=200809L \
        -O2 -Wall -Wextra -Werror -I"$work/$variant" -I"$work/$variant/tests" \
        -c "$work/$variant/tests/test-helpers.c" -o "$work/$variant/helpers.o"
    "$cc" --sysroot="$sysroot" -std=c99 -D_POSIX_C_SOURCE=200809L \
        -O2 -Wall -Wextra -Werror -I"$work/$variant/tests" \
        "$source/tests/exec-fd-leak-checker.c" "$work/$variant/helpers.o" \
        -o "$work/$variant/exec-fd-leak-checker"
    "$cc" --sysroot="$sysroot" -std=c99 -O2 -Wall -Wextra -Werror \
        "$root/tests/wayland-fds.c" "$work/$variant/helpers.o" \
        -o "$work/$variant/count-test"
    "$cc" --sysroot="$sysroot" -std=c99 -D_POSIX_C_SOURCE=200809L \
        -O2 -Wall -Wextra -Werror -I"$work" -I"$work/$variant/tests" \
        "$work/sanity-fd-cases.c" "$work/$variant/helpers.o" \
        -o "$work/$variant/sanity-fd-cases"
done
cat > "$work/run.sh" <<'EOF'
#!/bin/sh
set -eu
[ "$(uname -s)" = NetBSD ] || { echo 'Run on NetBSD.' >&2; exit 2; }
cd "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)"
ulimit -c 0
while read -r expected file; do
    [ "$(sha256 -q "$file")" = "$expected" ] || {
        echo "Changed artifact: $file" >&2; exit 1
    }
done < artifacts.sha256
for variant in baseline fixed; do
    if "./$variant/count-test" "$(pwd)/$variant/exec-fd-leak-checker" > "$variant.log" 2>&1; then
        status=0
    else
        status=$?
    fi
    cat "$variant.log"
    if [ "$variant" = fixed ]; then
        [ "$status" = 0 ] || exit 1
    else
        # With fdescfs mounted, the original counter may also be correct.
        printf 'Baseline status: %s (expected nonzero with static /dev/fd)\n' "$status"
    fi
    for testcase in sanity_fd_leak sanity_fd_leak_exec sanity_fd_exec; do
        if TEST_BUILD_DIR="$(pwd)/$variant" "./$variant/sanity-fd-cases" "$testcase" > "$variant-$testcase.log" 2>&1; then
            status=0
        else
            status=$?
        fi
        cat "$variant-$testcase.log"
        printf '%s upstream %s: exit %s\n' "$variant" "$testcase" "$status"
        if [ "$variant" = fixed ]; then
            case "$testcase" in
            sanity_fd_leak)
                [ "$status" -gt 128 ]
                grep -q 'unclosed 2' "$variant-$testcase.log" ;;
            sanity_fd_leak_exec) [ "$status" = 1 ] ;;
            sanity_fd_exec) [ "$status" = 0 ] ;;
            esac
        fi
    done
done
EOF
chmod +x "$work/run.sh"
(cd "$work" && shasum -a 256 baseline/count-test baseline/exec-fd-leak-checker \
    baseline/sanity-fd-cases fixed/count-test fixed/exec-fd-leak-checker \
    fixed/sanity-fd-cases run.sh > artifacts.sha256)
printf 'Built baseline/fixed upstream helper probes: %s/run.sh\n' "$work"
