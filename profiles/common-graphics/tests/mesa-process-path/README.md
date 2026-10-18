# Mesa executable paths without procfs

MesaLib 26.2.4nb9 uses NetBSD's `KERN_PROC_PATHNAME` query for executable paths.
It rejects NULL, zero-size, failed, truncated and unterminated results.
Successful lengths exclude the terminating NUL. Other OS branches retain their code.

The regression applies the production patch to the checksum-pinned Mesa archive.
It compiles the exact upstream and patched function bodies with GCC16.
The host contract explicitly controls syscall results and simulates absent procfs.
It checks the MIB, buffer bounds, short and exact capacities, errors and NUL handling.
The upstream function fails the path assertion; the patched function passes.
This host boundary is separate from target execution.

```sh
CC=/absolute/native-gcc16 "$HOST_PYTHON315" tests/mesa-process-path/run.py \
  /absolute/mesa-26.2.4.tar.xz /absolute/sysroot \
  /absolute/aarch64--netbsd-gcc /absolute/new-work
```

The builder also produces `target-before` and `target-after` using real SDK headers.
Transfer these exact executables to the matching target. Record their hashes first.
Run each through an absolute path with `--require-no-proc` in a target without procfs.
The upstream probe must fail. The patched probe must pass.
Neither target probe substitutes syscalls or needs Mesa development tools installed.
They compare the native query with the executed path and check all short capacities.

Actual AArch64 VM execution passes this RED/GREEN contract without procfs.
The focused native contract passes ASan/UBSan and strict Memcheck with no live blocks,
errors or suppressions. Cppcheck, GCC `-fanalyzer` and Clang Static Analyzer report
no findings in the extracted function before or after the patch using host bindings.
The [Linux/GCC16 package receipt](../../cross/mesa-linux-aarch64.md) separately
records full nb9 packaging, installed CPU rendering and all 39 target invocations.
