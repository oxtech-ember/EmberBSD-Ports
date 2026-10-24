#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD, AI-assisted checks through the actual upstream Meson CLI.
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 MESON_SOURCE NEW_WORK" >&2; exit 2; }
source=$1
mkdir "$2"
work=$(CDPATH= cd -- "$2" && pwd)
mkdir "$work/project" "$work/bin"
cat > "$work/project/meson.build" <<'EOF'
project('llvm-selection-fixture', 'c', 'cpp', meson_version: '>=1.12.1', default_options: ['cpp_std=c++20'])
cpp = meson.get_compiler('cpp')
assert(cpp.compiles('static_assert(__cplusplus >= 202002L); int main() { return 0; }'))
llvm = dependency('llvm', method: get_option('lookup'), native: get_option('build_dep'), version: '>=23.1.4')
assert(llvm.version() == '23.1.4')
EOF
cat > "$work/project/meson.options" <<'EOF'
option('lookup', type: 'combo', choices: ['config-tool', 'auto'], value: 'config-tool')
option('build_dep', type: 'boolean', value: false)
EOF
cat > "$work/bin/good" <<'EOF'
#!/bin/sh
printf '%s %s\n' "${0##*/}" "$*" >> "$LLVM_TRACE"
case "$1" in
    --version) if [ "${0##*/}" = wrong ]; then echo 21.1.8; else echo 23.1.4; fi ;;
    --components) echo core ;;
    --shared-mode) echo shared ;;
    --cppflags|--libs|--libfiles|--libdir) ;;
    *) exit 2 ;;
esac
EOF
cp "$work/bin/good" "$work/bin/wrong"
cp "$work/bin/good" "$work/bin/llvm-config-64"
cp "$work/bin/good" "$work/bin/llvm-config-32"
cp "$work/bin/good" "$work/bin/llvm-config"
cp "$work/bin/good" "$work/bin/llvm-config-23"
cat > "$work/bin/cmake" <<'EOF'
#!/bin/sh
echo cmake >> "$LLVM_TRACE"
exit 1
EOF
cat > "$work/bin/compiler-proxy" <<'EOF'
#!/bin/sh
exec "${CXX:-c++}" "$@"
EOF
chmod +x "$work/bin/"*
cat > "$work/native.ini" <<EOF
[binaries]
cpp = '$work/bin/compiler-proxy'
EOF
cp "$work/native.ini" "$work/native-good.ini"
printf "llvm-config = '%s/bin/good'\n" "$work" >> "$work/native-good.ini"
cp "$work/native.ini" "$work/native-bad.ini"
printf "llvm-config = '%s/missing'\n" "$work" >> "$work/native-bad.ini"
cat > "$work/cross.ini" <<EOF
[binaries]
c = '${CC:-cc}'
cpp = '$work/bin/compiler-proxy'
[host_machine]
system = 'linux'
cpu_family = 'aarch64'
cpu = 'aarch64'
endian = 'little'
EOF
probe()
{
    name=$1 want=$2 path=$3
    shift 3
    [ -z "${MESON_SELECTION_CASE:-}" ] || [ "$MESON_SELECTION_CASE" = "$name" ] || return 0
    trace=$work/$name.trace
    : > "$trace"
    if LLVM_TRACE="$trace" LLVM_CONFIG_PATH="$path" CMAKE="$work/bin/cmake" \
        PATH="$work/bin:$PATH" "${PYTHON:-python3}" "$source/meson.py" setup \
        "$work/$name-build" "$work/project" "$@" > "$work/$name.log" 2>&1; then result=0; else result=$?; fi
    printf '%s\n' "$result" > "$work/$name.status"
    printf '%s actual=%s expected=%s\n' "$name" "$result" "$want"
    if [ "$want" = pass ]; then [ "$result" -eq 0 ] || exit 1; else
        [ "$result" -ne 0 ] || { echo "FAIL: $name accepted invalid selection" >&2; exit 1; }
        grep -Eq 'Dependency.*(LLVM|llvm)|LLVM_CONFIG_PATH' "$work/$name.log"
    fi
    # Explicit config-tool selection must not execute an alternative provider.
    if grep -Eq '^(llvm-config[^ ]*|cmake)( |$)' "$trace"; then
        echo "FAIL: $name tried an alternative provider" >&2
        exit 1
    fi
}
probe valid pass "$work/bin/good" --native-file "$work/native.ini"
[ ! -f "$work/valid.trace" ] || grep -q '^good --version$' "$work/valid.trace"
probe missing fail "$work/missing" --native-file "$work/native.ini"
probe wrong-version fail "$work/bin/wrong" --native-file "$work/native.ini"
probe empty fail '' --native-file "$work/native.ini"
probe relative fail good --native-file "$work/native.ini"
probe machine-precedence pass "$work/missing" --native-file "$work/native-good.ini"
[ ! -f "$work/machine-precedence.trace" ] || grep -q '^good --version$' "$work/machine-precedence.trace"
probe invalid-machine fail "$work/bin/good" --native-file "$work/native-bad.ini"
probe auto-invalid fail "$work/missing" --native-file "$work/native.ini" -Dlookup=auto
probe cross-host fail "$work/bin/good" --native-file "$work/native.ini" --cross-file "$work/cross.ini"
probe cross-build pass "$work/bin/good" --native-file "$work/native.ini" --cross-file "$work/cross.ini" -Dbuild_dep=true
echo 'PASS: actual Meson tool selection; fake LLVM metadata, no LLVM/ELF runtime proof'
