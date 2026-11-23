# DWARF format and expression acceptance

This suite exercises native GDB 18.1 on NetBSD 11/AArch64. Ports owns the
GDB adaptation and its debugger tests. The OS repository owns the separate
CTF converter and its type/symbol association limits, described in the
[OS CTF guide](https://github.com/oxtech-ember/EmberBSD/blob/main/external/cddl/osnet/dist/tools/ctf/cvt/docs/ctf-external-types.md).
These fixtures and local patches are AI-assisted EmberBSD work.

## Build and run

Generate target executables with the accepted GCC 16.2 cross compiler and
complete sysroot. The GCC16 CRT directory is selected explicitly.

```sh
sh profiles/development-toolchain/gdb/dwarf-variants-build.sh \
    /absolute/current-gcc16/bin/aarch64--netbsd-gcc \
    /absolute/sysroot /absolute/new-fixtures
```

The builder records compiler and ELF-reader versions and debug metadata.
GCC's cross prefix can contain the older bootstrap readelf. The target
acceptance uses the selected Binutils 2.47 `greadelf`; use that version for
location-list interpretation. Base CRT objects can carry older DWARF CUs
alongside the fixture CU, so an executable's first CU is not necessarily
the tested source unit.

Transfer the complete fixture directory and the target scripts to the AArch64
VM. Use the shared [LLVM family](../../common-build-tools/llvm-family.md),
including the corrected packaged `llvm-dwp` and `llvm-objcopy`.
The canonical DWP correction and its broader regression are described in
[the LLVM DWP tests](../../common-build-tools/cross/llvm-dwp-tests.md).
The accepted Binutils 2.47 build lacks zstd compression, so LLVM's object copier
creates the two zstd inputs.

```sh
OBJCOPY=/usr/pkg/bin/llvm-objcopy \
    sh dwarf-variants-package.sh /usr/pkg/bin/llvm-dwp /absolute/fixtures
sh dwarf-variants-target.sh /usr/pkg/bin/gdb /absolute/fixtures \
    /absolute/new-results
sh dwarf-variants-limits.sh /usr/pkg/bin/gdb /absolute/fixtures \
    /absolute/new-expression-results
sh dwarf-variants-ax.sh /usr/pkg/bin/gdb /absolute/fixtures \
    /absolute/new-agent-results
```

Packaging verifies that the DWP CU index contains both compilation units,
then removes only the generated standalone DWO inputs. The debugger runner
rejects a DWP case if any DWO remains in its directory. The original
cross-build path must not exist on the test target; do not mount it there.
Use a fresh build directory to regenerate inputs before repackaging.
On macOS, create transfer archives with `COPYFILE_DISABLE=1 tar --no-xattrs`
to avoid AppleDouble files being mistaken for standalone DWO inputs.

## Matrix

| Group | Cases | Required observation |
| --- | ---: | --- |
| C DWARF2/3/4/5, DWARF32/64, `-O0`/`-O2` | 16 | Two breakpoints, record members, scalar locals across a call, backtrace and normal exit |
| C++ DWARF4/5, DWARF32/64, type units | 4 | Signature-referenced template/inheritance types, optimized locals and normal exit |
| DWARF5 GNU and ELF zlib compression, DWARF32/64 | 4 | The same C debugging workflow using genuinely compressed sections |
| Separate `.gnu_debuglink`, DWARF32/64 | 2 | Stripped debug sections, external debug-file lookup and live values |
| DWARF4/5 indexed DWP, DWARF32/64 | 4 | Main-CU values and helper-CU argument at separate breakpoints, with no standalone DWO fallback |
| DWARF5 ELF zstd compression, DWARF32/64 | 2 | Compressed sections and the same live C workflow |

This is 32 compiler-produced debugging cases. Optimized cases verify actual
location lists and expressions, but do not enumerate every DWARF operation,
attribute, language or producer extension.

## Expression regression and local repair

`dwarf-variants-limits.S` supplies small, explicit DWARF5 units in both
DWARF32 and DWARF64. Every valid case must yield `variant_value == 42`.
The suite includes direct expressions, `DW_OP_call4`, same-CU and cross-CU
`DW_OP_call_ref`, constant `DW_OP_entry_value`, `DW_LLE_startx_length`,
`DW_LLE_startx_endx`, default locations and default/range precedence.
The cross-CU call enters a CU with the other offset width, performs a
CU-relative nested call and returns to another call in the original CU.
Malformed call operands and truncated default expressions must diagnose
truncation without crashing. There are 20 valid and four malformed cases.

The local `dwarf-variants-fixes.patch` adds `DW_OP_call_ref` to the expression
engine, symbol-requirement scanner and tracepoint expression compiler.
The called CU's context is restored after evaluation. It also adds
`DW_LLE_startx_endx` and default-location handling to the shared location
reader and location descriptions, with bounded expression lengths.
The lazy cross-CU lookup owns a symbol-expansion queue when invoked outside
symbol reading, processes it, and releases it before aging the CU cache.
Nested readers retain their caller's queue. The cross-CU fixture has no
address range in its second CU, so breakpoint lookup does not preload it.
The AX compiler independently bounds nested calls, frame-base expressions
and CFA expressions to 256 levels; tracepoint collection can bypass the
symbol-requirement scanner, so the scanner's guard is insufficient.
The patch also evaluates general [entry-value operands](entry-value.md) with
reconstructed register state and a separate nested stack. The patch has not
been submitted or accepted upstream. Compilation alone
is not acceptance; compare the installed debugger before and after it.

`dwarf-variants-ax.sh` adds 14 agent-compiler checks: eight successful
direct/same-CU/cross-CU translations and six recursive `call2`/`call4`/
`call_ref` cases. A discarded register expression makes the requirement
scanner stop before the recursive call. The test accepts only the specific
AX recursion diagnostic, proving the AX compiler itself rejected the loop.
No running inferior or trace-capable remote target is needed. The six
recursive ELF fixtures are additional to the 24 runtime-expression inputs.

The fixture semantics follow [DWARF5 sections 2.5 and 2.6](https://dwarfstd.org/doc/DWARF5.pdf)
and the [standard's corrections](https://dwarfstd.org/errata-dwarf5.html).
In particular, `call_ref` is section-relative inside the current executable
or shared object; it is not an arbitrary reference into another module.

## Remaining limits

General entry expressions and reconstructible register arithmetic are covered
by [the entry-value regression](entry-value.md). Historical memory without a
snapshot or matching `DW_AT_call_data_value`, missing register call values and
historical frame/TLS state remain unavailable. Current memory/register values
do not substitute for missing entry state.

The source also names narrower boundaries: skeletonless type units in DWP
without `.gdb_index`, `.debug_types` in an alternate/supplementary DWZ
object, and imported units within type units. Those source findings are
not executable coverage claims for this suite. Standalone supplementary
forms retain their separate acceptance in `test-target.sh`.

## Installed revision nb1

The clean cross-built GDB 18.1nb1 package passed all 32 format, 24 expression,
14 agent-compiler and 72 entry-value checks through `/usr/bin/gdb` in the
AArch64 UTM VM on 2026-10-08. Its installed ELF matches the archive and stage;
[package.md](package.md) records both hashes and the separate external/ABI
acceptance. The two earlier constant entry-value gaps now pass.

## Original package measurement

Native acceptance on NetBSD 11/AArch64 in UTM, 2026-10-08, used GCC 16.2.0
inputs and the installed `/usr/bin/gdb` wrapper for the GDB 18.1 package.
The installed ELF matched the rebuilt package and staged ELF:
`eb1c0bb10217764350b530fdf089b288f18a3ad913e0fa14da517645d9b55356`.
Package SHA256:
`a04fabdc497b7cc1f7a4c653d5834f545a47a36b92d17fede505fc9e8ef5419c`.

| Suite | Before the DWARF repair | Installed repair |
| --- | --- | --- |
| Compiler matrix | 30 PASS; both DWARF5 DWP cases fail | 32 PASS |
| Explicit expressions and malformed inputs | 6 PASS, 16 FAIL, 2 KNOWN_GAP | 22 PASS, 2 KNOWN_GAP |
| Agent-expression compiler | 4 PASS, 10 FAIL | 14 PASS |

Four additional DWP runs explicitly stopped in the helper CU and read
`*value == 41`, then continued to the main CU's second breakpoint and normal
exit. All four passed. The target runner includes this assertion for each
DWP case; the evidence preserves these later transcripts separately.

The original package exposed constant `DW_OP_entry_value` as two known gaps.
GDB 18.1nb1 removes that syntax restriction; the entry-value runner records its
separate RED/GREEN result. The expression runner now requires both constant
cases to return 42 and has no expected-gap exemption.

The unpatched AX recursion controls ran with CPU/core bounds and exposed
call2/call4 stack exhaustion. The repaired cases emit the specific AX
recursion-limit diagnostic. The archived evidence includes each transcript,
input index and hash. Archive SHA256:
`237d39d1d9365cd3bff91a468c51000069ed02164203261e31039059a7400381`.

No result here establishes universal DWARF conformance, physical-board
ptrace behavior, kernel core dumps or the complete upstream GDB testsuite.
