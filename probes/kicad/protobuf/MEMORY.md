# Native process lifetime records

These exceptions describe new runs on 2026-10-18. They were not recovered from
the previous environment. They apply to protobuf 36.2, Abseil 20260817.0,
GCC 16.2.0 and the native Linux code-generation and installed C++ contracts.
They do not apply to the UPB allocation-failure contract or target execution.

Strict raw Memcheck used `--leak-check=full --show-leak-kinds=all
--errors-for-leak-kinds=all --track-origins=yes --error-exitcode=99`.
The CLI run also requested 40 callers. Raw logs remain under
`$PROTOBUF_WORK/protoc-memory-results` and `$PROTOBUF_WORK/logs`.

The original CLI retains 99,786 bytes in 446 blocks and reports 122 contexts.
The shutdown-patched CLI retains 5,955 bytes in 37 blocks and reports 26 contexts.
Neither raw run passes. Neither reports definite or indirect losses.
The C++ contract reports one reachable 8-byte block after its intentional
invalid-UTF-8 diagnostic. Its raw run also fails the strict gate.

## Source ownership

The following paths refer to the pinned release source trees. Each named owner
retains the allocation for the lifetime of the process.

| Exceptions | Source owner | Reason |
| --- | --- | --- |
| `parser_type_map`, `parser_type_backing` | `src/google/protobuf/compiler/parser.cc`, `GetTypeNameTable`, line 67 | Function-static pointer owns the type-name map. |
| `cpp_keywords`, `cpp_keyword_backing` | `src/google/protobuf/compiler/cpp/helpers.cc`, `Keywords`, line 225 | Function-static pointer owns the C++ keyword set. |
| `cpp_nullary_methods`, `nullary_method_backing` | Same file, `MessageKnownNullaryMethodsSnakeCase`, line 104 | Function-static pointer owns the method-name set. |
| `cpp_camelcase_methods`, `camelcase_method_backing` | Same file, `MessageKnownMethodsCamelCase`, line 91 | Function-static pointer owns the method-name set; the function is inlined into collision resolution. |
| `well_known_files`, `well_known_strings`, `well_known_backing` | Same file, `IsWellKnownMessage`, line 1414 | Function-static pointer owns the set and its filename strings. |
| `cpp_version` | `src/google/protobuf/compiler/versions.cc`, line 43 | Upstream explicitly keeps a heap-allocated version to avoid repeated parsing. |
| `objc_prefix_storage` | `src/google/protobuf/compiler/objectivec/names.cc`, line 208 | `g_prefix_mode` is a global reference to an allocated `PrefixModeStorage`. |
| `log_timezone` | `absl/log/internal/globals.cc`, line 97 | `SetTimeZone` installs one process-wide pointer with an atomic compare/exchange. |
| `utc_*`, `local_*`, `timezone_*` | `absl/time/internal/cctz/src/time_zone_impl.cc`, lines 37–118 | The global zone map, function-static mutex and UTC pointer retain zones and their vectors. `ClearTimeZoneMapTestOnly` explicitly cannot delete live zones. |
| `contract_global_sinks` | `absl/log/internal/log_sink_set.cc`, lines 167–180 and 270 | `NoDestructor<GlobalLogSinkSet>` retains the vector containing the default stderr sink. |

The six `possible` records belong only to the five static protobuf hash
containers and the well-known filename strings. Abseil's
`absl/container/internal/raw_hash_set.cc:1082` allocates a backing region and
returns pointers at the control and slot offsets. Those interior pointers explain
the leak-checker's classification. The static containers still own the regions.
No `possible` exception covers a descriptor-pool allocation or an arbitrary hash
table call.

## Exception scope and causal control

`native-runtime.supp` contains 27 observed allocation stacks. It matches only
`Memcheck:Leak` and the observed `reachable` or `possible` kind. It has no frame
wildcards, ellipses, object-wide matches, or invalid-access exceptions.
Some time-zone owners have identical inlined call stacks. The file retains one
named record per observed context; it does not claim 27 distinct frame patterns.

The CLI stacks retain every frame from allocation through `ProtobufMain`.
They end there because the original `main` uses a tail call and the patched
`main` returns after shutdown. The same exceptions must match both programs.
The Objective-C startup stack ends at `_dl_init`; the raw trace after the loader
boundary interprets argument words as unknown frames. These words are not used
as wildcard frames. The consumer exception retains its complete stack to `main`.

Run both CLI variants with the same file and retain both statuses. The original
variant must still fail with descriptor-pool/registry records. The patched
variant must have zero unsuppressed errors. This prevents an exception set from
hiding the shutdown defect. The generated C++ bytes must still agree.

The current comparison passes this control: original status 99 with 96
unsuppressed registry contexts; repaired status zero with none. Both suppress
the same 5,955 bytes in 37 blocks. The C++ consumer passes with its one 8-byte
exception. Independent source and receipt review confirmed these boundaries.

Pass the file explicitly:

```sh
valgrind --tool=memcheck --track-origins=yes --leak-check=full \
  --show-leak-kinds=all --errors-for-leak-kinds=all --num-callers=40 \
  --error-exitcode=99 --suppressions=./native-runtime.supp COMMAND ARGUMENTS
```

These are process lifetime exceptions, not evidence that the allocations were
freed. A compiler, source version, input or stack change requires a new raw run
and ownership review before any exception is changed.
