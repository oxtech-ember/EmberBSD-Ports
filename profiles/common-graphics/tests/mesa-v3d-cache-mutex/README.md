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

Full package checks, installed ABI checks, repeated native rendering, and the
complete Plasma session remain separate acceptance steps.

The LLD package also retains the installed libgallium symbol-version ABI.
See the [linker regression](../mesa-symbol-version/README.md).
