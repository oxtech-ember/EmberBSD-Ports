# V3D BO cache mutex lifecycle

MesaLib 26.2.4nb8 initializes the V3D BO cache mutex before publishing a screen.
It checks both screen mutex initializations and the handle-table allocation.
Creation errors release only resources already acquired.
Normal teardown drains cached BOs before destroying the mutexes.
The screen and its owned file descriptor also have explicit failure cleanup.

The pinned upstream leaves `bo_cache.lock` zero-initialized.
Its BO cache still calls `mtx_lock` on that object.
Zero-filled storage is not a portable initialized C11 mutex.
EmberBSD's pthread implementation rejects a mutex without its initialized magic value.
This patch does not alter GPU allocation limits or kernel buffer handling.

```sh
ruby run.rb /absolute/mesa-26.2.4.tar.xz /absolute/new-output
```

The runner verifies the archive SHA512 and the pkgsrc patch SHA1.
It extracts complete, unchanged bodies of `v3d_screen_create`,
`v3d_screen_destroy`, `v3d_bo_cache_free_all`, and `v3d_bufmgr_destroy`.
The real Mesa list implementation is retained.
Hardware, allocation, and unrelated screen services are explicit test doubles.
The mutex boundary uses real pthread mutexes and rejects uninitialized objects.
The baseline fails before an invalid mutex can reach cache operations.

Checks cover allocation, both mutex initializations, handle-table allocation,
device discovery, and performance-counter initialization failures.
Every failure is followed by a successful create/drain/destroy cycle.
The tests verify reverse destruction order and one close of the owned descriptor.
Both simulator selections run, with shader-cache code enabled in the native selection.
Five mutations remove initialization, ignore initialization failure, remove normal
or failure destruction, or destroy the cache mutex before draining BOs.
Each mutation must fail. Normal and strict ASan/UBSan checks pass.
These checks do not reproduce concurrent GPU execution or prove desktop stability.

The complete screen translation unit passes GCC 16.2 AArch64 compilation and
`-fanalyzer` with the accepted Mesa configuration and EmberBSD headers.
Cppcheck 2.22 also parses that configuration with GCC's actual predefined macros.
It reports the same five const/style suggestions in each screen version.
Shared Mesa and system headers have additional inherited style suggestions.
No warning, error, performance, or portability finding is reported.
The fixture has inherited const/style suggestions in its explicit boundaries.
No diagnostic category is disabled. Retain these findings with the build evidence.
Valgrind is unavailable on the macOS/arm64 host; ASan/UBSan are not Memcheck.

The simulator's existing allocator does not return an allocation error.
It dereferences its allocated file before returning it.
Its destroy function also changes global state without a null-object contract.
This patch calls it only after initialization returned normally.
Simulator allocation-failure handling remains outside this change.
The physical package uses `USE_V3D_SIMULATOR=0`.

## Complete package and native acceptance

The nb8 package uses GCC 16 and LLD 23.1.3 with shared LLVM 23.1.3.
Commit `3299874` preserves the libgallium symbol-version ABI for LLD.
GNU linkers retain their supported `--default-symver` path.
The fallback uses the same SONAME version node without changing API exports.
See the [linker regression](../mesa-symbol-version/README.md).

Normal CM5 installation verifies all 100 payload entries and the dependency graph.
SONAMEs, versioned API exports, two TLS symbols, and 26 public headers match nb7.
The same previously linked consumer returns 1,639 dispatch entries before and after upgrade.
Its VERNEED still resolves to the installed libgallium version node.

The installed package passes shader rejection, triangle pixels, four V3D EGL
lifecycles, and all 39 upstream test invocations. `Cache.List` is skipped.
Nine NIR cases remain disabled. These omissions are not successful test executions.
Fifteen temperature samples over 39 seconds range from 64.208 to 65.857 degrees Celsius.
No throttling or undervoltage flag is reported during that bounded run.
Use the [installed package runner](../../cross/mesa-package.md) to repeat the checks.

The accepted package SHA256 is
`8eb3e18747551374de7546cb9cd05af2906c4de1e6c6666ff22ad795ba573f0d`.
The 39-invocation bundle SHA256 is
`a266c5c9197da24b592e21854a57f2eaa62a843bc807b6a44749308660de2fb8`.

These checks do not establish sustained Plasma or physical HDMI presentation.
A separate startup diagnostic observes a bounded D-Bus reply delay on the main thread.
The shell responds after an additional wait and exits normally.
The cause of that delay remains under investigation; no GPU deadlock is established.
