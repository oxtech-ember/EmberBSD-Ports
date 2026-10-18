#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Existing POSIX GCC compiles target runtimes.
check_external_compiler() {
    [ "$resume" = no ] || fail 'External compiler mode does not support frontend resume.'
    [ "$runtime_gomp$runtime_atomic" = nono ] || fail 'External compiler mode currently builds libgcc and libstdc++ only.'
    for compiler in "$cc" "$cxx"; do
        compiler_version=$("$compiler" -v 2>&1) || fail 'Cannot identify external compiler.'
        printf '%s\n' "$compiler_version" | grep -qx 'Thread model: posix' || fail 'External compiler must use POSIX threads.'
    done
    external_cc1=$("$cc" -print-prog-name=cc1)
    external_cc1plus=$("$cxx" -print-prog-name=cc1plus)
    compiler_root=$(realpath "$kernel") || fail 'Cannot resolve compiler prefix.'
    for frontend in "$external_cc1" "$external_cc1plus"; do
        [ -x "$frontend" ] || fail 'External compiler frontend is missing.'
        resolved=$(realpath "$frontend") || fail 'Cannot resolve compiler frontend.'
        case "$resolved" in "$compiler_root"/*) ;; *) fail 'External compiler frontend escapes its prefix.';; esac
    done
    external_cc1=$(realpath "$external_cc1")
    external_cc1plus=$(realpath "$external_cc1plus")
    external_compiler_state=$(
        printf 'compiler_mode=external-posix\nversion=16.2.0\ntriplet=%s\nthread_model=posix\n' "$triplet"
        printf 'support_target=libgcc-support\ntarget_objects=external-compiler\n'
        printf 'compiler=%s\ncc1=%s\ncc1plus=%s\n' "$kernel" "$external_cc1" "$external_cc1plus"
        shasum -a 256 "$cc" "$cxx" "$external_cc1" "$external_cc1plus"
    )
}

build_external_runtime() (
    # Top-level target-library rules depend on all-gcc. Use the upstream
    # support target, then configure each target library directly instead.
    "$make" -j"$jobs" configure-gcc all-libiberty all-libcpp all-libdecnumber \
        all-libbacktrace all-build-libiberty all-build-libcpp \
        all-build-fixincludes all-fixincludes \
        > "$work/support-host.log" 2>&1
    "$make" -C "$work/build/gcc" -j"$jobs" \
        "GCC_FOR_TARGET=$cc --sysroot=$sysroot" libgcc-support \
        > "$work/support-build.log" 2>&1
    for frontend in cc1 cc1plus; do
        [ ! -e "$work/build/gcc/$frontend" ] || fail 'External runtime mode unexpectedly built a frontend.'
    done
    build_triplet=$(sh "$work/src/config.guess")
    export CC="$cc --sysroot=$sysroot -B$work/build/gcc/"
    # Use the C driver for C++ so it does not inject an old libstdc++ at link.
    export CXX="$cc --sysroot=$sysroot -B$work/build/gcc/ -shared-libgcc -nostdinc++"
    export CFLAGS="$target_flags" CXXFLAGS="$target_flags" CPPFLAGS=
    export AR="$AR_FOR_TARGET" AS="$AS_FOR_TARGET" LD="$LD_FOR_TARGET" NM="$NM_FOR_TARGET"
    export OBJCOPY="$OBJCOPY_FOR_TARGET" OBJDUMP="$OBJDUMP_FOR_TARGET"
    export RANLIB="$RANLIB_FOR_TARGET" READELF="$READELF_FOR_TARGET" STRIP="$STRIP_FOR_TARGET"
    export LDFLAGS="-L$work/stage/usr/pkg/gcc16/lib -Wl,-rpath,/usr/pkg/gcc16/lib -Wl,-z,relro"
    {
        printf 'support_target=libgcc-support\ntarget_objects=external-compiler\n'
        printf 'CC=%s\nCXX=%s\nLDFLAGS=%s\n' "$CC" "$CXX" "$LDFLAGS"
    } > "$work/external-runtime-plan.txt"
    for library in libgcc libstdc++-v3; do
        directory=$work/build/$triplet/$library
        mkdir -p "$directory"
        cd "$directory"
        set -- --build="$build_triplet" --host="$triplet" --target="$triplet" \
            --with-cross-host="$build_triplet" --with-target-subdir="$triplet" \
            --prefix=/usr/pkg/gcc16 --libdir=/usr/pkg/gcc16/lib \
            --with-toolexeclibdir=/usr/pkg/gcc16/lib \
            --disable-multilib --enable-shared --enable-threads=posix --disable-nls
        if [ "$library" = libstdc++-v3 ]; then
            set -- "$@" --with-gxx-include-dir=/usr/pkg/gcc16/include/c++ \
                --enable-long-long --disable-libstdcxx-pch --disable-libssp
        fi
        "$work/src/$library/configure" "$@" > "$work/$library-configure.log" 2>&1
        # Configure must retain the exact external target compiler command.
        grep -Fx "CC = $CC" Makefile >/dev/null || fail 'Target library lost the selected external compiler.'
        "$make" -j"$jobs" all > "$work/$library-build.log" 2>&1
        "$make" "DESTDIR=$work/stage" install > "$work/$library-install.log" 2>&1
    done
)
