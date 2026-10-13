#!/bin/sh
# Exercise the real upstream routine. Do not duplicate its prefix expression.
set -eu
if [ "$#" -ne 2 ]; then
    echo "usage: $0 ENCHANT_SOURCE NEW_WORK" >&2
    exit 2
fi
source_dir=$(cd "$1" && pwd)
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
work=$2
cxx=${CXX:-clang++}
test ! -e "$work"
mkdir -p "$work"
work=$(cd "$work" && pwd)
# The release uses CRLF. Extract the complete definition, not the declaration.
awk '
    { sub(/\r$/, "") }
    /^int TestProvidersInDirectory\(char \* dir_name\)$/ { active=1 }
    active {
        print
        opens=gsub(/\{/, "{"); closes=gsub(/\}/, "}")
        depth+=opens-closes
        if (opens) started=1
        if (started && depth==0) { done=1; exit }
    }
    END { if (!done) exit 1 }
' "$source_dir/tests/providers/providers.test.cpp" > "$work/provider-discovery.inc"
"$cxx" -std=c++20 -Wall -Wextra -Werror -I"$work" \
    -fsanitize=address,undefined -fno-omit-frame-pointer \
    "$script_dir/provider-discovery.cpp" -o "$work/provider-discovery"
ASAN_OPTIONS=halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1 "$work/provider-discovery"
