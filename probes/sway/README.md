# Current Sway source and cross packages

This port selects [Sway 1.12](https://github.com/swaywm/sway/releases/tag/1.12),
released on 2026-05-25, at commit
`88869399f421d9180dd8b6ed0b5a1f4a3585d252`. It uses the common wlroots
0.20.2 API, GCC 16.2.0 and the existing graphics sysroot. It does not add
another wlroots, Mesa or compiler version.

The [source manifest](sources.tsv) records each original archive and SHA256.
The recipes keep their pkgsrc provenance at commit
`fff4deb639a1a640476203c80f752fb77b6cb14b`. The EmberBSD adaptations use AI
assistance. They have not been accepted upstream.

## Shared dependencies

JSON-C 0.19 is the current stable release from 2026-06-27. The recipe
retains the shared/static library, CMake metadata and pkg-config interface.
It uses the new `libjson-c.so.5.5.0` payload. Upstream warnings remain fatal.

The BSD input-name provider uses the latest stable `20231112` tag of
libevdev-openbsd. Both this tag and upstream HEAD resolve to
`d41a0fc04be7841b06a7cf172375dcbd91fdf3f5`, checked on 2026-10-19. The
commit date is 2023-11-11. This is the current upstream source, rather than
an older branch selected from pkgsrc. The archive for the selected tag is
byte-identical to the earlier tag because both select the same commit.

This canonical BSD provider implements event-name conversion. Sway uses
that API to translate button names and IPC fields. It does not replace the
common libopeninput device backend or provide Linux force-feedback ioctls.
The existing two pkgsrc API patches are preserved.

The cross recipe uses the selected target CC, AR and RANLIB. It builds the
shared object with the GNU SONAME option. This avoids the build host's BSD
make framework selecting Darwin `-force_load` options. Native BSD builds
keep their existing make path.

Both ordinary AArch64 packages pass PLIST, permissions, PIE, RELRO, RPATH
and work-reference checks. The shared sysroot installation matches all six
libevdev and 24 JSON-C payload entries. These are package and source checks;
installed API and compositor acceptance are separate checks below.

## Sway recipe

The recipe uses common PCRE2, matching upstream's `libpcre2-8` dependency.
It retains sway, swaybar, swaymsg, swaynag, wallpapers, completions, the
session helper, configuration and manual pages. It explicitly requires
GdkPixbuf, the Basu tray backend and native scdoc. Cross builds use the
receipt-verified native Wayland scanner. Missing tools or libraries fail
configuration. Subproject fallback downloads are disabled.

Use the ordinary common graphics export and its matching cross MAKECONF:

```sh
env TMPDIR=/absolute/build-tmp bmake -C /absolute/pkgsrc/wayland/sway \
  MAKECONF=/absolute/cross.mk.conf MAKE_JOBS=1 package
```

The selected common wlroots configuration determines Sway's backend
features. The accepted DRM/GLES2 provider currently has no Xwayland.
The initial port therefore targets a Wayland session. It does not claim
X11 application, Vulkan/HDR or physical-device acceptance.

## Input-name contract

`tests/input-names.c` checks 14 independent ABI, event-name and invalid-input
contracts. Compile it with the common target compiler, installed
`libevdev.pc` and normal target RPATH. Execute the target ELF on an explicitly
selected EmberBSD VM. This check does not read an input device.

Full Sway packaging, headless compositor/IPC acceptance and normal installed
package removal/reinstallation are the next gates. A source recipe or a
linked executable alone does not establish a desktop session.
