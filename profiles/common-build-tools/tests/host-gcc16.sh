#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Refusal checks for the standalone native GCC16 selector.
set -eu
[ "$#" = 1 ] || { echo "Usage: $0 NEW_WORK" >&2; exit 2; }
work=$1
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
mkdir "$work"
double() { # NAME GNUC CLANG BANNER
    cat > "$work/$1" <<SH
#!/bin/sh
case "\$*" in
*-dM*) printf '#define __GNUC__ $2\n'; [ "$3" = yes ] && printf '#define __clang__ 1\n'; exit 0 ;;
*--version*) echo '$4'; exit 0 ;;
esac
exit 1
SH
    chmod 755 "$work/$1"
}
double gcc 16 no 'gcc (GCC) 16.2.0'
double clang-as-gcc 4 yes 'gcc (GCC) 16.2.0'
double gcc-15 15 no 'gcc (GCC) 15.2.0'
double apple-banner 16 no 'Apple clang version 17'
check() { # EXPECTED_STATUS MESSAGE VALUE
    status=0
    out=$(HOST_CC=$3 sh -c '. "$1"; ember_require_host_gcc16 HOST_CC c' sh \
        "$here/../cross/host-gcc16.sh" 2>&1) || status=$?
    [ "$status" = "$1" ] || { echo "FAIL: '$3' status $status: $out" >&2; exit 1; }
    case "$out" in *"$2"*) ;; *) echo "FAIL: '$3': $out" >&2; exit 1;; esac
}
check 2 'HOST_CC is required' ''
check 2 'must be an absolute path' gcc
check 2 'not an executable file' "$work/missing"
check 2 'system or package-manager compiler' /usr/bin/cc
check 2 'is Clang, not native GCC16' "$work/clang-as-gcc"
check 2 'is not GCC16' "$work/gcc-15"
check 2 'reports Clang, LLVM or Apple' "$work/apple-banner"
check 0 '' "$work/gcc"
echo 'PASS: native GCC16 selector refusals and acceptance'
