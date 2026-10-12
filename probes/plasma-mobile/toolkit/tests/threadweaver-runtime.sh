#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), installed ThreadWeaver API and upstream tests.
set -eu
[ "$#" = 2 ] || { echo 'Usage: threadweaver-runtime.sh UPSTREAM_BINARIES NEW_OUTPUT' >&2; exit 2; }
binaries=$(CDPATH= cd -- "$1" && pwd)
mkdir "$2"
work=$(CDPATH= cd -- "$2" && pwd)
PATH=/usr/pkg/bin:/usr/pkg/sbin:/usr/bin:/usr/sbin:/bin:/sbin; export PATH
umask 077
mkdir "$work/home" "$work/runtime"
sysctl kern.boottime > "$work/boot.before"
pkg_info -e kf6-threadweaver > "$work/package.txt"
failed=0
for name in ThreadWeaverJobTests ThreadWeaverSequencesTests ThreadWeaverQueueTests \
    ThreadWeaverLifecycleTest ThreadWeaverShutdownOnQApplicationQuitTest \
    ThreadWeaverQueueFactoryTest ThreadWeaverDeleteTest; do
    [ -x "$binaries/$name" ] || exit 2
    result=0
    timeout -k 5 120 env -i PATH="$PATH" LC_ALL=C.UTF-8 HOME="$work/home" \
        XDG_RUNTIME_DIR="$work/runtime" QT_QPA_PLATFORM=minimal \
        "$binaries/$name" > "$work/$name.log" 2>&1 || result=$?
    printf '%s %s\n' "$name" "$result" >> "$work/status.txt"
    tail -n 3 "$work/$name.log"
    sha256 "$binaries/$name" >> "$work/tests.sha256"
    ldd "$binaries/$name" > "$work/$name.ldd"
    [ "$result" = 0 ] || failed=1
done
# Both installed header spellings are public API. A case-insensitive host
# must preserve both directory names in the package for this target.
cat > "$work/headers.cc" <<'CPP'
#include <ThreadWeaver/Job>
#include <threadweaver/job.h>
#include <type_traits>
static_assert(std::is_class_v<ThreadWeaver::Job>);
int main() { return 0; }
CPP
/usr/pkg/gcc16/bin/g++ -std=c++17 -fPIC -fsyntax-only \
    -I/usr/pkg/include/KF6/ThreadWeaver -I/usr/pkg/qt6/include \
    -I/usr/pkg/qt6/include/QtCore "$work/headers.cc" > "$work/headers.log" 2>&1
sysctl kern.boottime > "$work/boot.after"
cmp "$work/boot.before" "$work/boot.after" || failed=1
[ "$failed" = 0 ] || exit 1
echo 'PASS: installed ThreadWeaver queues and both public header directory spellings'
