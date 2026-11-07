#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Check the common package's shared/static and opt-in upstream test options.
set -eu

if [ "$#" -ne 2 ]; then
	echo "Usage: $0 BMAKE PKGSRCDIR" >&2
	exit 2
fi
bmake=$1
pkgsrc=$2
pkg=$pkgsrc/security/wolfssl
pc_patch=$pkg/patches/patch-support_wolfssl_pc.in
private_libs=$(sed -n 's/^+Libs[.]private: //p' "$pc_patch")
case "$private_libs" in
*'@PTHREAD_LIBS@'*) ;;
*) echo "static pkg-config interface omits detected pthread libraries: $private_libs" >&2; exit 1 ;;
esac
case "$private_libs" in
*'-lpthread'*|*'-pthread'*) echo "pkg-config interface hardcodes pthread for single-threaded builds: $private_libs" >&2; exit 1 ;;
esac
supported=$("$bmake" -C "$pkg" -V PKG_SUPPORTED_OPTIONS)
case " $supported " in
*" shared "*) ;;
*) echo "missing WolfSSL shared package option: $supported" >&2; exit 1 ;;
esac
case " $supported " in
*" tests "*) ;;
*) echo "missing WolfSSL tests package option: $supported" >&2; exit 1 ;;
esac
test_target=$("$bmake" -C "$pkg" PKG_OPTIONS.wolfssl=tests -V TEST_TARGET)
[ "$test_target" = check ] || { echo "tests option lacks the upstream check target: $test_target" >&2; exit 1; }
test_target=$("$bmake" -C "$pkg" PKG_OPTIONS.wolfssl=-tests -V TEST_TARGET)
[ -z "$test_target" ] || { echo "disabled tests still select an upstream target: $test_target" >&2; exit 1; }
disabled_test=$("$bmake" -C "$pkg" PKG_OPTIONS.wolfssl=-tests -n do-test)
case "$disabled_test" in
*"WolfSSL tests are disabled"*) ;;
*) echo "disabled test target does not explain how to enable tests: $disabled_test" >&2; exit 1 ;;
esac

has()
{
	case " $args " in
	*" $1 "*) return 0 ;;
	*) return 1 ;;
	esac
}

check()
{
	options=$1
	shared=$2
	tests=$3
	args=$("$bmake" -C "$pkg" "PKG_OPTIONS.wolfssl=$options" -V CONFIGURE_ARGS)
	if [ "$shared" = yes ]; then
		has --enable-shared || { echo "$options: missing --enable-shared" >&2; exit 1; }
		! has --disable-shared || { echo "$options: unexpected --disable-shared" >&2; exit 1; }
	else
		has --disable-shared || { echo "$options: missing --disable-shared" >&2; exit 1; }
		! has --enable-shared || { echo "$options: unexpected --enable-shared" >&2; exit 1; }
	fi
	if [ "$tests" = yes ]; then
		has --enable-examples || { echo "$options: missing --enable-examples" >&2; exit 1; }
		has --enable-crypttests || { echo "$options: missing --enable-crypttests" >&2; exit 1; }
		! has --disable-examples || { echo "$options: unexpected --disable-examples" >&2; exit 1; }
		! has --disable-crypttests || { echo "$options: unexpected --disable-crypttests" >&2; exit 1; }
	else
		has --disable-examples || { echo "$options: missing --disable-examples" >&2; exit 1; }
		has --disable-crypttests || { echo "$options: missing --disable-crypttests" >&2; exit 1; }
		! has --enable-examples || { echo "$options: unexpected --enable-examples" >&2; exit 1; }
		! has --enable-crypttests || { echo "$options: unexpected --enable-crypttests" >&2; exit 1; }
	fi
	has --enable-wpas || { echo "$options: missing --enable-wpas" >&2; exit 1; }
	has --enable-ecc || { echo "$options: missing --enable-ecc" >&2; exit 1; }
	has --enable-tls13 || { echo "$options: missing --enable-tls13" >&2; exit 1; }
}

check '' yes yes
check shared yes yes
check -shared no yes
check -tests yes no
check 'shared -tests' yes no
check '-shared -tests' no no
echo "PASS: WolfSSL backend, test, and shared/static options"
