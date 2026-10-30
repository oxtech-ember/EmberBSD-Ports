#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Reject invalid scanner bootstrap inputs.
set -eu
# These isolated input/PLAN fixtures exercise the lower-level producer.
QT_HOST_LOCKED=1
export QT_HOST_LOCKED
[ "$#" = 3 ] || { echo "Usage: $0 DISTFILES HOST_QT NEW_WORK" >&2; exit 2; }
dist=$1 host=$2 work=$3
[ ! -e "$work" ] && [ ! -L "$work" ]
mkdir "$work"
recipe=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)/build-qtwaylandscanner.sh
reject() {
    name=$1 message=$2; shift 2
    status=0
    "$@" > "$work/$name.log" 2>&1 || status=$?
    [ "$status" = 2 ] && grep -q "$message" "$work/$name.log" || {
        echo "Invalid input did not fail safely: $name ($status)" >&2; exit 1;
    }
}
reject relative 'Use absolute paths' sh "$recipe" "$dist" "$host" relative "$work/obj" "$work/prefix"
reject parent 'Parent path components' sh "$recipe" "$dist" "$host" "$work/new/.." "$work/obj" "$work/prefix"
reject equal 'overlap' sh "$recipe" "$dist" "$host" "$work/same" "$work/same" "$work/prefix"
reject nested 'overlap' sh "$recipe" "$dist" "$host" "$work/source" "$work/source/obj" "$work/prefix"
reject outputs 'overlap' sh "$recipe" "$dist" "$host" "$work/source" "$work/obj" "$work/obj"
reject jobs 'JOBS must be positive' env JOBS=0 sh "$recipe" "$dist" "$host" "$work/source" "$work/obj" "$work/prefix"
for name in source prefix objects; do
    ln -s "$work/absent" "$work/dangling-$name"
    source=$work/source objects=$work/obj prefix=$work/prefix
    case "$name" in
    source) source=$work/dangling-source ;;
    prefix) prefix=$work/dangling-prefix ;;
    objects) objects=$work/dangling-objects ;;
    esac
    reject "symlink-$name" 'must not be symlinks' sh "$recipe" "$dist" "$host" "$source" "$objects" "$prefix"
done
reject missing 'Cannot resume missing' env RESUME=1 sh "$recipe" "$dist" "$host" "$work/source" "$work/obj" "$work/prefix"
mkdir "$work/foreign"
printf 'foreign input\n' > "$work/foreign/inputs.txt"
reject changed 'Bootstrap inputs changed' env RESUME=1 sh "$recipe" "$dist" "$host" "$work/foreign" "$work/obj" "$work/prefix"
mkdir "$work/dist"
printf 'corrupt archive\n' > "$work/dist/qtbase-everywhere-src-6.12.0.tar.xz"
reject checksum 'checksum mismatch' sh "$recipe" "$work/dist" "$host" "$work/source" "$work/obj" "$work/prefix"
[ ! -e "$work/source" ] && [ ! -e "$work/new" ] && [ ! -e "$work/obj" ] && [ ! -e "$work/prefix" ]
# The complete host builder must reject an interrupted Qtbase extraction too.
mkdir -p "$work/full/source/qtbase-everywhere-src-6.12.0"
: > "$work/full/inputs.txt"
full_recipe=$(dirname "$recipe")/build-host-tools.sh
reject full-proof 'Missing patched Qt scanner proof' env RESUME=1 \
    HOST_LLVM_BUILD="$work/not-configured-llvm" HOST_CLANG_BUILD="$work/not-configured-clang" \
    HOST_DBUS_PREFIX="$work/not-configured-dbus" \
    sh "$full_recipe" "$dist" "$work/full"
echo 'PASS: path, symlink, job, missing/changed resume and checksum and interrupted full-source rejection before work'
