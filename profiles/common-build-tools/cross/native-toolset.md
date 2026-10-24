# Bind the SDK native toolset

The common cross profile and native LLVM generator controller use
SDK API 1 and `native_toolset.NATIVE_TOOLSET_API=1`.
The SDK owns the descriptor, producer qualification, path checks and tool validation.
Read its [tool selection contract](https://github.com/oxtech-ember/EmberBSD-SDK/blob/main/docs/tool-selection.md).
Ports maps that selection to pkgsrc variables. It does not define another descriptor.

Set these four inputs for Python native controllers:

| Variable | Input |
| --- | --- |
| `EMBERBSD_NATIVE_TOOLSET_DESCRIPTOR` | Absolute SDK descriptor path |
| `EMBERBSD_NATIVE_TOOLSET_DESCRIPTOR_SHA256` | Exact descriptor SHA256 |
| `EMBERBSD_NATIVE_TOOLSET_PRODUCER_RECEIPT` | Absolute accepted producer receipt path |
| `EMBERBSD_NATIVE_TOOLSET_PRODUCER_RECEIPT_SHA256` | Exact producer receipt SHA256 |

The controller interpreter must match the selected `python` role.
Explicit `HOST_CC`, `HOST_CXX`, `HOST_PYTHON`, CMake and Ninja inputs must match
their selected roles. Native Clang table generation also requires declared
`llvm-config` and `llvm-tblgen` roles. A version banner cannot replace membership.

## Prepare the pkgsrc include

Run the selected SDK Python with the explicitly selected SDK source:

```sh
/absolute/sdk/python -B -E -S profiles/common-build-tools/cross/prepare-native-tools.py \
    --sdk-source /absolute/EmberBSD-SDK publish \
    --descriptor /absolute/native-toolset.json --descriptor-sha256 DESCRIPTOR_SHA256 \
    --producer-receipt /absolute/accepted-producer.json \
    --producer-receipt-sha256 PRODUCER_RECEIPT_SHA256 \
    --output /absolute/new-native-bindings
```

The destination must be new. The command uses SDK no-replace publication.
It writes a read-only `host-tools.mk` and the unchanged SDK selection JSON.
Its result reports the include path and SHA256. These are configuration outputs,
not a second toolset descriptor or an automatic cache.

Set the four descriptor inputs in MAKECONF. Also set:

- `EMBERBSD_SDK_SOURCE`: the explicit SDK source.
- `EMBERBSD_NATIVE_TOOLSET_VALIDATOR_PYTHON`: the selected SDK Python.
- `EMBERBSD_NATIVE_TOOLSET_MAKECONF`: the published include path.
- `EMBERBSD_NATIVE_TOOLSET_MAKECONF_SHA256`: the include SHA256.

The profile loads the SDK selection once per configuration check.
It verifies the include hash and exact derived bytes before including it.
It rejects writable includes, missing roles and conflicting native overrides.
Rendered guards compare against literal SDK values. A make command-line alias
cannot replace the value used as its own expectation.
The cross profile reserves `_EMBER_SDK_*` and `_EMBER_NATIVE_*` variables.
It rejects command-line overrides of that namespace before validation.
It also checks every `NATIVE_*` compiler/binutils alias before configure.
Extra `bmake`, `gmake`, `xz`, `xzcat` and `install` roles must be declared explicitly.
There is no selection from a system `PATH` or a compiler-name fallback.

Native compiler commands contain the declared preprocessing, language and link flags.
This preserves the ABI for consumers that use only `CC_FOR_BUILD` for compile and link.
`HOST_CC` and `HOST_CXX` remain executable paths. `HOST_*FLAGS` carry their separate flags.
NSS passes native preprocessing/language flags and native linker flags to `nsinstall`.
These assignments do not change target `CFLAGS`, `CXXFLAGS`, `CPPFLAGS` or `LDFLAGS`.

The make adapter refuses control characters, backslashes, double quotes, dollar signs
and hash characters in emitted values. Tool paths also cannot contain single quotes.
This is an explicit make-representation limit, not an SDK descriptor restriction.

## Source checks and limits

Run the Python source fixtures with `--sdk-source /absolute/EmberBSD-SDK`:

- `tests/native-toolset-selection.py`: eleven double refusal cases, one LLVM controller
  fixture and ten actual SDK admission refusals across LLVM and make entrypoints.
- `tests/native-toolset-make.py`: native ABI argv construction, thirteen refusals and atomic publication.

The positive controller and render fixtures use explicit SDK API doubles.
The admission refusals also load the actual SDK with missing, hash-mismatched,
unsupported or rejected metadata. They accept no synthetic bundle.
These tests do not execute compilers or bmake.
They do not qualify a native bundle. The unchanged selection baseline creates output
without a descriptor; the refusal regression detects this before any producer starts.
Real pkgsrc/configure checks and native compiler acceptance require a qualified bundle.
The `cross-targets.py` and `cross-native-compilers.py` real make checks include
negative role-alias, reserved-variable and ABI override cases.
They require qualified SDK inputs. These cases have source coverage only until
a qualified bundle is available; API doubles do not establish make-parser acceptance.

This change does not cover the development-toolchain host producer, the standalone
cross-tool composer or Wayland scanner builder. Their selectors require separate
SDK integration. Existing package receipts retain their original scope and provenance.
