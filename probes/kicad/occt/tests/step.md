# Installed OCCT8 STEP geometry contract

This consumer uses the installed `TKDESTEP` toolkit. It creates a 1 by 2 by 3
box and checks the source BRep. A separate STEP writer transfers and writes it.
A new reader reads the file and transfers its single root back to a shape.
The reader never receives the source shape or writer session.

Both shapes must be valid and contain exactly one solid. Their bounds must be
`(0,0,0)` to `(1,2,3)` within an absolute `1e-7` coordinate tolerance.
`AddOptimal` disables triangulation and shape-tolerance expansion.
The source volume must be 6 within `1e-12`. The readback volume must equal the
independently supplied expected value within `1e-8`. The volume computation
uses closed geometry and does not use triangulation.

Configure with an installed OCCT 8.0.1 prefix and the common GCC16 toolchain:

```sh
cmake -S probes/kicad/occt/tests -B /absolute/new-step-consumer \
    -DCMAKE_TOOLCHAIN_FILE=/absolute/aarch64-gcc16.cmake \
    -DCMAKE_PREFIX_PATH=/absolute/installed-prefix \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
    -DEMBERBSD_OCCT_STEP=ON -DEMBERBSD_OCCT_STEP_UBSAN=ON
cmake --build /absolute/new-step-consumer --target occt-step
```

The option defaults to off, so Foundation-only historical core checks retain
their original requirements. When enabled, the test requires GCC16 and the real
imported OCCT8 targets `TKPrim`, `TKTopAlgo` and `TKDESTEP`. It does not select
legacy `TKSTEP` or source-tree headers. The optional UBSan trap mode instruments
only this consumer. It does not instrument the installed shared dependencies.

Execute only in an authorized target acceptance environment. Use a private,
writable working directory and an external bounded execution controller.
The consumer creates its own directory there. It removes only its exact STEP
file and directory. The controller must also confirm remote cleanup.

| Arguments | Required status | Independent witness |
| --- | --- | --- |
| `roundtrip 6` | 0 | `STEP_TRANSFER_DONE roots=1 shapes=1`, `STEP_ROUNDTRIP_PASS`, `owned_fixture_cleanup=0` |
| `roundtrip 5` | 1 | Real STEP transfer completes. Readback reports `expected=5` and rejects its volume. Cleanup is zero. |
| `malformed` | 0 | The real reader rejects a non-STEP file and prints `STEP_READ_REFUSED mode=malformed`. Cleanup is zero. |
| `missing` | 0 | No input file is created. The real reader prints `STEP_READ_REFUSED mode=missing`. Cleanup is zero. |

The two refusal modes pass only when the reader returns a non-success status.
An unexpected successful read fails the test. A diagnostic or signal alone
does not satisfy either refusal witness.

Use the production `target-query.py --execute` runner for target execution.
Set its private `build_root` to contain the consumer and its failure marker.
Declare the installed files from `share/opencascade/resources/SHMessage`,
`XSMessage`, `StdResource` and `XSTEPResource` as hashed `execute_inputs` below
`data/occt/`. Preserve the original bytes. Map `CSF_SHMessage`, `CSF_XSMessage`
and `CSF_STEPDefaults` to their stage directories. Map `CSF_StandardDefaults`,
`CSF_PluginDefaults`, `CSF_XCAFDefaults` and `CSF_StandardLiteDefaults` to
`data/occt/StdResource`. Map `CSF_OCCTResourcePath` to `data/occt` and set
`CSF_LANGUAGE` to the language literal `us`. These process-local settings follow
the upstream `adm/templates/env.sh` resource layout. Do not source that script
into the target's global environment. See the
[execute-data contract](../../../../profiles/common-graphics/cross/introspection.md#compiled-configure-probes).

The consumer cross-build passes against the ordinary installed OCCT 8.0.1
package with the common GCC16.2 compiler and the real CMake imported targets.
The captured compilation database selects GNU++20 and retains the installed
feature definitions, `-O3`, `-DNDEBUG`, warnings and UBSan trap flags. The
AArch64 ELF requires `libTKDESTEP.so.8.0`, has RELRO and uses the target RPATH
`/usr/pkg/lib:/usr/pkg/gcc16/lib`. It has no `libubsan` runtime dependency.

Clang Static Analyzer 21.0.0 reports no diagnostics for the consumer with the
actual definitions, installed headers, GCC16 C++ headers and explicit GNU++20.
The input inventory records 484 source/header entries and real header-link
provenance. Cppcheck 2.22.0 cannot analyze this translation unit: its normal
parser rejects the exact GCC16 preprocessing at NetBSD `sys/endian.h:74`;
its supported experimental Clang AST import rejects an invalid `scratch space`
location. Both refusals are retained. No headers or diagnostic categories were
changed, and no clean Cppcheck result is claimed. This is a new EmberBSD-owned
consumer; it does not patch OCCT library source.

All four cases pass in an AArch64 EmberBSD guest with the installed OCCT 8.0.1
package. The accepted consumer ELF SHA256 is
`468565e48ee227327425ddbb9c168fad18edad0edca5f3d19771bc843876d7c6`.
The production runner verifies the ELF/provider closure and 16 original resource
files, with a total of 85,108 resource bytes. Each case verifies remote hashes
before and after execution. Each case removes its fixture and transfer directory.

The successful readback reports volume 6. The wrong expected volume 5 fails
with status 1 after the real transfer and readback. The malformed and missing
inputs reach the real reader and report refusal statuses 3 and 2. These modes
return status 0 because refusal is their required outcome. No case sets an
infrastructure failure marker.

UBSan trap instrumentation covers the consumer and its compiled inline code;
it does not instrument the installed shared dependencies. This is not a
Valgrind or ASan result. This box contract does not accept a complete STEP
assembly, shell closure, meshing, KiCad STEP import, GUI operation, a physical
device or whole-library memory behavior.
