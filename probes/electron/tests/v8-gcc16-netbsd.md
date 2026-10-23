# V8 GCC16 NetBSD regression

The regression replays exact production compiler commands from a generated
NetBSD x64 Electron GN graph. The pinned baseline must fail on the atomic-load
constructor error, the unused pointer-table label, the signed comparison, the
`HeapGrowingMode` alias, and GCC's unsupported `nodebug` attribute. The patch
must make all four production translation units compile with GCC16 and
`-Werror`.

The first source change provides the default result storage required by GCC's
generic atomic builtin. `TaggedPayload` stays trivially copyable, and the
pointer table remains one word. The second change marks a Linux-oriented label
unused when the target cannot name virtual memory ranges. The third uses an
unsigned shift operand in the Karatsuba heuristic; the guarded shift is within
the width of `uint32_t`. The fourth qualifies the enum type in the public
`Heap` alias. The fifth uses `nodebug` only when the compiler supports it.

Run `v8-gcc16-netbsd.py` as documented in [the test index](README.md). It uses
isolated source overlays and writes only below a new work directory. It needs
the exact Chromium/V8 pins, the generated NetBSD x64 GN output, the canonical
SDK workspace/sysroot, and the selected GCC16 compiler. It checks the original
diagnostics before accepting the patched compile. It does not compile or link
the complete V8 library.
