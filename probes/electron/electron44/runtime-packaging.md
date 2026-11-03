# Stage the Electron runtime

This source probe is the only Electron 44 recipe candidate. Move this directory
to `pkgsrc/devel/electron44` when its ordinary build and install targets work.
Remove the probe in that same change. Keep the shared Chromium and Electron
patch series at its existing owner. Do not add a second fetch-only recipe.

## Build boundary

The recipe currently fetches Electron 45.2.1 and Node 24.22.1. The
[source preparer](source-preparation.md) creates a pinned DEPS input workspace
and applies the recipe-local security series. Its Git-only acquisition stage
records deferred CIPD/GCS/LFS inputs, followed by a guarded upstream patch stage.
It does not yet prepare the complete source graph or run GN and Ninja. Do not use `NO_BUILD`, a
downloaded binary ZIP, or an externally supplied ZIP as its ordinary build.

The SDK already supplies the needed mechanisms. Load the native Ports
host prefix with `native_toolset.load_host_prefix`. Select GN, Ninja and Python
from that selection. Use `process.run_logged` for both producers while the
caller retains its source/input locks and exclusive work context. A separate
Electron executor or qualification format is not required.

The missing recipe integration is concrete:

1. Starting with the prepared DEPS input, acquire the full pinned dependency
   tree, run the guarded upstream patch stage, and apply ordered Ports BSD
   patches in the recipe's own work tree. The two current distfiles are insufficient.
2. Map the selected native prefix and independent target SDK to GN arguments.
   Clang is the default; select GCC only for an explicit platform requirement.
   Bind the native compiler paths and ordered ABI arguments,
   Mac SDK, host Node and other generators used by the actual graph. Bind the
   target compiler/binutils, EmberBSD sysroot and target pkgsrc metadata.
   Set the target `is_clang` mode and the host mode independently, as documented
   in the parent README. Use the matching host and snapshot toolchain families.
   Preserve the target custom libc++ policy, final-link pool and link launcher.
3. Write that checked `args.gn` in a new recipe-owned output directory. Run the
   selected GN as `gn gen OUTPUT --script-executable=SELECTED_PYTHON`. Then run
   the selected Ninja as `ninja -C OUTPUT -j JOBS electron_dist_zip`.
   Use the SDK process API and explicit argv arrays for these calls. Do not
   select a tool through ambient PATH or switch families after a build failure.
4. The controller's `build` and `reconfigure --build-after-reconfigure` produce
   `OUTPUT/dist.zip`; they do not stage or replace a runtime directory. To stage
   the successful, drained result, invoke `files/stage-runtime.py` separately
   with `--archive OUTPUT/dist.zip`, its actual SHA256 in `--archive-sha256`,
   an absolute new `--destination`, `--target`, and `--sdk-source`. The hash is
   a byte-stability check; it does not accept the source graph, compiler,
   sysroot or build by itself.

The initial source preparer and standalone GN fixtures do not complete steps 1
and 2.
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

## Package installation mechanism

`files/install-runtime.py` supplies the installation phase separately from the
build. Its `install` action takes the producer's `--work`, the selected
`--sdk-source`, `--target`, `--lock-root`, an existing package `--destdir`, and
`--prefix /usr/pkg`. It reads only `WORK/out/dist.zip`, holds the work and
DESTDIR contexts exclusively and the SDK context shared, and uses the same
bounded extractor and payload checks as standalone staging. The producer API
hashes the archive once through a stable open file. Standalone staging still
requires its caller's exact `--archive-sha256`.

The complete payload goes to `DESTDIR/usr/pkg/lib/electron44`, followed by
`bin/electron -> ../lib/electron44/electron`. Both destinations must be new;
existing or redirected paths are refused. No target code runs. If another
writer creates the link name after payload publication, installation fails and
preserves both that entry and the staged payload for diagnosis. The caller must
recover its package-owned DESTDIR before retrying; this is not a live-root
installer or a replacement operation.

The `plist` action, with the same arguments, lists the installed regular files,
links and empty directories for pkgsrc's `GENERATE_PLIST`. It refuses redirected
parents and propagates directory-read errors. It does not substitute for the
recipe's runtime dependency metadata, loader validation or package lifecycle
checks. The ordinary package build must first complete the existing source and
toolchain checks and the selected controller build; a ZIP's location alone is
not evidence of that build.

`probes/electron/tests/electron-package-install.py --sdk-source /absolute/EmberBSD-SDK`
uses small synthetic ZIP/ELF inputs for payload preservation, relative links,
PLIST, destination refusals, link races and read errors. It neither reads an
existing production ZIP nor runs a compiler or target program. Ordinary recipe
integration and target package acceptance remain separate work.

## BSD API boundaries

BSD uses the shared desktop window-focus implementation and NativeTheme accent
color observer. `nativeImage.createThumbnailFromPath` remains a macOS/Windows
API and is not exposed on BSD or Linux.

The BSD crash collection backend is not implemented. `crashReporter.start`
and `setUploadToServer` report an unsupported-operation error;
`getUploadToServer` returns false. Extra parameters remain available through
add/get/remove, and report listing can still read existing text records. These
operations do not imply that crashes are captured or uploaded.

NetBSD application memory metrics read current RSS and peak RSS from
`KERN_PROC2`, converting pages and KiB respectively to the API's units. Query
errors retain Electron's existing zero-result convention. On architectures
where the kernel does not track the RSS maximum, its reported peak is current
RSS. The added API specs require execution on the target; cross-linking alone
does not validate these desktop or kernel interactions.

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
[BUILD.gn](https://github.com/electron/electron/blob/v45.2.1/BUILD.gn) and
[ZIP script](https://github.com/electron/electron/blob/v45.2.1/build/zip.py).
The prepared Ports source also contains the BSD adaptations listed in the
parent README. In particular, BSD does not select the Linux SUID helper, and
the current ZIP script omits dummy ANGLE EGL/GLES files.

The local pkgsrc `www/chromium` recipe and the FreeBSD maintainer's
[Electron recipe](https://github.com/tagattie/FreeBSD-Electron/blob/master/devel/electron39/Makefile)
show the applicable BSD pattern: build the owned source tree, install its
runtime files in a private versioned directory, and retain license notices.
Their older file lists and compiler policies do not define this runtime's
payload or its selected toolchains.
