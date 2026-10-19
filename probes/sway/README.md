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

The common exporter does not include these three new recipes yet. After
the ordinary common graphics export, copy the following directories from
this Ports checkout to the same paths in that export:

- `profiles/common-graphics/recipes/wayland/sway` to `wayland/sway`.
- `profiles/common-graphics/recipes/textproc/json-c` to `textproc/json-c`.
- `profiles/common-graphics/recipes/devel/libevdev-chunk` to `devel/libevdev-chunk`.

Use that export and its matching cross MAKECONF:

```sh
env TMPDIR=/absolute/build-tmp bmake -C /absolute/pkgsrc/wayland/sway \
  MAKECONF=/absolute/cross.mk.conf MAKE_JOBS=1 package
```

The selected common wlroots configuration determines Sway's backend
features. The accepted DRM/GLES2 provider currently has no Xwayland.
The initial port therefore targets a Wayland session. It does not claim
X11 application, Vulkan/HDR or physical-device acceptance.

The header patch makes `stringop.h` declare its own `va_list` dependency.
An independent GCC16 translation unit fails with the original header and
passes with the patch. The current recipe keeps upstream's fatal linker
warnings. On NetBSD it selects direct ELF dependency resolution, matching
Sway's declared libraries. The inherited `--copy-dt-needed-entries` default
can warn about compatibility symbols that the application never uses;
see the [upstream diagnosis](https://mail-index.netbsd.org/tech-toolchain/2026/09/18/msg004903.html)
and [GNU dependency-resolution contract](https://sourceware.org/binutils/docs/ld/Options.html).

`tests/link-dependencies.py` builds two real DSOs with the common GCC16.
Its baseline reproduces the false warning. Direct dependency resolution
passes the safe call, still fails on an actual warned call, and rejects
an undeclared indirect dependency. The exact Sway link also passes with
this mode and the unchanged `--fatal-warnings` flag.

```sh
python3 probes/sway/tests/link-dependencies.py \
  --cc /absolute/common-cross/bin/aarch64--netbsd-gcc \
  --sysroot /absolute/common-sysroot --work /absolute/new-link-test
```

Cppcheck 2.22.0 and GCC 16.2.0 analyze the 12 C modules changed by the
inherited portability patches, before and after patching, with the real
cross flags and headers. Findings remain visible on both versions. They
include allocation-failure paths in command parsing, the input manager
and tree output. These are existing upstream issues; this port does not
claim a clean compositor analysis or allocation-failure acceptance outside IPC.
`tests/stringop-native.c` checks 14 contracts against the actual common
string implementation under native ASan/UBSan. It covers high bytes,
quoted arguments, empty input and owned return values. It does not inject
allocation failures or establish a full compositor memory-check result.

Some of the inherited multi-module Cppcheck inputs stop at GLib diagnostic
pragmas. Those parser failures limit that comparison. The IPC module has a
separate complete comparison with the actual target headers and flags.
Its analysis copies omit only GCC diagnostic pragmas and retain line numbers;
the compiler inputs and executable code remain unchanged. The signed event
flags give ten C11 shift errors in the original header. The patch uses unsigned
shifts and preserves all 32-bit protocol values. Existing style and warning
findings remain visible.

`tests/ipc-values.py` reproduces the original strict GCC shift rejection and
runtime UBSan mask failure. The patched actual header passes GCC path analysis
and native ASan/UBSan. It checks ten event wire values, eleven masks, command
values and enum width. The subscription-mask contract still requires an event
index below 32; all upstream defined event indices are below 22.

```sh
python3 probes/sway/tests/ipc-values.py --source /absolute/original/sway-1.12 \
  --cc /absolute/common-cross/bin/aarch64--netbsd-gcc \
  --sysroot /absolute/common-sysroot --work /absolute/new-ipc-value-check
```

## Compositor and shutdown checks

Sway 1.12nb5 passed the ordinary GCC16 package build and all package checks.
All 33 installed payload entries match that package in the shared sysroot.
Its package SHA256 is
`14294d586f593e33c8ac15a011591a4fe8ab9766fcdd08ba5337fb7cc5b54c69`.
The same package passes installed acceptance on an isolated AArch64 VM.
The unprivileged Pixman/headless compositor passes version, workspace switching,
output creation, tree queries, the exit reply and actual process exit status 0.

The original nb4 package reproduces reply loss despite process exit status 0:
the display loop stops before the queued IPC response is written.
The source patch uses the existing
nonblocking writer once before teardown closes each connection. It handles a
writer that already disconnected the client. This is one best-effort write;
it does not guarantee delivery of a large or blocked backlog.

`tests/ipc-shutdown-native.py` compiles the actual writer, disconnect and display
destruction functions with the real list implementation and native sockets.
The original source reproduces reply loss. The patched source passes reply,
closed-peer and blocked-socket cases under ASan/UBSan. A test-only Wayland event
ownership model checks each removal and release; it does not replace a target
Wayland implementation. Both native runners use short owned directories under
`TMPDIR`, independently of their build paths, to fit Unix socket path limits.

IPC startup now returns an error to the existing main cleanup path. It checks
address/list allocations and event registration, rolls back owned resources,
and registers the display listener only after preparation succeeds. The
subscriber query tolerates startup and completed teardown. The main cleanup
state is initialized before its first error jump. This avoids invoking a
termination callback that can return or send an event before IPC exists.

`tests/ipc-startup-native.py` executes the actual startup, address, subscriber,
teardown and termination functions with the real list/log code. Eleven original
lifecycle failures become twelve passing sanitizer controls. Three allocator
failures, event registration, both environment publications, path construction,
bind/listen failure, and early/late shutdown have independent resource assertions.
The explicit test-only bind/listen failure boundary uses owned files;
socket descriptors, descriptor flags and filesystem
cleanup are real. Wayland event ownership also uses a test boundary. These checks
do not establish compositor acceptance under injected target allocation failures.
The separate installed VM check uses the actual Wayland event loop and sockets.

Full target-header analysis covers both IPC and main. GCC16 path analysis passes.
Cppcheck retains five warnings from GLib inline headers on each module. The two
IPC allocation warnings are removed. A separate actual-main GCC16 check rejects
the original jump across `nag_gpu` initialization and accepts the patched source.
The wider command/input/tree allocation-failure findings remain outside this fix.

```sh
python3 probes/sway/tests/headless.py --host explicit-target \
  --renderer pixman --results /absolute/new-headless-results
```

The runner requires an installed package and an existing unprivileged `nobody`
account. A parent waits for the compositor and records its real exit status.
The runner requires the exit reply and status 0, saves the compositor
log, and removes only its own guest directory. The VM has no physical graphics
or input device. This check does not qualify a hardware desktop session.

Ordinary `pkg_delete` removes all 33 package payload entries on the VM.
Ordinary `pkg_add` restores the same 33 entries with matching hashes and modes.
The existing configuration remains unchanged and `pkg_admin check sway` passes.
The same strict headless checks pass after reinstallation.

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
