# GCC16 NetBSD cross TLS capability

Native NetBSD libstdc++ configuration runs `GCC_CHECK_TLS` and defines
`_GLIBCXX_HAVE_TLS`. Cross configuration selects a target branch in
`libstdc++-v3/crossconfig.m4`. Upstream calls `GCC_CHECK_TLS` in some
branches, for example GNU/Linux. The NetBSD/OpenBSD branch does not call it.
As a result, a cross-built runtime had no `HAVE_TLS`, unlike a native build of
the same recipe.

The two configurations select different `std::call_once` implementations.
With TLS, the inline code in `<mutex>` uses the thread-local
`std::__once_callable` and `std::__once_call`. Without TLS, it uses the global
`std::__once_functor` and its lock. Each library exports only the variables
of its own configuration. Both export `__once_proxy`.

| Configuration | Exported `call_once` variables and functions |
| --- | --- |
| TLS (native, repaired cross) | `std::__once_call`, `std::__once_callable` |
| Non-TLS (earlier cross) | `std::__once_functor`, `std::__get_once_functor_lock`, `std::__set_once_functor_lock_ptr` |

A consumer and its runtime must use the same configuration. On amd64,
LLVM 23 built with native GCC16 headers failed in the EmberBSD loader with
`Undefined symbol "_ZSt11__once_call"` against `gcc16-runtime-16.2.0nb4`.

## Compatibility

The repaired runtime matches native GCC16 on NetBSD. It is not compatible
with binaries that inline `std::call_once` from non-TLS cross headers. Such a
binary needs `std::__once_functor` and fails to load with the repaired
runtime. Rebuild packages that were compiled with `gcc16-16.2.0nb3` or earlier
cross headers. Also rebuild packages staged with `gcc16-runtime-16.2.0nb4` or
earlier. This applies to each target architecture that used an earlier cross
runtime. Binaries without `std::call_once` inline code are not affected.

## Repair

`patches/gcc-netbsd-tls.patch` adds two pkgsrc patches to `lang/gcc16`:

- `patch-libstdc++-v3_crossconfig_tls` calls the upstream `GCC_CHECK_TLS`
  in the NetBSD case, after the math checks. OpenBSD is unchanged.
- `patch-libstdc++-v3_configure_tls` is the matching generated `configure`
  delta from GNU Autoconf 2.69 (`sources.tsv`). It applies after
  `patch-libstdc++-v3_configure_math`.

The cross case of `GCC_CHECK_TLS` uses link tests with the selected target
compiler and sysroot. No cache answer is supplied. Native configuration does
not execute the cross branch, so its result is unchanged.

To reproduce the generated delta, run Autoconf 2.69 in `libstdc++-v3` of a
source tree prepared with the existing patches. The unchanged `configure` is
reproduced first, apart from pkgsrc's libstdc++ SONAME substitution. Apply the
new `crossconfig.m4` change and run Autoconf again.

The recipes advance to `gcc16-16.2.0nb4`, `gcc16-libs-16.2.0nb5` and the
runtime-only `gcc16-runtime-16.2.0nb5`. The runtime verifier requires the exact
TLS source patches and exactly one `#define _GLIBCXX_HAVE_TLS 1` in the staged
`c++config.h`. It records `GCC_RUNTIME_CXX_TLS_INPUTS_SHA256`. A nb4 stage
fails this check; build a new stage.

## Checks

```sh
python3 -B profiles/development-toolchain/runtime/tests/package-test.py \
    --sdk-source /absolute/EmberBSD-SDK
sh profiles/development-toolchain/tests/source-profile.sh
```

The package test removes and duplicates the TLS define. It also changes each
TLS patch. Each mutation must fail. The source profile applies the full delta
series to the pinned pkgsrc with zero fuzz. The [cross math check](cross-math.md)
removes the TLS and math configure deltas in reverse order for its baseline.

## Evidence

- An amd64 runtime build from a macOS host configured libstdc++ with
  `checking whether the target supports thread-local storage... yes`.
- `runtime.py check` accepted the `gcc16-runtime-16.2.0nb5` stage.
- `nm -D` of its `libstdc++.so.7` shows the TLS row of the table and no
  `__once_functor` symbols. The native GCC16 library has the same set.
- On a Jasper Lake amd64 laptop, LLVM 23 and Mesa 26 Iris built with native
  GCC16 headers loaded with this runtime. An EGL GBM probe passed three runs
  with hardware rendering.
