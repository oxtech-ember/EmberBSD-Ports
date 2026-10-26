# Select the native Ports prefix

The native toolset is the ordinary Ports installation, commonly named
`host-pkg-g16`. Build its packages with the native GCC16 from Ports.
The cross SDK uses these installed host tools.
There is no separate qualification, seed acceptance, tool inventory hash,
or producer receipt requirement for this path.

The SDK owns `native_toolset.load_host_prefix(prefix, required_roles=...)`.
It checks that selected tools resolve inside the prefix, run on the host,
and keep the compiler's executable components inside the same prefix.
Ports maps those paths to pkgsrc variables.
Read the [SDK tool selection contract](https://github.com/oxtech-ember/EmberBSD-SDK/blob/main/docs/tool-selection.md).

Set `EMBERBSD_HOST_PREFIX` for the native LLVM generator controllers.
Run them with Python from that prefix. Explicit `HOST_CC`, `HOST_CXX`,
`HOST_PYTHON`, CMake and Ninja arguments must match the selected tools.
Native Clang table generation also selects `llvm-config` and `llvm-tblgen`
from this prefix. The build environment searches only the prefix.

## Configure pkgsrc

Generate the ordinary make-variable include with the selected Python:

```sh
/absolute/host-pkg-g16/bin/python3.15 -B -E -S \
    profiles/common-build-tools/cross/prepare-native-tools.py \
    --sdk-source /absolute/EmberBSD-SDK write \
    --host-prefix /absolute/host-pkg-g16 --output /absolute/host-tools.mk
```

The command writes one configuration file. Rerun it after changing the
selected prefix or its tool paths. It replaces that file atomically.
It does not create a report, certificate or toolset descriptor.

Set these values before including the common cross profile:

```make
EMBERBSD_SDK_SOURCE=/absolute/EmberBSD-SDK
EMBERBSD_HOST_PREFIX=/absolute/host-pkg-g16
EMBERBSD_NATIVE_TOOLSET_MAKECONF=/absolute/host-tools.mk
```

`EMBERBSD_HOST_PYTHON` defaults to `${EMBERBSD_HOST_PREFIX}/bin/python3.15`.
Set it explicitly when the selected Python has another path.
The adapter checks that its interpreter is the prefix's selected Python.
The profile checks the generated assignments before using them. Conflicting
native compiler, tool and ABI overrides fail. No hash or read-only mode is required.

Native compiler commands retain host ABI flags. Target flags and sysroot
settings stay separate. `CC_FOR_BUILD` and `CXX_FOR_BUILD` contain complete
native compile/link commands. `HOST_CC` and `HOST_CXX` contain executable paths.
The include selects a prefix-only PATH; pkgsrc adds its generated wrappers.
Source archive checksums, package checks and target ABI checks remain enabled.

## Checks

`tests/native-toolset-selection.py` checks the LLVM command and environment
with API doubles. `tests/native-toolset-make.py` checks the make mapping,
atomic rewrites and rejection of stale or conflicting inputs.
These tests do not build a compiler or establish target runtime behavior.
