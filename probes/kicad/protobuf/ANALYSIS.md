# Protobuf native validation

This record covers the restored protobuf 36.2 sources and local fixes.
The source archives are pinned in `sources.sha256`.
The checks below ran on the native x86_64 Linux build host on 2026-10-18.
They do not establish AArch64 execution or KiCad acceptance.

The native build uses GCC 16.2.0, shared Abseil 20260817.0 and the common
shared zlib 1.3.2 provider. It retains gzip-stream support.
The zlib runtime SHA256 is
`f478c019f930497878761d9c768c6c613d515571a7104c232bf1a48f592af34f`.
The first interrupted configuration used host zlib 1.3.1.
Its log remains available and is not the accepted provider configuration.

## Source and path analysis

Cppcheck 2.22.0 used the actual native compilation database, GCC16 builtin
values, the selected standard and native include paths. No diagnostic category
was suppressed. GCC analysis added `-fanalyzer` to the actual C command.
Clang 19.1.7 analyzed the C++ command with the actual GCC16 C++ headers.

| Scope | Baseline | Patched | Interpretation |
| --- | --- | --- | --- |
| `upb/message/copy.c`, Cppcheck, C23 | 22 findings | 20 findings | The repeated-field failure check no longer has an always-false condition. See the classifications below. |
| `upb/message/copy.c`, GCC16 analyzer | No diagnostics | No diagnostics | Runtime allocation-failure tests are still necessary. |
| `upb/message/copy.c`, Clang analyzer, C23 | One null-minitable warning | No diagnostics | The baseline path models inconsistent field types; it is not causal allocation-failure evidence. |
| `compiler/main.cc`, Clang analyzer, C++17 | Two dead-store warnings | The same two warnings | Both are in upstream `parse_context.h`; neither concerns CLI teardown. |
| `compiler/main.cc`, Cppcheck | Incomplete | Incomplete | Tool limitation with the real GCC16 headers; this is not a clean result. |
| Installed C consumer, Cppcheck, C23 | Not applicable | 24 findings | Const/style suggestions, intentional alignment members and the same pointer-union warning. |
| Installed C consumer, GCC16 analyzer | Not applicable | One uninitialized-value warning | Getter union-copy modeling limitation, explained below. |
| Installed C and C++ consumers, Clang analyzer | Not applicable | No diagnostics | Actual installed headers and compiler flags. |
| Installed C++ consumer, Cppcheck | Not applicable | Incomplete | Namespaced feature-query limitation in the actual Abseil headers. |

The remaining `copy.c` findings are two redundant `break` statements,
six pointer-to-const suggestions, eleven parameter-to-const suggestions and
one `pointerSize` warning. The warning is a false positive in
`upb/mini_table/internal/message.h`: the code copies exactly one pointer-sized
union representation into a pointer-sized destination. The adjacent static
assert verifies the representation size. The const and redundant-statement
items are upstream style work outside this allocation-failure repair.

The C consumer has nine local style/alignment findings and fifteen findings in
installed UPB headers. The `max_align_t` union members intentionally align the
arena storage; they do not need a runtime read. The pointer-to-const suggestions
and empty-loop style finding do not change the fault-injection behavior.

GCC reports `value.size` as uninitialized at `has_scalar_text` through
`upb_Message_GetString`. This is a model false positive for this fixture's actual
`DescriptorProto.name` field: the generated minitable selects
`kUpb_FieldRep_StringView`, the getter sets `def.str_val`, and both getter paths
copy `sizeof(upb_StringView)`. The trace does not model that full active-member
copy. Independent source review found no missing guard. The raw warning remains
available; strict unsuppressed Memcheck passes the normal and failing paths.

The baseline also reported `nullPointerArithmeticRedundantCheck` for the
source message. It considers a NULL message value at the explicit
`UPB_ASSERT(source)` precondition in `upb_Clone_MessageValue`.
No change was made to that input precondition. The warning's disappearance
is not causal evidence for either allocation fix.

The Clang C baseline path treats `upb_MiniTableField_CType(field)` as a
non-message type when selecting the subtable, then as a message type for the
clone operation. The field does not change between those calls.
This warning also does not establish an allocation-failure repair.

Cppcheck cannot process all GCC16 C++ preprocessor feature queries directly.
A private finite adapter measured feature answers with the selected GCC16
command. Unknown answers caused explicit failures; none was guessed.
Namespaced C++ attribute queries in Abseil still blocked that approach.
As a separate check, both complete translation units were preprocessed by
the actual GCC16 command. Cppcheck rejected both at GCC16 `<array>:75`.
The failed runs remain diagnostics, not accepted coverage.

The final before/after C records are under
`$PROTOBUF_WORK/analysis-native-final-copy-measured`.
The unchanged C++ entry-point path-analysis records are under
`$PROTOBUF_WORK/analysis-native-array-fixed`.
The installed-consumer records are under
`$PROTOBUF_WORK/analysis-native-contracts`.
The exact GCC-preprocessed Cppcheck attempts are under
`$PROTOBUF_WORK/analysis-gcc-preprocessed`.
Earlier incomplete attempts remain available in separate analysis directories.

## Execution checks

The native helper completed its normal CMake/Ninja build and full installation
with status zero. Its immutable invocation snapshot and log remain under
`helper-snapshots` and `logs/native-build-final-sole-ninja.log`.
The loader selects the common repaired zlib 1.3.2 from the explicit provider.

| Check | Result |
| --- | --- |
| Installed C++ library consumer | 14 checks pass, including gzip-stream round trip and independent wire bytes. |
| Installed UPB consumer | Four allocation-failure modes pass and preserve the source. |
| Original UPB causal control | Initial-message and scalar-string clone/copy cases produce invalid writes; repeated-field case returns false success with an absent field. |
| Repaired UPB strict Memcheck | Zero errors, zero remaining blocks, zero suppressions in all modes. |
| CLI functional comparison | Same version, generated C++ bytes, unknown-option status and error text. |
| Raw strict CLI Memcheck | Original: 122 contexts. Repaired: 26 contexts. Both fail the all-leak-kinds gate. |
| CLI with the same documented cache exceptions | Original: status 99 and 96 unsuppressed registry contexts. Repaired: status zero and zero unsuppressed errors. Both exclude the same 5,955 bytes in 37 blocks. |
| C++ consumer Memcheck | Raw: one reachable 8-byte Abseil log-sink block. With the one exact lifetime exception: zero unsuppressed errors. |

[MEMORY.md](MEMORY.md) records the current exception ownership and raw failures.
An independent agent reviewed the patches, fault-injection fixture, causal logs,
exception stacks and source-lifetime classifications. The UPB runs use no
exceptions. Nothing treats the retained process caches as freed memory.

The baseline UPB uses the original release code plus the two canonical build
portability patches through its own CMake graph. It uses Release `-O3` plus `-g`;
the installed library uses Release `-O3`. The baseline C fixture uses Release,
and the installed consumer uses RelWithDebInfo. These are not byte-identical
compiler configurations. The baseline CLI entry point links to the same
installed compiler library as the repaired CLI.

Evidence directories are `upb-causal-results`, `protoc-causal-results`,
`protoc-memory-results`, `protoc-memory-reviewed` and `protoc-memory-script`.
All are below `PROTOBUF_WORK`. Failed configuration/analysis attempts remain
separate from accepted results. AArch64 build/runtime, package lifecycle and
KiCad acceptance remain unverified by this native checkpoint.
