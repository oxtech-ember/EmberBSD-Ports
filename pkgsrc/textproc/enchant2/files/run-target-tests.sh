#!/bin/sh
# Run the upstream ELF tests in a disposable copy of their fixture layout.
# AI-assisted EmberBSD adaptation. This does not replace a production library.
set -eu
if [ "$#" -ne 2 ]; then
    echo "usage: $0 PAYLOAD NEW_WORK" >&2
    exit 2
fi
payload=$(cd "$1" && pwd -P)
work=$2
files='main.test providers.test libenchant_mock_provider.so
libenchant_mock_provider2.so libenchant_null_provider.so
libenchant_null_identify.so libenchant_null_describe.so
enchant_hunspell.so test.pwl'
for name in $files lib/.libs/libenchant-2.so.2; do
    test -f "$payload/$name" || { echo "missing payload: $name" >&2; exit 1; }
done
test ! -e "$work" && test ! -L "$work"
umask 077
mkdir "$work"
work=$(cd "$work" && pwd -P)
mkdir -p "$work/home" "$work/lib/.libs"
for name in $files; do
    cp "$payload/$name" "$work/$name"
done
cp "$payload/lib/.libs/libenchant-2.so.2" "$work/lib/.libs/"
chmod u+w "$work/test.pwl"
cd "$work"
HOME=$work/home
ENCHANT_CONFIG_DIR=config
# Match the upstream libtool wrapper and libenchant-copy target. The library
# bytes must match the tested build. Its location controls gnulib relocation.
LD_LIBRARY_PATH=$work/lib/.libs
export HOME ENCHANT_CONFIG_DIR LD_LIBRARY_PATH
status=0
./main.test > main.log 2>&1 || status=$?
cat main.log
if [ "$status" -ne 0 ]; then
    exit "$status"
fi
status=0
./providers.test > providers.log 2>&1 || status=$?
cat providers.log
if [ "$status" -ne 0 ]; then
    exit "$status"
fi
# The old discovery bug returned success without running a provider test.
grep -F "Running tests on $work/enchant_hunspell.so" providers.log >/dev/null
grep -E '^Success: [1-9][0-9]* tests passed\.$' main.log >/dev/null
grep -E '^Success: [1-9][0-9]* tests passed\.$' providers.log >/dev/null
