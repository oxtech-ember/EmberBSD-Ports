# CMake Mach-O architecture reader

The common CMake 4.4.4nb1 patch uses one deployment-target condition for the
`mach-o/utils.h` header and `macho_arch_name_for_cpu_type`. GCC16 does not
implement Clang's `__builtin_available` extension. The pre-macOS-13 branch
continues to use `NXGetArchInfoFromCpuType`. The CMake BSD license is unchanged.

Use a real native GCC16 bootstrap compilation entry for `Source/cmMachO.cxx`.
Save the materialized compiler arguments after pkgsrc wrappers. The entry
must use an initial deployment target of macOS 13 or later. Preserve the
generated bootstrap headers and the selected SDK. Use a one-entry standard
compilation database with `arguments`, `directory` and `file` fields.

```sh
python3 -B check.py \
    --sdk-source /absolute/EmberBSD-SDK \
    --compile-commands /absolute/compile_commands.json \
    --baseline /absolute/original/cmMachO.cxx \
    --candidate /absolute/patched/cmMachO.cxx \
    --cxx /absolute/g++-16 \
    --sysroot /absolute/MacOSX.sdk \
    --read-root /absolute/native-prefix \
    --read-root /absolute/cmake-work \
    --read-root /absolute/source-inputs \
    --lock-root /absolute/lock-root \
    --output /absolute/new-regression-output
```

The Python orchestrator uses only the standard library and explicit SDK API 1.
It retains each actual command, status and output hash. The baseline must fail
on the unsupported builtin. The candidate must compile and link the complete
translation unit. Both original and patched files must also compile with a
macOS 12 deployment target. No diagnostics are disabled.

Each of the three native programs checks eight independent binary fixtures:
arm64, arm64e, x86_64, an ordered universal file, an unknown CPU, a dylib name,
invalid magic and a truncated header. The system `lipo` independently checks
the four supported architecture fixtures. The driver also checks validity,
error messages and the header count. Original and patched pre-13 programs
must produce the same expected outputs.

These checks run on the current host. A lower deployment flag does not prove
execution on an older macOS release. The check does not establish a complete
CMake package, the full upstream suite, Valgrind or whole-package memory safety.
Paired Cppcheck and Clang Static Analyzer checks use the affected module's
actual flags, generated headers, SDK and measured native ABI. Keep compiler
header parser limitations separate from successful analyzer results.
