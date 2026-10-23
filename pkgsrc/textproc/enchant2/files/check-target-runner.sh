#!/bin/sh
# Check runner layout and failure handling. These stubs do not test Enchant.
set -eu
if [ "$#" -ne 1 ]; then
    echo "usage: $0 NEW_WORK" >&2
    exit 2
fi
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
root=$1
test ! -e "$root" && test ! -L "$root"
mkdir "$root"
root=$(cd "$root" && pwd -P)
payload=$root/payload
mkdir -p "$payload/lib/.libs"
for name in libenchant_mock_provider.so libenchant_mock_provider2.so \
    libenchant_null_provider.so libenchant_null_identify.so \
    libenchant_null_describe.so enchant_hunspell.so test.pwl \
    lib/.libs/libenchant-2.so.2; do
    printf '%s\n' "$name" > "$payload/$name"
done
cat > "$payload/main.test" <<'SCRIPT'
#!/bin/sh
set -eu
test "$HOME" = "$PWD/home"
test "$ENCHANT_CONFIG_DIR" = config
test "$LD_LIBRARY_PATH" = "$PWD/lib/.libs"
grep -Fx 'lib/.libs/libenchant-2.so.2' "$LD_LIBRARY_PATH/libenchant-2.so.2" >/dev/null
test -f libenchant_mock_provider.so
test -w test.pwl
if [ "$TEST_FIXTURE_MODE" = main-fails ]; then exit 17; fi
echo 'Success: 1 tests passed.'
SCRIPT
cat > "$payload/providers.test" <<'SCRIPT'
#!/bin/sh
set -eu
if [ "$TEST_FIXTURE_MODE" = provider-fails ]; then exit 19; fi
if [ "$TEST_FIXTURE_MODE" = no-provider ]; then exit 0; fi
printf 'Running tests on %s/enchant_hunspell.so\n' "$PWD"
echo 'Success: 1 tests passed.'
SCRIPT
chmod u+x "$payload/main.test" "$payload/providers.test"
for mode in pass main-fails provider-fails no-provider; do
    status=0
    TEST_FIXTURE_MODE=$mode sh "$script_dir/run-target-tests.sh" \
        "$payload" "$root/run $mode" > "$root/$mode.log" 2>&1 || status=$?
    case "$mode:$status" in
        pass:0|main-fails:17|provider-fails:19|no-provider:1) ;;
        *) echo "FAIL: $mode returned $status" >&2; exit 1 ;;
    esac
done
# A second invocation must preserve an existing work directory.
status=0
TEST_FIXTURE_MODE=pass sh "$script_dir/run-target-tests.sh" \
    "$payload" "$root/run pass" > "$root/existing-work.log" 2>&1 || status=$?
test "$status" -ne 0
echo 'PASS: runner layout, isolated paths, failure status, and non-vacuous counts'
