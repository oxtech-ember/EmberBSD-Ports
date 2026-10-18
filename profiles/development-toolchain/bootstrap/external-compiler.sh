#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Existing POSIX GCC compiles target runtimes.
check_external_compiler() {
    [ "$resume" = no ] || [ "$resume" = support ] || fail 'External compiler mode does not support frontend resume.'
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
        printf 'support_target=gcc-leaf-metadata-v1\ntarget_objects=external-compiler\n'
        printf 'compiler=%s\ncc1=%s\ncc1plus=%s\n' "$kernel" "$external_cc1" "$external_cc1plus"
        shasum -a 256 "$cc" "$cxx" "$external_cc1" "$external_cc1plus"
    )
}

build_external_runtime() (
    # libgcc-support also installs compiler headers through fixincludes,
    # whose macro_list prerequisite builds cc1. Select metadata leaves only;
    # the authenticated external compiler owns its existing internal headers.
    "$make" -j"$jobs" configure-gcc all-libiberty all-libcpp all-libdecnumber \
        all-libbacktrace all-build-libiberty all-build-libcpp \
        all-build-fixincludes all-fixincludes \
        > "$work/support-host.log" 2>&1
    "$make" -C "$work/build/gcc" -j"$jobs" \
        "GCC_FOR_TARGET=$cc --sysroot=$sysroot" \
        libgcc.mvars tconfig.h machmode.h mode-classes.def version.h \
        > "$work/support-build.log" 2>&1
    for frontend in cc1 cc1plus; do
        [ ! -e "$work/build/gcc/$frontend" ] || fail 'External runtime mode unexpectedly built a frontend.'
    done
    # Upstream libgcc install-unwind_h-forbuild writes into this output dir.
    # It holds the newly built unwind header, not replacement compiler headers.
    mkdir -p "$work/build/gcc/include"
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
        printf 'support_target=gcc-leaf-metadata-v1\ntarget_objects=external-compiler\n'
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

check_external_support_resume() {
    check_runtime_libraries
    for support_input in "scope=runtime-only-external-compiler" "target=$target" "triplet=$triplet" \
        "seed_source=$origin" "compiler=$kernel" "sysroot=$sysroot" "math=$math" "jobs=$jobs" \
        "host_cc=${HOST_CC:-cc}" "host_cxx=${HOST_CXX:-c++}" \
        "host_cflags=${HOST_CFLAGS:--O2}" "host_cxxflags=${HOST_CXXFLAGS:--O2}" \
        "host_ar=${AR:-auto}" "host_nm=${NM:-auto}" "host_ranlib=${RANLIB:-auto}"; do
        grep -Fqx "$support_input" "$work/inputs.txt" || fail "Support resume input changed: $support_input"
    done
    # The closed leaf contract replaces only the historical support target.
    prior_compiler_state=$(sed 's/^support_target=libgcc-support$/support_target=gcc-leaf-metadata-v1/' "$work/external-compiler.txt")
    [ "$external_compiler_state" = "$prior_compiler_state" ] || fail 'External compiler changed before support resume.'
    grep -Fqx "CFLAGS_FOR_TARGET = $target_flags" "$work/build/Makefile" && \
        grep -Fqx "CXXFLAGS_FOR_TARGET = $target_flags" "$work/build/Makefile" && \
        grep -Fqx 'LDFLAGS_FOR_TARGET = -Wl,-rpath,/usr/pkg/gcc16/lib -Wl,-z,relro' "$work/build/Makefile" || fail 'Support target flags changed.'
    grep -Fqx "$(shasum -a 256 "$make")" "$work/inputs.txt" || fail 'Support GNU make provider changed.'
    support_action=resume
    [ "$check" != yes ] || support_action=check
    sh "$here/support-resume.sh" "$support_action" "$work"
}
