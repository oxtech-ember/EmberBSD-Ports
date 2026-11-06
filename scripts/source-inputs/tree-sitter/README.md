# Tree-sitter source

`source.py` prepares and verifies the common `textproc/tree-sitter` release
using the existing network archive owner. Select the SDK source, verified
pkgsrc export, archive, patch tool, and output explicitly; `--help` lists
options. The owner binds the effective recipe, including runtime pkg-config
metadata and public ABI headers.

Use `verify-source` before consumers build against a prepared tree. The
upstream CMake project compiles the runtime C sources and installs the public
header, shared/static libraries, and `tree-sitter.pc`.
