# Stage the Electron runtime

The Electron recipe is owned by `pkgsrc/devel/electron44`. The shared Chromium
and Electron patch series remains under `probes/electron/patches`.

## Build boundary

The recipe binds an explicitly selected, complete Electron 45.2.1 source
workspace to `files/build-electron.py`. The [source owner](source-preparation.md)
prepares the pinned dependency graph and ordered Ports patches before pkgsrc
configuration. `DISTFILES` is empty: neither an external distribution ZIP nor
two standalone Electron/Node archives supply this complete workspace. The
controller verifies the prepared graph, source identities and selected tools.
The pkgsrc scratch `WRKSRC` stays separate from the reusable workspace, so its
patch phase does not reapply the source owner's patches.

`producer.mk` maps `EMBERBSD_ELECTRON_*` settings to the existing controller CLI.
Required settings select `WORKSPACE`, `PORTS_SOURCE`, `SDK_SOURCE`, `HOST_PREFIX`,
`COMPILER_PREFIX`, `SYSROOT`, `WORK`, `GIT`, `LOCK_ROOT`, `LINK_CONTEXT`, `TARGET`,
`PYTHON`, `NODE_SOURCE`, `NODE_PKGSRC`, `V8_SOURCE`, `V8_PORTS_SOURCE`,
`V8_PKGSRC`, `PERFETTO_SOURCE`, `PERFETTO_PORTS_SOURCE`, `PERFETTO_ARCHIVE`,
`PERFETTO_PATCH`, `PROTOBUF_SOURCE`, `PROTOBUF_PORTS_SOURCE`, `PROTOBUF_ARCHIVE`
and `PROTOBUF_PATCH`. SDK source, host prefix, Python, sysroot and target default to the
corresponding common cross-configuration values. Optional settings follow the
controller's option names in uppercase with underscores, including independent
host/target compiler families, runtime stages and native generators. Abseil,
ICU, RE2 and Undici always use the common Ports packages; their `SHARED_*`
settings default to `yes` and cannot select bundled copies. Undici is also a
runtime package dependency. Use the controller's help and the [Electron README](../../../probes/electron/README.md) for those
input contracts. No recipe path overrides the controller's identity checks.

When reusing a graph configured outside the exported recipe, keep the original
controller location as well as its selected inputs. Set pkgsrc `FILESDIR` to
that owner's `electron44/files` directory. The controller derives helper paths
from its own location; a copied controller has different identity paths even
when its bytes match. Changing those paths requires a new configuration rather
than bypassing the existing graph's identity checks.

A new `WORK` is configured once through the selected GN. An existing
`configuration.json` is left for the controller's strict build checks; an
existing work directory without it is refused and preserved. Changes that need
GN regeneration require the controller's explicit `reconfigure` operation with
compatible identities. The recipe does not silently reset or reconfigure an
existing graph. `JOBS` defaults to `MAKE_JOBS` when selected by the caller;
otherwise the controller uses the SDK CPU resolver. `KEEP_GOING` applies only
to the build action. The selected Ninja retains compatible objects and produces
`WORK/out/dist.zip`.

The build and installation phases are separate. `do-install` passes that
producer work directory to `install-runtime.py`; `GENERATE_PLIST` uses its
`plist` action. `runtime-dependencies.mk` selects shared package owners of the
runtime libraries, including the dynamically loaded libnotify. Split LLVM
runtime buildlinks keep their headers and link-time files as build-only
dependencies. Ordinary cross-build, package creation and isolated host-rooted
install/delete/reinstall have passed. Target execution, GUI, complete ABI and
hardware acceptance remain pending.

The controller's `build` and `reconfigure --build-after-reconfigure` do not
extract or hash the distribution after each build. For a separate inspection,
invoke `files/stage-runtime.py` with `--archive WORK/out/dist.zip`, its actual
SHA256 in `--archive-sha256`, an absolute new `--destination`, `--target` and
`--sdk-source`. The hash establishes byte stability, not the source, compiler,
sysroot or runtime acceptance.

## Staging mechanism

`files/stage-runtime.py` is the bounded extraction helper for explicit staging. It does not
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

The native buildlink can use the installed host prefix and its platform C++ ABI
without a replacement stage; omit `HOST_BUILDLINK_STAGE_ROOT` and select the
native tools makeconf. The explicit hardened replacement-stage route remains
available. The target LLVM runtime is selected independently of the host ABI.

DevTools build actions use the selected common native JavaScript providers.
The producer projects their installed package identities into one fingerprint
input shared by Node and TypeScript actions. An unchanged selection preserves
its timestamp, so an unchanged build remains incremental; a changed selection
invalidates the affected actions.
