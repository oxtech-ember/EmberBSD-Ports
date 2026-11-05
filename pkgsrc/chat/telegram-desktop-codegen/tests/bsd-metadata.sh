#!/bin/sh
# Inspect package metadata only; this does not execute a NetBSD build.
set -eu
[ "$#" -eq 3 ] || { echo 'usage: bsd-metadata.sh BMAKE MAKECONF RECIPE_DIR' >&2; exit 2; }
bmake=$1
export MAKECONF=$2
cd "$3"
for os in NetBSD FreeBSD OpenBSD DragonFly; do
    args=$("$bmake" -V '${CMAKE_CONFIGURE_ARGS}' USE_CROSS_COMPILE=no "OPSYS=$os")
    deps=$("$bmake" -V '${BUILDLINK_TREE}' USE_CROSS_COMPILE=no "OPSYS=$os")
    toolbase=$("$bmake" -V '${TOOLBASE}' USE_CROSS_COMPILE=no "OPSYS=$os")
    localbase=$("$bmake" -V '${LOCALBASE}' USE_CROSS_COMPILE=no "OPSYS=$os")
    case "$args" in *"-DDESKTOP_APP_CPPGIR_EXECUTABLE=$toolbase/bin/cppgir"*) ;; *) echo "$os: wrong generator" >&2; exit 1;; esac
    case "$args" in *"-DDESKTOP_APP_CPPGIR_DATA_DIR=$toolbase/share/cppgir"*) ;; *) echo "$os: wrong generator data" >&2; exit 1;; esac
    case "$args" in *"-DDESKTOP_APP_GIR_DIR=$localbase/share/gir-1.0"*) ;; *) echo "$os: wrong GIR directory" >&2; exit 1;; esac
    case " $deps " in *' cppgir '* ) ;; *) echo "$os: missing cppgir buildlink" >&2; exit 1;; esac
    case " $deps " in *' kf6-kcoreaddons '* ) ;; *) echo "$os: missing kcoreaddons buildlink" >&2; exit 1;; esac
    case " $deps " in *' glib2 '* ) ;; *) echo "$os: missing glib2 buildlink" >&2; exit 1;; esac
done
echo 'PASS: native Unix provider metadata'
