# Sxmo 1.18.1 portability probe

This probe starts the current stable Sxmo port. The selected upstream tag
`1.18.1` resolves to `61ade447e7c033421df8f248835d0f51daaf58c3`.
The [source manifest](sources.tsv) records the original archive and SHA256.
Sxmo is AGPL-3.0-only. Each source file keeps its original copyright notice.
The clock adaptation is EmberBSD work with AI assistance.

The intended Wayland backend is current Sway 1.12 with common wlroots 0.20.2.
The probe does not replace the backend or claim a complete mobile session.

## Build the real helpers

Use the common GCC 16.2.0 cross compiler and the same EmberBSD sysroot as the
desktop packages. Supply a new work directory on the build filesystem:

```sh
python3 build.py /absolute/sxmo-utils-1.18.1.tar.gz \
  /absolute/common-tools/bin/aarch64--netbsd-gcc \
  /absolute/sysroot /absolute/new-sxmo-work
```

The script checks the source hash, compiler and target triplet. It extracts
the archive, applies the public patch and builds all four original C helpers.
It saves every command, exit status and successful output hash in `receipt.json`.
Any failed helper makes the complete command fail. A partial source build
does not create or install an incomplete Sxmo package.

`sxmo_sleep` uses the target's real timerfd API. The patch keeps realtime
and monotonic clocks. It explicitly rejects boottime and alarm clocks when
the target headers do not define them. It preserves those options on Linux.
It does not map an alarm clock to a normal timer.

## Regression and analysis

```sh
python3 tests/sleep-clocks.py /absolute/sxmo-utils-1.18.1.tar.gz \
  /absolute/new-clock-check
python3 tests/led-bounds.py /absolute/sxmo-utils-1.18.1.tar.gz \
  /absolute/new-led-check
```

The regression compiles the actual program against a host-only timerfd
boundary fixture. A ready pipe supplies the timer expiration. Eight CLI
cases check both supported clocks, missing duration, unknown clock and
three explicit unsupported-clock errors. The original source and a removed
guard must fail compilation. ASan and UBSan check the host execution.
This fixture does not measure real elapsed time or suspend behavior.

The LED check executes the original parser and real file-reading functions.
Four original sanitizer failures cover excess color tokens, invalid sentinel
shifts, a full input buffer and a failed read. The patch checks exact RGB
names and array capacity. It terminates successful bounded reads and closes
descriptor zero correctly. Group handles use -1 for unopened descriptors. Eighteen valid, malformed and descriptor-zero
cases pass ASan/UBSan. Temporary regular files check the file contract;
they do not emulate a hardware LED driver.

Cppcheck 2.22.0 compares original and patched source after preprocessing
with the real GCC16 target headers and macros. The selected helper has no
new findings. Three unused inline functions in target headers are inherited.
GCC 16.2.0 `-fanalyzer -c` also completes for the patched helper.
The complete four-helper comparison retains a Cppcheck array warning in
`led_max_brightness`: the reported group access assumes `LED_GROUP`, while
its only `COLOR_MAX` caller is inside the unchanged `LED_MULTICOLOR` branch.
That infeasible path is recorded as a false positive. Existing style
findings remain visible in the reports.
Valgrind is unavailable on the macOS/Apple Silicon host. The native sanitizer
run is a substitute check, not a Valgrind result.

The real timerfd checks also pass in an isolated EmberBSD 11/AArch64 VM:

```sh
python3 tests/run-timers.py user@explicit-target /absolute/sxmo-build \
  /absolute/new-target-results
```

Eight target cases include three measured one-second realtime/monotonic
waits, the aligned realtime timer and explicit errors for unsupported clocks.
The runner checks the built payload hashes. It saves all output and status
files, then removes its own target temporary directory. The VM has no
physical input or graphics device. Suspend and alarm wakeup are not checked.

## Current boundary

The real AArch64 build links `sxmo_aligned_sleep`, `sxmo_sleep` and
`sxmo_status_led`. The full probe fails at `sxmo_vibrate`: the common
input-headers FreeBSD interface uses `_IOWINT` for force-feedback removal,
which NetBSD does not define. NetBSD also needs an actual force-feedback
device contract before this program can control hardware. Adding an ioctl
number does not establish such a contract.

The shell session still needs platform work for device discovery, `/sys`
power and LED policy, service supervision, networking, audio and modem
integration. The full upstream shellspec and hardware checks have not run.
No complete Sxmo package or visible Sxmo session is accepted.
