# Stage the Electron runtime

This source probe is the only Electron 44 recipe candidate. Move this directory
to `pkgsrc/devel/electron44` when its ordinary build and install targets work.
Remove the probe in that same change. Keep the shared Chromium and Electron
patch series at its existing owner. Do not add a second fetch-only recipe.

## Build boundary

The recipe currently fetches Electron 44.9.3 and Node 24.22.0. It does not prepare
the complete Chromium DEPS tree or run GN and Ninja. Do not use `NO_BUILD`, a
downloaded binary ZIP, or an externally supplied ZIP as its ordinary build.

The SDK already supplies the needed mechanisms. Load the accepted native
selection with `native_toolset.load_native_toolset`. Select GN, Ninja and Python
from that selection. Use `process.run_logged` for both producers while the
caller retains its source/input locks and exclusive work context. A separate
Electron executor or qualification format is not required.

The missing recipe integration is concrete:

1. Prepare the full pinned Electron DEPS source and ordered Ports patches in
   the recipe's own work tree. The two current distfiles are insufficient.
2. Map the accepted native selection and the independent GCC16 target SDK to
   GN arguments. Bind the native compiler paths and ordered ABI arguments,
   Mac SDK, host Node and other generators used by the actual graph. Bind the
   target compiler/binutils, EmberBSD sysroot and target pkgsrc metadata.
   Select both GCC host and snapshot families documented in the parent README.
   Preserve the target custom libc++ policy, final-link pool and link launcher.
3. Write that checked `args.gn` in a new recipe-owned output directory. Run the
   selected GN as `gn gen OUTPUT --script-executable=SELECTED_PYTHON`. Then run
   the selected Ninja as `ninja -C OUTPUT -j JOBS electron_dist_zip`.
   Use the SDK process API and explicit argv arrays for these calls. Do not
   select a tool through ambient PATH or replace the target compiler with Clang.
4. Stage only `OUTPUT/dist.zip` produced by that successful, drained build.
   Use its actual SHA256 as a byte-stability check. The hash does not accept
   the source graph, compiler, sysroot or build by itself.

The current standalone source and GN fixtures do not implement steps 1 and 2.
They also do not establish a production GN graph for the selected native SDK.
Those are recipe bindings to the existing APIs, not missing SDK executors.
Keep the probe until this integration is implemented and checked with real GN.

## Staging mechanism

`files/stage-runtime.py` is a bounded extraction helper for step 4. It does not
run a payload or install a package. It returns extracted byte and ELF facts.
It emits no success, qualification or build receipt. The caller owns the input,
destination parent and their SDK context locks for the whole call.

The helper uses SDK API 1 for stable regular-file reads, no-replace directory
publication and ELF inspection. The archive digest must match before parsing.
The destination must be new. A failure removes only the helper's temporary
directory. A concurrent destination is preserved.

The helper preserves all runtime members. It does not copy an old Linux or BSD
file allowlist. It requires the target `electron` executable, exact version,
Electron `LICENSE` and generated `LICENSES.chromium.html`. Safe relative links
and additional BSD helpers, shared libraries, locales and resources are kept.
Unsafe names, collisions, escaping links, special files, privilege mode bits,
corrupt data and wrong-CPU ELF images are refused. It does not strip executables
or remove sandbox files or options.

The first mechanism supports stored/deflated, single-disk ZIPs with a standard
central directory, at most 65,534 entries, a 16 MiB directory, 2 GiB per member
and 8 GiB total. A ZIP64 central directory is an explicit unsupported case.
These limits are checked before extraction. They are not a runtime file list.

The SDK ELF reader checks machine, class, type and dynamic entries. It does not
yet read `PT_INTERP` or the NetBSD ABI note. Before ordinary installation, check
the actual loader identity, EmberBSD sysroot provenance and complete target
runtime closure. An ELF machine value alone cannot establish that provenance.
Install the complete checked payload under `${PREFIX}/lib/electron44` and use
a relative `${PREFIX}/bin/electron` link. Generate and review the package file
list from that actual payload. Keep both notice files installed. Reconcile the
recipe license expression and redistribution restrictions with the generated
notices and selected dependency recipes before distribution.

## Source checks

Run the selected Python with an explicit SDK API 1 source:

```sh
/absolute/sdk/python -B probes/electron/tests/electron-runtime-stage.py \
    --sdk-source /absolute/EmberBSD-SDK
```

The tests use small synthetic ELF and ZIP data. They cover complete-member
preservation, notices, relative links, target identity, corruption, traversal,
collisions, size limits, cleanup and destination races. They run no GN, Ninja,
compiler or target program. They cannot qualify an Electron artifact.

The runtime dependency selection comes from Electron's `dist_zip` target and
`build/zip.py`, including the generated Chromium credits. See the upstream
[BUILD.gn](https://github.com/electron/electron/blob/v44.9.3/BUILD.gn) and
[ZIP script](https://github.com/electron/electron/blob/v44.9.3/build/zip.py).
The prepared Ports source also contains the BSD adaptations listed in the
parent README. In particular, BSD does not select the Linux SUID helper, and
the current ZIP script omits dummy ANGLE EGL/GLES files.

The local pkgsrc `www/chromium` recipe and the FreeBSD maintainer's
[Electron recipe](https://github.com/tagattie/FreeBSD-Electron/blob/master/devel/electron39/Makefile)
show the applicable BSD pattern: build the owned source tree, install its
runtime files in a private versioned directory, and retain license notices.
Their older file lists and compiler policies do not define this runtime's
payload or its GCC16 toolchains.
