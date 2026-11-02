#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
# Test the actual cc wrapper and selected Clang. WORK must be new.
set -eu
[ "$#" -eq 4 ] || { echo "Usage: $0 CC_WRAPPER CLANG READELF NEW_WORK" >&2; exit 2; }
wrapper=$1 clang=$2 readelf=$3 work=$4
mkdir "$work"
cat > "$work/cc" <<EOF
exec=$clang
exec_path=$clang
path=${clang%/*}
worklog=$work/work.log
append_executable=-Wl,-z,relro
append_shared=-Wl,-z,relro
EOF
export CWRAPPERS_CONFIG_DIR=$work
cd "$work"
printf '#include "generated.h"\n' > missing.c
printf 'int main(void) { return 0; }\n' > main.c
for flag in -M -MM; do
    "$wrapper" -Werror "$flag" -MG missing.c > "${flag#-}.d"
    grep -q 'generated.h' "${flag#-}.d"
done
for flag in -MD -MMD; do
    "$wrapper" -Werror "$flag" main.c -o "${flag#-}-program"
    "$readelf" -l "${flag#-}-program" | grep -q GNU_RELRO
done
"$wrapper" -Werror -c main.c -o main.o
"$wrapper" -Werror -E main.c -o main.i
"$wrapper" -Werror -shared -fPIC main.c -o libmain.so
"$readelf" -l libmain.so | grep -q GNU_RELRO
printf '%s\n' 'PASS: -M/-MM dependencies, -MD/-MMD executable RELRO, shared RELRO, -c and -E'
