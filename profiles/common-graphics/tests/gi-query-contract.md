# GI launcher host contract

Run `python3.15 gi-query-contract.py --sdk-source /absolute/EmberBSD-SDK [--target aarch64|amd64] CROSS_TOOLS NEW_WORK`.
Select CPython 3.15 and SDK API 1 explicitly. The SDK must provide
`PRODUCER_STREAM_API = 1`, `PRODUCER_INPUT_API = 1`, and
`PRODUCER_INSPECTION_API = 1`. The test records the interpreter path,
SHA256 and version. It uses only the Python standard library and the selected SDK.
The cross-tools directory must provide the selected GCC16 compiler and readelf.
The test creates real target ELF fixtures with `-nostdlib`. It checks provider
and transport guards. Injected SSH outcomes do not qualify target execution.
Use the real EmberBSD query guest for that separate acceptance boundary.

The contract checks the omitted, explicit `flat` and `prefix-bin` executable
layouts. Unknown values and non-string values fail before SSH. Transfer
archives retain the same ELF bytes and mode at `query` or `bin/query`, with
the same provider hashes in `lib`. Controlled statuses 0 and 7 preserve
separate streams, literal arguments, execution receipts and cleanup.
The production manifest/resource shell also runs with `prefix-bin`. These
controls do not execute target ELF or qualify LLVM metadata queries.

The production launcher reads target ELF headers and dynamic entries through the
SDK. The `readelf` configuration field remains required for recipe identity
compatibility. It must name a regular executable file. Both contracts reject
an executable directory before SSH. The launcher does not use readelf to parse
the target files.

Run the companion `python3.15 pixbuf-query-contract.py --sdk-source /absolute/EmberBSD-SDK [--target aarch64|amd64] CROSS_TOOLS NEW_WORK`.
It builds its own GCC16 ELF provider, program and loader module. Eighteen
controlled transport and local refusal scenarios cover loader/MIME output, private paths,
source changes, failure status and cleanup. Two host guards reject another
Python version or implementation before configuration or transport.
These are host contracts. Real target loading and the complete upstream
scanner and Pixbuf suites remain separate checks.

Each production SSH command has a 180-second output timeout. This includes
allocation, transfer, query, status readback, XML readback and cleanup. The SDK
owns and drains the host process session. Each empty-session proof has a
separate 30-second inspection budget. Unknown rows still prevent proof and
cause refusal. SDK stop grace periods apply after interruption. Each stdout capture is limited to
16 MiB. Stderr is limited to 1 MiB. Truncation is an infrastructure failure;
it cannot become a legitimate negative configure result. GI XML overflow and
stderr truncation retain a transfer receipt and do not publish the dump.
The remote target query keeps its separate 60-second timeout and 5-second
termination grace period.

The GI bmake fixture checks the published `EMBERBSD_GI_PYTHON` alias and the
common `EMBERBSD_CROSS_BUILD_PYTHON` selector. Equal providers are accepted.
Different providers are refused. Pixbuf controls verify the selected SSH host
key alias and reject malformed UTF-8 in cache comments and loader output.

Run `python3.15 gdk-pixbuf-guards.py --sdk-source /absolute/EmberBSD-SDK SOURCE HOST_PYTHON SYSROOT READELF NEW_WORK`
for the complete companion guard set. It retains 23 local refusals, 12 mocked
loader/MIME transports, three native executions of the production shell hash
loops and two upstream printer controls. `SOURCE` must contain the verified
patched `build-aux/gen-thumbnailer.py`; it need not contain a completed package
build. The shell controls use a native timeout stub. They never execute target
ELF. The guards retain source hashes, phase logs and the MIME cache hash receipt.

The production GI, Pixbuf and execute launchers pass `-E -S` to the selected
host Python. These tools use only the standard library and the explicitly
selected SDK. They must ignore pkgsrc's target `PYTHONPATH` and its
`sitecustomize.py`. The GI contract loads an actual platform-changing site
as a negative control. It then uses the recipe's isolated launcher for
preflight and a bounded transport probe. The target `LD_LIBRARY_PATH` and
literal target arguments remain available to the helper.

The thumbnailer generator retains `--runner PYTHON SCRIPT`. It inserts
`-E -S` into its helper subprocess argv. Two generator controls use literal
paths with spaces, a target `sitecustomize.py`, and printer statuses 0 and 7.
Only status 0 may publish thumbnailer metadata.
