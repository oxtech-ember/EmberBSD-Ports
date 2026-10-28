# Common Clang Python bindings

The package installs the selected LLVM version's `clang` Python package and
license under `${PREFIX}/share/clang-python-bindings`. It invokes the common
`lang/clang` pkgsrc extract and patch phases in its own work directory, using
the same LLVM archive and complete Clang patch series. It does not build LLVM.
Point the selected host Python consumer at this directory and select the
matching `libclang` explicitly. No Python package download is needed.
