# LLVM 23 SPIR-V Translator

This recipe uses the stable [23.1.2 source tag](https://github.com/KhronosGroup/SPIRV-LLVM-Translator/releases/tag/v23.1.2).
The tag names commit `e65dde28ce8f12ef7245914fa2850260328669e4`.
It matches the common LLVM 23.1 family. LLVM 21 is not an alternative provider.

The package builds its shared library and command with GCC 16.2. It uses the
canonical SPIRV-Headers and SPIRV-Tools recipes. The header input is the pkgsrc
buildlink prefix. Upstream appends `include` to that prefix. CMake must not fetch
a second header tree.

The recipe enables the upstream lit suite. `make test` runs
`check-llvm-spirv`. Installed Clang supplies the frontend for shader translation
test inputs. It does not compile the package objects. The matching Python 3.15
lit package supplies the test driver. Preserve the full LLVM tool payload and
the SPIR-V assembler, disassembler, linker and validator for these tests.

Ordinary cross package builds do not run the test goal. A cross-built test
suite needs the target executable and matching target LLVM tools on the target
system. A metadata check does not establish that execution path.

Source hashes and install declarations do not qualify a package. Complete
normal packaging, installed library/command checks, the upstream suite and the
native Mesa shader consumer before accepting a new build.
