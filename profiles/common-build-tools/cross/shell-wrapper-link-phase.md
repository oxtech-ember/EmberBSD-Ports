# Shell wrapper compilation and link phases

The shared pkgsrc export patch keeps the framework's buildlink library search
path for CC and CXX links while omitting that injected path from compile,
preprocess, assembly, syntax-only and dependency-only invocations. Explicit
caller arguments remain subject to the existing wrapper transformations. The
scanner skips operands of supported separate driver options and stops at `--`;
`-MD` and `-MMD` alone do not suppress linking. The cwrappers route is unchanged.

`shell-wrapper-scan.py` checks the actual exported scanner, including operand
and `--` boundaries. `shell-wrapper-link-phase.py` checks generated wrappers
with selected target C and C++ compilers and an installed libdrm buildlink view.
