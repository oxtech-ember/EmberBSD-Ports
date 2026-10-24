# ANGLE AST GCC16 checks

The AI-assisted patch changes three translator source files and adds three
upstream regressions in two existing test files. Apply it with `-p1 -F0` from
the Chromium source root, after its pinned ANGLE checkout.

Checked constant-array allocation gains an explicit `size_t` destination for
`ValueOrDie()` before `new[]`. Overflow checking and element counts remain.
Statement insertion uses emplace with the same local pointer lvalue. It copies
the same non-owning pointer, preserving statement order and ownership while
avoiding an impossible const-reference vector alias-adjustment path.
The new tests check two independent constant values and front/middle/end
insertions with and without spare capacity.

Unary diagnostic naming checks the optional function descriptor directly.
Ordinary operators pass null and retain their operator string. The resolved
built-in caller passes its descriptor and retains the function name. A new
write-only unary-operator test complements the existing built-in regression.

## Saved stack diagnostic scope

The non-copyable rebuilder has three automatic NodeStackGuards. Each saves its
previous private ConsList, links to that live member, then restores the previous
list before destroying the saved member on every normal and early exit.
The constructor and destructor remain unchanged. A GCC16-only diagnostic
push/pop covers the constructor alone for the exact false positive described
in [GCC PR105867](https://gcc.gnu.org/pipermail/gcc-bugs/2022-June/789493.html).
The warning remains active elsewhere. No production compiler flag changes.

Upstream previously tried a [heap-backed repair](https://chromium.googlesource.com/angle/angle/+/a06cb3680fde6928fb4aa6fbec74544133e6401d).
It was [reverted for shader-compilation cost](https://chromium.googlesource.com/angle/angle/+/0eaaba0fdb80fb7d3c26420e1debbc3abd808136).
This patch retains the existing stack lifetime and introduces no allocation.
Retire the diagnostic scope when a compiler repair passes the production TU
and its real escaped-local control. No upstream fixed-version claim is made.

## Executed checks

All three original production GCC16 commands fail; all three patched commands
produce target AMD64 objects with their original flags. Both changed upstream
test translation units compile with the target configuration and bundled GTest.
Their target test suites have not executed.

A full target TU with a real escaped local after the pragma pop still fails
with exactly one dangling-pointer diagnostic. An extracted exact guard/ConsList
regression uses native GCC16 on Darwin ARM64. Original and patched guards pass
six-level traversal and every early-return depth. A missing-tail restoration
control returns 11. This is a host lifetime check, not target shader execution.

All six paired Clang Static Analyzer calls complete. IntermNode and Rebuild
remain clear. ParseContext findings decrease from four to three by removing
the null descriptor path. Three inherited findings remain unconfirmed. All six
Cppcheck inputs stop at dependency parser errors in math.h or libc++ traits;
this is incomplete analysis. These checks do not establish complete ANGLE,
GPU, Electron or Blanc acceptance.
