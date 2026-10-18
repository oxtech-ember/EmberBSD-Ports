#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), real recipe generator compiler regression.
set -eu
[ "$#" = 3 ] || { echo "Usage: $0 EXPORTED_PKGSRC MAKECONF NEW_WORK" >&2; exit 2; }
pkgsrc=$1 makeconf=$2 work=$3
bmake=${BMAKE:-bmake}
mkdir "$work"
"$bmake" -C "$pkgsrc/shells/bash" MAKECONF="$makeconf" show-vars \
    VARNAMES='PKG_FAIL_REASON EMBERBSD_CROSS_BUILD_CC NATIVE_CC EMBERBSD_CROSS_BUILD_CXX NATIVE_CXX CONFIGURE_ENV NATIVE_OPSYS' \
    > "$work/bash.txt" 2> "$work/bash.stderr"
[ -z "$(sed -n '1p' "$work/bash.txt")" ]
"${RUBY:-ruby}" - "$work/bash.txt" <<'RUBY_CHECK'
require 'shellwords'
v = File.readlines(ARGV.fetch(0)).map(&:chomp)
[[v[1], v[2]], [v[3], v[4]]].each do |provider, command|
  expected = [provider]
  expected << '-B/usr/bin/' if %w[Darwin Linux].include?(v[6])
  abort 'wrong native compiler command' unless provider.start_with?('/') && Shellwords.split(command) == expected
end
# Bash appends another CC_FOR_BUILD. Check every assignment, including the last.
assignments = Shellwords.split(v[5]).grep(/^CC_FOR_BUILD=/)
abort 'missing Bash configure assignments' unless assignments.length >= 2
abort 'inconsistent compiler assignment' unless assignments.all? { |x| x == 'CC_FOR_BUILD=' + v[2] }
RUBY_CHECK
for variable in NATIVE_CC NATIVE_CXX; do
    "$bmake" -C "$pkgsrc/shells/bash" MAKECONF="$makeconf" \
        "$variable=/bin/false" -v PKG_FAIL_REASON > "$work/$variable.txt"
    grep -q 'Cross generators require the selected native build compilers' "$work/$variable.txt"
done
echo 'PASS: actual Bash generator compiler assignments and overridden-compiler refusal'
