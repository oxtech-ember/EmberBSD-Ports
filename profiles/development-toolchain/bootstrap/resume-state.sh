#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Source from build.sh. Validate before changing a failed runtime build.
check_resume() {
    [ -f "$work/inputs.txt" ] && [ -d "$work/src" ] && [ -d "$work/build/gcc" ] && \
        [ -d "$work/stage" ] || fail 'Incomplete runtime work directory.'
    [ ! -e "$work/build-success" ] || fail 'Refusing to resume a completed runtime stage.'
    [ -z "$(find "$work/stage" -type f -o -type l)" ] || fail 'Resume requires an uninstalled runtime stage.'
    for resume_input in 'scope=runtime-only-bootstrap' "target=$target" "triplet=$triplet" \
        "seed_source=$origin" "kernel=$kernel" "sysroot=$sysroot" "math=$math" \
        "host_cc=${HOST_CC:-cc}" "host_cxx=${HOST_CXX:-c++}" \
        "host_cflags=${HOST_CFLAGS:--O2}" "host_cxxflags=${HOST_CXXFLAGS:--O2}"; do
        grep -Fqx "$resume_input" "$work/inputs.txt" || fail "Resume input changed: $resume_input"
    done
    resume_hashes=$(awk 'length($1) == 64 && $1 !~ /[^0-9a-f]/ && NF == 2 { print }' "$work/inputs.txt")
    [ -n "$resume_hashes" ] || fail 'Missing original input hashes.'
    printf '%s\n' "$resume_hashes" | shasum -a 256 -c --status || fail 'Original runtime inputs changed.'
    [ -x "$work/build/gcc/xgcc" ] || fail 'Missing completed host frontend.'
    [ "$("$work/build/gcc/xgcc" -dumpmachine)" = "$triplet" ] && \
        [ "$("$work/build/gcc/xgcc" -dumpfullversion)" = 16.2.0 ] || fail 'Runtime frontend target/version changed.'
    "$work/build/gcc/xgcc" -v 2>&1 | grep -qx 'Thread model: posix' || fail 'Resume requires the POSIX-thread frontend.'
}

backup_resume() {
    resume_backup=$(mktemp -d "$work/resume.XXXXXX") || fail 'Cannot preserve previous configure state.'
    cp "$work/inputs.txt" "$resume_backup/inputs.txt"
    for resume_log in configure.log frontends.log runtime-build.log runtime-install.log; do
        [ ! -f "$work/$resume_log" ] || cp "$work/$resume_log" "$resume_backup/"
    done
    # GCC configure prefers an existing executable ./nm before the supplied
    # NM_FOR_TARGET. Move that generated wrapper as well as its empty cache.
    # Keep every frontend and target object. Only generated configure state
    # and outputs that the failed ar/nm could have left are invalidated.
    for resume_state in gcc/Makefile gcc/config.cache gcc/nm \
        "$triplet/libgcc/Makefile" "$triplet/libgcc/config.cache" \
        "$triplet/libstdc++-v3/Makefile" "$triplet/libstdc++-v3/config.cache" \
        "$triplet/libgcc/libgcc.map" "$triplet/libgcc/tmp-libgcc.map" \
        "$triplet/libgcc/libgcc.a" "$triplet/libgcc/libgcc_eh.a" "$triplet/libgcc/libgcov.a"; do
        backup_generated "$resume_state"
    done
    for resume_library in "$work/build/$triplet/libgcc"/libgcc_s.so*; do
        [ ! -e "$resume_library" ] && [ ! -L "$resume_library" ] || \
            backup_generated "${resume_library#"$work/build/"}"
    done
    printf 'resume_prior_inputs_sha256=%s\nresume_backup=%s\n' \
        "$(shasum -a 256 "$resume_backup/inputs.txt" | awk '{print $1}')" "$resume_backup" >> "$work/inputs.txt"
}

backup_generated() {
    if [ -f "$work/build/$1" ] || [ -L "$work/build/$1" ]; then
        mkdir -p "$resume_backup/build/$(dirname "$1")"
        mv "$work/build/$1" "$resume_backup/build/$1"
    fi
}
