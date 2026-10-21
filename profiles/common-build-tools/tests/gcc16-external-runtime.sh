#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Fixture regression for layering a
# cross-built GCC16 compiler stage over the installed runtime provider.
set -eu
[ "$#" = 1 ] || { echo 'Usage: gcc16-external-runtime.sh NEW_WORK' >&2; exit 2; }
root=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
script=$root/profiles/common-build-tools/cross/gcc16-external-runtime.sh
mkdir "$1"
work=$(CDPATH= cd -- "$1" && pwd)
mkdir "$work/bin"
# Fixture "ELF" files carry the readelf output for each query.
cat > "$work/bin/readelf" <<'EOF'
#!/bin/sh
for file do :; done
case "$1" in
-h) sed -n 's/^H://p' "$file" ;;
-d) sed -n 's/^D://p' "$file" ;;
--dyn-syms) sed -n 's/^S://p' "$file" ;;
*) exit 2 ;;
esac
EOF
cat > "$work/bin/pkg_info" <<'EOF'
#!/bin/sh
[ "$1" = -K ] || exit 2
db=$2; shift 2
case "$1" in
-e) [ -d "$db/gcc16-runtime-16.2.0nb6" ] || exit 1; echo gcc16-runtime-16.2.0nb6 ;;
-qL) cat "$db/$2/files" ;;
*) exit 2 ;;
esac
EOF
chmod +x "$work/bin/readelf" "$work/bin/pkg_info"
library() {
    cat <<EOF
H:  Type:                              DYN (Shared object file)
D: 0x000000000000000e (SONAME)             Library soname: [$1]
D: 0x0000000000000001 (NEEDED)             Shared library: [${3:-libc.so.12}]
S: Symbol table '.dynsym' contains 3 entries:
S:    Num:    Value          Size Type    Bind   Vis      Ndx Name
S:      1: ${2:-0000000000001000}    10 FUNC    GLOBAL DEFAULT   11 run@@GCC_16
S:      2: 0000000000004000     ${4:-8} TLS     GLOBAL DEFAULT   20 _ZSt11__once_call@@GLIBCXX_3.4.11
S:      3: 0000000000000000     0 FUNC    GLOBAL DEFAULT  UND abort
EOF
}
fixture() {
    rm -rf "$work/case"
    db=$work/case/sysroot/usr/pkg/pkgdb/gcc16-runtime-16.2.0nb6
    lib=$work/case/sysroot/usr/pkg/gcc16/lib
    stage=$work/case/stage/usr/pkg/gcc16
    mkdir -p "$db" "$lib" "$stage/lib" "$stage/include/c++/x86_64--netbsd/bits" "$stage/bin"
    printf '%s\n' /usr/pkg/gcc16/lib/libstdc++.so.7 /usr/pkg/gcc16/lib/libstdc++.so.7.36 \
        /usr/pkg/share/licenses/gcc16-runtime/COPYING3 > "$db/files"
    library libstdc++.so.7 > "$lib/libstdc++.so.7.36"
    ln -s libstdc++.so.7.36 "$lib/libstdc++.so.7"
    library libstdc++.so.7 0000000000002000 > "$stage/lib/libstdc++.so.7.36"
    ln -s libstdc++.so.7.36 "$stage/lib/libstdc++.so.7"
    ln -s libstdc++.so.7 "$stage/lib/libstdc++.so"
    echo compiler > "$stage/bin/gcc"
    echo '#define _GLIBCXX_HAVE_TLS 1' > "$stage/include/c++/x86_64--netbsd/bits/c++config.h"
    mkdir -p "$work/case/sysroot/usr/pkg/gcc16/include/c++/x86_64--netbsd/bits"
    cp "$stage/include/c++/x86_64--netbsd/bits/c++config.h" "$work/case/sysroot/usr/pkg/gcc16/include/c++/x86_64--netbsd/bits/"
}
run() {
    sh "$script" "$work/case/stage" /usr/pkg "$work/case/sysroot" /usr/pkg/pkgdb \
        "$work/bin/pkg_info" "$work/bin/readelf" x86_64--netbsd
}
refuse() {
    if run > "$work/$1.log" 2>&1; then echo "Accepted: $1" >&2; exit 1; fi
    grep -q "$2" "$work/$1.log" || { cat "$work/$1.log" >&2; exit 1; }
    # A refused stage keeps every runtime file for diagnosis.
    [ -e "$work/case/stage/usr/pkg/gcc16/lib/libstdc++.so.7.36" ] || [ "$1" = missing ] || exit 1
}
fixture
run > "$work/pass.log"
grep -q '2 files match gcc16-runtime-16.2.0nb6' "$work/pass.log"
[ ! -e "$work/case/stage/usr/pkg/gcc16/lib/libstdc++.so.7.36" ]
[ ! -L "$work/case/stage/usr/pkg/gcc16/lib/libstdc++.so.7" ]
# Development links and compiler files stay in the compiler package.
[ -L "$work/case/stage/usr/pkg/gcc16/lib/libstdc++.so" ] && [ -f "$work/case/stage/usr/pkg/gcc16/bin/gcc" ]
fixture
library libstdc++.so.7 0000000000001000 libm.so.0 > "$work/case/stage/usr/pkg/gcc16/lib/libstdc++.so.7.36"
refuse needed 'runtime ABI differs'
fixture
library libstdc++.so.7 0000000000001000 libc.so.12 16 > "$work/case/stage/usr/pkg/gcc16/lib/libstdc++.so.7.36"
refuse size 'runtime ABI differs'
fixture
sed 's/run@@GCC_16/run@@GCC_17/' "$work/case/sysroot/usr/pkg/gcc16/lib/libstdc++.so.7.36" > "$work/case/stage/usr/pkg/gcc16/lib/libstdc++.so.7.36"
refuse version 'runtime ABI differs'
fixture
rm "$work/case/stage/usr/pkg/gcc16/lib/libstdc++.so.7"
ln -s libstdc++.so.7.37 "$work/case/stage/usr/pkg/gcc16/lib/libstdc++.so.7"
refuse link 'runtime link differs'
fixture
rm "$work/case/stage/usr/pkg/gcc16/lib/libstdc++.so.7.36"
refuse missing 'lacks runtime file'
fixture
mv "$work/case/sysroot/usr/pkg/pkgdb/gcc16-runtime-16.2.0nb6" "$work/case/sysroot/usr/pkg/pkgdb/gcc16-runtime-16.2.0nb5"
refuse provider 'gcc16-runtime>=16.2.0nb6'
fixture
echo '/* #undef _GLIBCXX_HAVE_TLS */' > "$work/case/stage/usr/pkg/gcc16/include/c++/x86_64--netbsd/bits/c++config.h"
refuse tls 'TLS runtime ABI'
fixture
printf '#define _GLIBCXX_HAVE_TLS 1\n#define _GLIBCXX11_USE_C99_COMPLEX 1\n' > "$work/case/sysroot/usr/pkg/gcc16/include/c++/x86_64--netbsd/bits/c++config.h"
refuse config 'C++ configuration differs'
fixture
sed 's/^H:.*/H:  Type: EXEC (Executable file)/' "$work/case/sysroot/usr/pkg/gcc16/lib/libstdc++.so.7.36" > "$work/exec"
cp "$work/exec" "$work/case/sysroot/usr/pkg/gcc16/lib/libstdc++.so.7.36"
cp "$work/exec" "$work/case/stage/usr/pkg/gcc16/lib/libstdc++.so.7.36"
refuse type 'not a shared object'
rm -rf "$work/case" "$work/exec"
echo 'PASS: matching runtime files leave the compiler stage; ABI, link, provider, TLS, C++ configuration and file-type differences are refused'
