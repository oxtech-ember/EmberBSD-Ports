# ELF absolute symbols

The ELF linker accepts repeated absolute definitions with equal values.
The carried LLVM 23 patch includes zero in this GNU ld compatibility rule.
An absent bitcode offset remains distinct from a known ELF offset of zero.
A prevailing bitcode definition also has no known absolute value yet.

Conflicting absolute values, section definitions and strong bitcode definitions
remain duplicate-symbol errors. This does not enable multiple definitions.
The patch changes an internal ELF interface; the installed driver API is unchanged.

Run this check from the Ports source root. Select the native LLVM prefix
and common AArch64 Binutils output:

```sh
python3 profiles/development-toolchain/cross/tests/lld-absolute.py \
    --llvm-prefix /absolute/native-prefix \
    --bfd-aarch64-ld /absolute/binutils/prefix/bin/aarch64--netbsd-ld \
    --work /absolute/new-check
```

The test checks x86-64 and AArch64 links, exact exit statuses, diagnostics,
ELF machine types and absolute symbol values. It checks both input orders
for bitcode conflicts. It does not execute target programs.

Keep the ordinary `tests` option enabled for the package's `check-lld` suite.
Static analysis and installed-consumer checks remain separate from these tests.

The Linux/Clang 23 native package passes `check-lld`: 3202 passed, 21 unsupported,
and one expected failure. The installed regression passes all 16 link cases.
Its 12 LLD cases also pass Valgrind with no memory errors or lost allocations.
Paired Clang Static Analyzer runs report the same three LLVM-header warnings.
An AArch64 kernel links with the installed package. Its hardware boot remains unverified.

Cppcheck 2.22 cannot complete these LLVM 23 translation units. Its Clang importer
asserts on both the original and patched `Symbols.cpp`. Its builtin parser also
rejects the native headers and the Clang-preprocessed translation unit.
These attempts do not establish a successful Cppcheck analysis.
