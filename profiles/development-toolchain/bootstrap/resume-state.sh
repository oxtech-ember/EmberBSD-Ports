#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Source from build.sh. Validate before changing a failed runtime build.
check_resume() {
    [ -f "$work/inputs.txt" ] && [ -d "$work/src" ] && [ -d "$work/build/gcc" ] && \
        [ -d "$work/stage" ] || fail 'Incomplete runtime work directory.'
    [ ! -e "$work/build-success" ] || fail 'Refusing to resume a completed runtime stage.'
    if [ "$resume" != runtime ]; then
        [ -z "$(find "$work/stage" -type f -o -type l)" ] || fail 'Resume requires an uninstalled runtime stage.'
    fi
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
    if [ "$resume" = runtime ]; then
        grep -qx 'target_binutils=audited-kernel-prefix' "$work/inputs.txt" || fail 'Runtime-only resume requires the explicit target-binutils receipt.'
        for resume_frontend in $frontend_files; do
            [ -s "$work/build/gcc/$resume_frontend" ] || fail "Missing frontend state: $resume_frontend"
        done
        for resume_driver in cc1 cc1plus; do
            [ -x "$work/build/gcc/$resume_driver" ] || fail 'Missing completed language frontend.'
        done
    fi
}

frontend_files='Makefile config.cache config.status config.log auto-host.h configargs.h xgcc cc1 cc1plus'

verify_frontend_state() {
    shasum -a 256 -c --status "$resume_backup/frontend.sha256" || fail 'Completed frontend state changed during runtime-only recovery.'
}

verify_runtime_stage() {
    (cd "$resume_backup/stage" && find . -print | LC_ALL=C sort) > "$resume_backup/stage.inventory.check"
    cmp -s "$resume_backup/stage.inventory" "$resume_backup/stage.inventory.check" || fail 'Partial-stage inventory changed.'
    (cd "$resume_backup/stage" && find . -type l -exec sh -c 'for path do printf "%s\t%s\n" "$path" "$(readlink "$path")"; done' sh {} + | LC_ALL=C sort) > "$resume_backup/stage.symlinks.check"
    cmp -s "$resume_backup/stage.symlinks" "$resume_backup/stage.symlinks.check" || fail 'Partial-stage symlinks changed.'
    resume_preserved_count=$(find "$resume_backup/stage" -type f | wc -l | tr -d ' ')
    [ "$resume_preserved_count" = "$(wc -l < "$resume_backup/stage.sha256" | tr -d ' ')" ] || fail 'Incomplete preserved-stage checksums.'
    if [ "$resume_preserved_count" = 0 ]; then
        [ ! -s "$resume_backup/stage.sha256" ] || fail 'Unexpected empty-stage checksum data.'
    else
        (cd "$resume_backup/stage" && shasum -a 256 -c --status ../stage.sha256) || fail 'Partial-stage preservation failed.'
    fi
    rm "$resume_backup/stage.inventory.check" "$resume_backup/stage.symlinks.check"
}

backup_runtime_resume() {
    resume_backup=$(mktemp -d "$work/resume-runtime.XXXXXX") || fail 'Cannot preserve runtime installation.'
    cp "$work/inputs.txt" "$resume_backup/inputs.txt"
    for resume_log in configure.log frontends.log frontend-version.txt runtime-build.log runtime-install.log; do
        [ ! -f "$work/$resume_log" ] || cp "$work/$resume_log" "$resume_backup/"
    done
    for resume_top in Makefile config.status config.log config.cache; do
        [ ! -f "$work/build/$resume_top" ] || cp "$work/build/$resume_top" "$resume_backup/top-$resume_top"
    done
    for resume_frontend in $frontend_files; do
        shasum -a 256 "$work/build/gcc/$resume_frontend"
    done > "$resume_backup/frontend.sha256"
    (cd "$work/stage" && find . -type f -exec shasum -a 256 {} + | LC_ALL=C sort) > "$resume_backup/stage.sha256"
    (cd "$work/stage" && find . -type l -exec sh -c 'for path do printf "%s\t%s\n" "$path" "$(readlink "$path")"; done' sh {} + | LC_ALL=C sort) > "$resume_backup/stage.symlinks"
    (cd "$work/stage" && find . -print | LC_ALL=C sort) > "$resume_backup/stage.inventory"
    resume_file_count=$(find "$work/stage" -type f | wc -l | tr -d ' ')
    [ "$resume_file_count" = "$(wc -l < "$resume_backup/stage.sha256" | tr -d ' ')" ] || fail 'Incomplete partial-stage checksums.'
    mv "$work/stage" "$resume_backup/stage"
    verify_runtime_stage
    mkdir "$work/stage"
    # Configure every existing target-library prerequisite again, not GCC.
    # libtool .la/.lai files embed the old installation directory. Keep target
    # objects, archives and DSOs; upstream make rebuilds their metadata/links.
    find "$work/build/$triplet" \( -type f -o -type l \) \
        \( -name Makefile -o -name config.cache -o -name config.status -o -name config.log \
        -o -name libtool -o -name '*.la' -o -name '*.lai' \) -print > "$resume_backup/target-metadata.paths"
    while IFS= read -r resume_metadata; do
        backup_generated "${resume_metadata#"$work/build/"}"
    done < "$resume_backup/target-metadata.paths"
    printf 'resume_runtime_prior_inputs_sha256=%s\nresume_runtime_backup=%s\nruntime_toolexeclibdir=/usr/pkg/gcc16/lib\n' \
        "$(shasum -a 256 "$resume_backup/inputs.txt" | awk '{print $1}')" "$resume_backup" >> "$work/inputs.txt"
    shasum -a 256 "$resume_backup/frontend.sha256" "$resume_backup/stage.sha256" \
        "$resume_backup/stage.symlinks" "$resume_backup/stage.inventory" \
        "$resume_backup/target-metadata.paths" >> "$work/inputs.txt"
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
