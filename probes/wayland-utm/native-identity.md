# Native DRM identity probe

The local `patch-zz-native-identity` adapts pinned libdrm 2.4.134 to the
EmberBSD read-only `hw.drm2.identity<minor>` PCI record. It is AI-assisted
and has not been submitted upstream. The upstream archive/license and
imported pkgsrc patches remain unchanged; `sources.tsv` pins its original
URL and SHA256. The matching kernel interface is documented in
[EmberBSD](https://github.com/oxtech-ember/EmberBSD/blob/main/sys/external/bsd/drm2/drm/docs/drm-native-identity.md).

A metadata-capable device can be discovered without opening its primary
node, owning DRM master, or opening `/dev/pci` or `/dev/drvctl`. Primary
and render indices are independent. Node names are returned only after
checking the actual character-device major/minor. Device enumeration keeps
libdrm's public structures and PCI-address folding. Flags zero still returns
vendor, product and subsystem IDs; revision is `0xff` unless requested.
Unknown public flags, schema versions, lengths or record flags fail.

Only missing metadata (`ENOENT`) uses the existing NetBSD discovery path,
so drivers which do not publish this record keep their previous behavior.
Malformed, inaccessible and mismatched metadata do not use that fallback.
An unregistered device has no record. Like device-node discovery generally,
this API is a snapshot: a removed device or replaced pathname can change
between calls. Reusing the same rdev denotes the currently registered device;
this interface is not a persistent identifier for a removed device instance.

## Isolated native build

```sh
sh build-libdrm.sh "$HOME/.cache/emberbsd-libdrm-identity" /path/to/libdrm-2.4.134.tar.xz
```

The optional archive is hash checked before extraction. Without it the
helper downloads the pinned original. Build in a new private directory as
an ordinary user; no installed system libraries or desktop are replaced.
The helper applies the full ordered patch set, records hashes, compiles
with `-Werror -Wno-error=cpp`, runs the production-code contract and upstream tests, and
stages libdrm in `install/`. Meson and upstream tests still need Python;
project-owned build and contract helpers use shell and C.

The sole `-Wno-error=cpp` exception preserves upstream explicit `#warning`
diagnostics for unsupported USB/OF/faux buses on NetBSD. Compiler diagnostics
remain fatal. The local patch resolves the NetBSD ALIGN macro collision,
places declarations before statements, checks signed snprintf results safely
and compiles a name helper only on the two platforms that use it.

The fixture compiles actual functions from patched `xf86drm.c`, including
`drmGetDevices2`, `drmGetDevice2`, node-name lookup, node-type lookup and
unchanged device allocation/folding. Only native system boundaries and the
unchanged legacy PCI fallback are mocked. It checks two devices with
nonmatching primary/render indices, master/global-access absence, missing
and reused paths, closed fds, optional revision, unknown flags/schema and
legacy fallback. The same contract can run on macOS against a freshly
patched tree:

```sh
sh tests/native-identity.sh /path/to/patched/libdrm-2.4.134
```

Host and native contracts pass. The isolated NetBSD 11/aarch64 library build
passes with the documented warning policy; upstream tests report three passes
and one device-dependent skip. The matched kernel changes pass targeted
compilation, but full kernel rebuilds and live unprivileged render-only
discovery remain pending; no acceleration is claimed. Runtime
acceptance must check the actual loaded libdrm, both enumeration calls,
render-name/type calls, and unchanged negative KMS permission checks. Drop
supplementary groups after an authorized render open to avoid an admin's
PCI permissions masking a regression. No account or permanent node-permission
change is required. This libdrm-only probe makes no Mesa version selection.
