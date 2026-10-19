# Sway startup errors and partial cleanup

The Sway 1.12 recipe owns this repair in EmberBSD-Ports. It keeps the common
GCC16 toolchain, wlroots 0.20.2 and existing dependencies. The source patch
uses AI assistance and has not been submitted upstream.

`server_init` creates the default seat before configuration loading.
If IPC setup then fails, `main` enters normal server cleanup while `config`
is still NULL. The seat destroy listener previously read
`config->handler_context.seat` in that state. A missing directory in
`SWAYSOCK` therefore caused SIGSEGV after the expected IPC bind error.

The [seat patch](../../profiles/common-graphics/recipes/wayland/sway/patches/patch-sway_input_seat.c)
checks `config` before updating its handler context. The rest of seat cleanup
still destroys devices, focus nodes, input methods, the cursor, listeners,
deferred bindings, the scene tree and the seat itself. It does not skip teardown
or create a replacement configuration.

## Real target regression

`tests/startup-failure.py` runs an unprivileged headless/Pixman compositor on an
explicit SSH target. It sets `SWAYSOCK` first below a missing directory and then
below a regular file. Both paths fit the socket path limit. Both must produce
the IPC bind diagnostic and process exit status 1. A waiting parent records
the actual process status separately from the SSH result. Core dumps are disabled.

The installed nb5 baseline returns 139 for both cases. The GCC16-built nb6
staged executable returns 1 for both cases. Each check removes its own guest
directory. The same nb6 executable also passes normal headless workspace,
output, tree and IPC exit checks with process status 0.

```sh
python3 probes/sway/tests/startup-failure.py --host explicit-target \
  --sway /absolute/target-stage/sway --results /absolute/new-startup-results
python3 probes/sway/tests/headless.py --host explicit-target \
  --sway /absolute/target-stage/sway --renderer pixman \
  --results /absolute/new-headless-results
```

The executable is copied from the verified package and run without installing
it. The existing runtime providers and package database remain unchanged.
This establishes staged target execution, not nb6 installed package lifecycle
or physical GPU/input acceptance.

## Native ownership and source analysis

`tests/seat-destroy-native.py` compiles the actual seat destroy handler with the
actual list implementation. Test boundaries model external resource types and
their destructors. Each destructor validates ownership. Three controls cover
absent configuration, the current handler seat and a different handler seat.
Allocation counters also require complete cleanup, including devices, nodes and
two deferred bindings. The baseline NULL-config case fails under UBSan; both
configured controls pass. All three patched controls pass ASan/UBSan.

```sh
python3 probes/sway/tests/seat-destroy-native.py \
  --baseline /absolute/original/sway-1.12 --patched /absolute/patched/sway-1.12 \
  --wayland /absolute/wayland-source --wayland-include /absolute/wayland-build/src \
  --work /absolute/new-seat-check
```

GCC16 `-fanalyzer` passes on both complete seat translation units with their
target compilation database flags and headers. Cppcheck 2.22.0 reports the same
one error, six warnings and 114 style findings before and after the patch.
No category is disabled. Only unsupported GCC diagnostic pragmas are replaced
by blank lines in its preprocessed input; code and line positions remain intact.

The `memleak: seat_device` report at the end of `seat_add_device` does not model
the ownership transfer through `wl_list_insert(&seat->devices, ...)`.
`seat_device_destroy` unlinks and frees that object during device or seat removal.
The assert string warning reports the conventional pointer-and-message idiom.
Five warnings come from existing GLib inline headers. These reports remain
visible; this is not a fully green Cppcheck result.

`tests/ipc-startup-native.py` separately tests the actual IPC startup, address,
subscriber, teardown and termination functions with real list/log code.
It checks three allocation failures, event registration, both environment
publications, path construction, bind/listen failures and early/late shutdown.
Eleven original failures become twelve sanitizer passes. Its explicit test-only
bind/listen and Wayland event ownership boundaries do not establish target
compositor acceptance under injected allocation failures.

The IPC patch returns startup errors to normal cleanup, rolls back owned
resources and registers the display listener only after preparation succeeds.
The subscriber query tolerates startup and completed teardown. Main initializes
its cleanup state before its first error jump.

Valgrind and LeakSanitizer are unavailable on the Darwin/AArch64 host.
The focused ASan/UBSan checks and allocation counters are not a full compositor
Memcheck result. The [main Sway probe](README.md) records wider analysis limits.
