#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Fake-tool command contract, not real packaging.
set -eu
[ "$#" = 1 ] || { echo 'Usage: package-cross-stage-contract.sh NEW_OUT' >&2; exit 2; }
out=$1
case "$out" in /*) ;; *) echo 'Absolute output path required.' >&2; exit 2;; esac
[ ! -e "$out" ] && [ ! -L "$out" ] || { echo 'Output path already exists.' >&2; exit 2; }
helper=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)/package-cross-stage.sh
umask 022
mkdir "$out"
mkdir "$out/tools" "$out/stage" "$out/recipe"
mkdir "$out/stage/bin"
printf 'Command-contract payload; not an executable.\n' > "$out/stage/bin/contract"
printf 'bin/contract\n' > "$out/recipe/PLIST"
printf 'Fake-tool package command contract.\n' > "$out/recipe/DESCR"
printf 'Glob expansion decoy.\n' > "$out/qt6-qtbase-6.12.0"
cat > "$out/tools/uname" <<'EOF'
#!/bin/sh
set -eu
case "$*" in -s) echo NetBSD;; -p) echo "${CONTRACT_MACHINE_ARCH:-x86_64}";; *) exit 2;; esac
EOF
cat > "$out/tools/pkg_create" <<'EOF'
#!/bin/sh
set -eu
: > "$CONTRACT_CALL_FILE"
for argument do
    printf '%s\n' "$argument" >> "$CONTRACT_CALL_FILE"
    package=$argument
done
printf 'Fake pkg_create placeholder; not a package archive.\n' > "$package"
EOF
cat > "$out/tools/pkg_info" <<'EOF'
#!/bin/sh
set -eu
[ "$#" = 2 ] && [ "$1" = -B ] && [ -s "$2" ]
printf 'Fake pkg_info command contract only.\n'
EOF
chmod 755 "$out/tools/uname" "$out/tools/pkg_create" "$out/tools/pkg_info"
PATH=$out/tools:$PATH
export PATH
depends='fixture-one-1.0 fixture-two-2.0nb1'
passed=0

metadata()
{
    printf 'MACHINE_ARCH=%s\nDEPENDS=%s\n' "$1" "$depends"
    if [ "$2" != absent ]; then printf 'CONFLICTS=%s\n' "$2"; fi
}

accept()
{
    name=$1
    arch=$2
    conflicts=$3
    info=$out/$name.build-info
    package=$out/$name.tgz
    CONTRACT_CALL_FILE=$out/$name.argv
    CONTRACT_MACHINE_ARCH=$arch
    export CONTRACT_CALL_FILE CONTRACT_MACHINE_ARCH
    metadata "$arch" "$conflicts" > "$info"
    (cd "$out" && sh "$helper" "$out/stage" "$out/recipe" "$package" "$info") > "$out/$name.log" 2>&1
    {
        printf '%s\n' -u root -g wheel -p "$out/stage" -I /usr/pkg \
            -c '-EmberBSD cross-built package' -d "$out/recipe/DESCR" \
            -f "$out/recipe/PLIST" -B "$info" -P "$depends"
        if [ "$conflicts" != absent ] && [ -n "$conflicts" ]; then
            printf '%s\n' -C "$conflicts"
        fi
        printf '%s\n' "$package"
    } > "$out/$name.expected-argv"
    cmp "$CONTRACT_CALL_FILE" "$out/$name.expected-argv"
    passed=$((passed + 1))
}

refuse()
{
    name=$1
    conflicts=$2
    info=$out/$name.build-info
    package=$out/$name.tgz
    CONTRACT_CALL_FILE=$out/$name.argv
    CONTRACT_MACHINE_ARCH=x86_64
    export CONTRACT_CALL_FILE CONTRACT_MACHINE_ARCH
    metadata x86_64 "$conflicts" > "$info"
    status=0
    (cd "$out" && sh "$helper" "$out/stage" "$out/recipe" "$package" "$info") > "$out/$name.log" 2>&1 || status=$?
    [ "$status" = 2 ]
    [ ! -e "$CONTRACT_CALL_FILE" ] && [ ! -e "$package" ]
    grep -q 'Invalid package conflict pattern list.' "$out/$name.log"
    passed=$((passed + 1))
}

accept absent x86_64 absent
accept empty x86_64 ''
accept glob x86_64 'qt6-qtbase-[0-9]* qt6-qtmultimedia-[0-9]*'
accept comparisons x86_64 'qt6-qtwayland<6.10.0 boost-libs>=1.90.0<2.0'
accept aarch64 aarch64 'qt6-qtbase-[0-9]*'
refuse metachar 'qt6-qtbase-[0-9]*;false'
refuse command 'qt6-qtbase-$(false)'
refuse option '-C'
refuse unclosed 'qt6-qtbase-[0-9*'
refuse unmatched 'qt6-qtbase-0-9]*'
refuse nested 'qt6-qtbase-[[0-9]]*'
refuse empty-class 'qt6-qtbase-[]*'
refuse duplicate "$(printf 'qt6-qtbase-[0-9]*\nCONFLICTS=qt6-qtmultimedia-[0-9]*')"
refuse duplicate-empty "$(printf '\nCONFLICTS=')"

CONTRACT_MACHINE_ARCH=x86_64
CONTRACT_CALL_FILE=$out/wrong-arch.argv
export CONTRACT_MACHINE_ARCH CONTRACT_CALL_FILE
metadata aarch64 'qt6-qtbase-[0-9]*' > "$out/wrong-arch.build-info"
status=0
sh "$helper" "$out/stage" "$out/recipe" "$out/wrong-arch.tgz" "$out/wrong-arch.build-info" > "$out/wrong-arch.log" 2>&1 || status=$?
[ "$status" = 1 ] && [ ! -e "$CONTRACT_CALL_FILE" ] && [ ! -e "$out/wrong-arch.tgz" ]
grep -q 'Package metadata does not match' "$out/wrong-arch.log"
passed=$((passed + 1))
printf 'PASS: %s fake-tool command contracts. No real package was created or installed.\n' "$passed" > "$out/result.txt"
cat "$out/result.txt"
