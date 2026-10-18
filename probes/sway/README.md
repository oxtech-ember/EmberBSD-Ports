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

The JSON-C patch uses POSIX `printf` to produce the exact upstream CLI
regression input. The original test fails on Darwin because `echo -n`
changes its input. It also fails on a target without `xxd`. The patched
test retains both expected output lines and the expected failure status.
All 28 upstream test scripts pass on the AArch64 target and under native
ASan/UBSan. The baseline passes 27 of 28 on each platform.

GCC analysis also found a copied-key leak when hash insertion fails.
The source patch releases that copy, preserves constant-key ownership and
leaves the value with the caller. `tests/json-key-failure.c` exercises the
real table-capacity failure and counts the copied key's release. It fails
on the original source and passes with the patch under ASan/UBSan.

Cppcheck 2.22.0 and GCC 16.2.0 analyze all 14 production C modules with
the real cross flags and headers. The changed module is analyzed again.
Cppcheck reports no errors. Its inherited warnings include constant
expressions after preprocessing and a negative `printbuf` position that
violates the buffer invariant. Three GCC reports remain visible: two lose
the object-type/table-length invariant, and one treats the successful
hash insertion as a leak across a translation-unit boundary. On success,
`lh_table_insert_w_hash` stores the key and the table later releases it.
No diagnostic category is disabled. The analyzer run is not fully green.

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

All 14 contracts pass on the target. `tests/input-names-native.py` also
passes with ASan/UBSan and detects the original missing APIs and a wrong
event-code control. It compiles the actual provider and uses the installed
BSD input headers. It does not duplicate event codes in a replacement API.

`tests/json-target.py` transfers the cross-built test executables and
upstream expected files to an explicit SSH target. It uses the installed
library, records each result, and removes its guest work directory.
The native sanitizer run uses the same source with a separate CMake build.
Valgrind and LeakSanitizer are unavailable on the Darwin/AArch64 host.
ASan/UBSan are not a Valgrind or general leak-check pass. The copied-key
regression has its own allocation-lifetime assertion.

Build the ownership regression against the matching native static library:

```sh
cc -O1 -g -D_GNU_SOURCE -fsanitize=address,undefined \
  -fno-omit-frame-pointer -I/absolute/json-build -I/absolute/json-source \
  probes/sway/tests/json-key-failure.c /absolute/json-build/libjson-c.a \
  -lm -o /absolute/test-work/json-key-failure
```

Use the host sanitizer's supported options. The test expects the original
source to fail its release assertion and the patched source to pass.

Full Sway packaging, headless compositor/IPC acceptance and normal installed
package removal/reinstallation are the next gates. A source recipe or a
linked executable alone does not establish a desktop session.
