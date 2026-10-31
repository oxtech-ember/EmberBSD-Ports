#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake cross-grpc-host-generators.sh PKGSRC MAKECONF
#
# When cross compiling, grpc's CMakeLists.txt looks up grpc_cpp_plugin on
# PATH and takes protoc from the buildlink copy of the target protoc. The
# cross bulk stopped in grpc++_reflection with "don't know how to make
# _gRPC_CPP_PLUGIN-NOTFOUND". Check that the cross build of net/grpc names
# the plugin of the native grpc tool dependency and the native protoc.
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 PKGSRC MAKECONF" >&2; exit 2; }
pkgsrc=$1 makeconf=$2
bm() { MAKECONF=$makeconf "${BMAKE:-bmake}" -C "$pkgsrc/net/grpc" MAKECONF="$makeconf" "$@" </dev/null; }
[ "$(bm -V '${USE_CROSS_COMPILE:Uno:tl}')" = yes ] ||
	{ echo "$0: select a MAKECONF for a cross build" >&2; exit 2; }
toolbase=$(bm -V '${TOOLBASE}')
status=0
tool=no
for d in $(bm -V '${TOOL_DEPENDS}'); do
	case $d in grpc-*:../../net/grpc) tool=yes;; esac
done
[ "$tool" = yes ] || { echo "FAIL: no tool dependency on the native net/grpc"; status=1; }
args=" $(bm -V '${CMAKE_CONFIGURE_ARGS}') "
case $args in *" -D_gRPC_CPP_PLUGIN:FILEPATH=$toolbase/bin/grpc_cpp_plugin "*) ;;
*) echo "FAIL: grpc_cpp_plugin is not the native $toolbase/bin/grpc_cpp_plugin"; status=1;;
esac
case $args in *" -D_gRPC_PROTOBUF_PROTOC_EXECUTABLE:FILEPATH=$toolbase/bin/protoc "*) ;;
*) echo "FAIL: protoc is not the native $toolbase/bin/protoc"; status=1;;
esac
[ "$status" -eq 0 ] || exit 1
echo "PASS: cross net/grpc runs the native grpc_cpp_plugin and protoc"
