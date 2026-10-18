# Asynchronous Qt child processes

This diagnostic checks the QProcess completion signals used by KWin's Xwayland
startup scripts. It needs the common Qt 6.12 Core and Gui runtime. It does not
need a compositor, GPU access or an active desktop.

Cross-build with the common GCC16 toolchain and verified EmberBSD sysroot:

```sh
sh build.sh /absolute/cross-tools /absolute/sysroot /absolute/new-binary
```

Copy the executable and `run.sh` to the target. Run as an ordinary user:

```sh
sh run.sh /absolute/binary /absolute/new-results
```

The runner checks Core and offscreen GUI applications with both dispatcher
choices. It repeats each check after a Qt thread has completed, after a detached child\nhas started, and after both operations. Every positive
process must deliver twenty `started` and `finished` signals. A negative process
must report `FailedToStart` without a `started` signal. Each child has a five
second deadline. Each test process also has an external deadline. A timeout
kills and reaps the diagnostic's child. The runner records the executable hash.

`QT_NO_GLIB=1` must select `QUnixEventDispatcherQPA` for GUI and
`QEventDispatcherUNIX` for Core. KWin uses the former. A passing standalone test
does not establish KWin's full startup, Xwayland readiness or Plasma stability.
The detached-first case reproduces a Qt 6.12 NetBSD defect. The intermediate\n`vfork` child initialized forkfd in shared memory. Its SIGCHLD handler belonged\nonly to that child. The Ports patch uses `fork` for this intermediate step and\nkeeps ordinary launch selection unchanged. The unpatched CM5 runtime starts\nthe next child but never delivers `finished`; the external deadline rejects it.\n\nSource: [Qt 6.12 QProcess](https://github.com/qt/qtbase/blob/v6.12.0/src/corelib/io/qprocess_unix.cpp),\nblob `58d582b2bb2f10a5e6e2df91c9309e57fa758a84`.\nThe separate full Plasma session remains the consumer acceptance gate.
