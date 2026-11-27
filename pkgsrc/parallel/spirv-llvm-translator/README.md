# LLVM 23 SPIR-V Translator

This recipe uses the [23.1.3 source tag](https://github.com/KhronosGroup/SPIRV-LLVM-Translator/releases/tag/v23.1.3).
The tag names commit `db5855d76a0ff33228bcf48032b350b25dcdbcf2`. Use LLVM 23.1.

The selected SDK compiler builds the shared library and the `llvm-spirv` command.
The SPIRV-Headers and SPIRV-Tools packages provide the headers and tools.
CMake reads the headers from the pkgsrc buildlink prefix.

For release testing, set `PKG_OPTIONS.spirv-llvm-translator+=tests` before configuration.
Run `bmake test` to execute `check-llvm-spirv`. Clang compiles shader test inputs.
Python lit runs the suite with the LLVM and SPIR-V tools.
Run cross-built tests on the target system with the matching target tools.

Source hashes and install declarations do not qualify a package. Complete
normal packaging, installed library/command checks, the upstream suite and the
native Mesa shader consumer before accepting a new build.
