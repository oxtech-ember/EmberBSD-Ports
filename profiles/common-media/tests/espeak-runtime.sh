#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Use unmodified upstream cases and installed data.
set -eu
[ "$#" = 2 ] || { echo 'Usage: espeak-runtime.sh TEST_BUNDLE NEW_RESULTS' >&2; exit 2; }
bundle=$(CDPATH= cd -- "$1" && pwd)
mkdir "$2"
result=$(CDPATH= cd -- "$2" && pwd)
mkdir "$result/scratch"
trap 'rm -rf "$result/scratch"' EXIT
trap 'exit 1' HUP INT TERM
ulimit -c 0
unset LD_LIBRARY_PATH ESPEAK_DATA_PATH
export LC_ALL=C
export TMPDIR=$result/scratch
cd "$result/scratch"
cp -R "$bundle/tests" tests
mkdir src
ln -s /usr/pkg/bin/espeak-ng src/espeak-ng
ln -s /usr/pkg/share/espeak-ng-data espeak-ng-data
failed=0
for test in cmd_options language-numbers-cardinal language-numbers-ordinal language-pronunciation language-phonemes language-replace; do
    if timeout -k 5 60 sh "tests/$test.test" > "$result/$test.log" 2>&1; then
        echo "PASS: upstream $test"
    else
        echo "FAIL: upstream $test"
        failed=1
    fi
done
for test in encoding ieee80; do
    if timeout -k 5 30 "$bundle/bin/$test.test" > "$result/$test.log" 2>&1; then
        echo "PASS: upstream $test"
    else
        echo "FAIL: upstream $test"
        failed=1
    fi
done
for iteration in 1 2; do
    timeout -k 5 15 espeak-ng -v en -w "$result/en-$iteration.wav" 'EmberBSD speech synthesis.'
    timeout -k 5 15 espeak-ng -v ru -w "$result/ru-$iteration.wav" 'Проверка синтеза речи.'
done
if timeout -k 5 15 espeak-ng -f "$result/missing-text" -w "$result/missing.wav" > "$result/missing.log" 2>&1; then
    echo 'FAIL: missing input accepted'
    failed=1
fi
if timeout -k 5 15 espeak-ng -v emberbsd-missing-voice -w "$result/invalid-voice.wav" 'test' > "$result/invalid-voice.log" 2>&1; then
    echo 'FAIL: unknown voice accepted'
    failed=1
fi
[ "$failed" = 0 ]
echo 'PASS: six upstream CLI suites, encoding/IEEE80 tests, repeated file synthesis and invalid inputs'
