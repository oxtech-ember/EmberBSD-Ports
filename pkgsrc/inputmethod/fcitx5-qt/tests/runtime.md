# Installed Fcitx Qt6 checks

Build and install Fcitx5 Qt 5.1.16nb1 with the common Qt 6.12 provider.
The quickphrase editor is a shared GUI module, not a standalone executable.
Its package path is `lib/fcitx5/qt6/libfcitx-quickphrase-editor5.so`.
The normal PLIST, permissions, PIE, RELRO, RPATH and work-directory checks remain enabled.

Run the installed-package check as an ordinary user:

```sh
sh runtime.sh /absolute/new-result-directory
```

The script uses upstream `fcitx5-qt6-immodule-probing` and the GUI wrapper.
It checks dynamic library resolution before executing them.
A private HOME/XDG environment and private D-Bus session isolate each invocation.
Qt uses its offscreen platform and the installed input-context module.
Each command has a 30-second limit and a five-second termination grace period.

The five checks require:

- Explicit `fcitx5` selection returns `fcitx::QFcitxPlatformInputContext`.
- A nonexistent input module does not select Fcitx.
- The GUI wrapper prints its help successfully.
- The installed `quickphrase/editor` metadata is found.
- A nonexistent configuration path returns the expected failure.

The wrapper metadata check does not create an editor widget.
These checks do not establish physical key input, Wayland text-input, rendering,
a complete Plasma session, long-run stability or memory-analysis acceptance.

## CM5 result

Ports `f30c7de` supplies the complete Qt package; `5ea1b13` supplies the runner.
The package was cross-built on macOS arm64 with common GCC 16.2.
All 48 installed files check on CM5. All five runtime checks pass on October 13, 2026.
The ordinary-user run took two seconds and did not restart the board.
The target is CM5 Rev 1.0, BCM2712 D0, 4 GiB, with a Waveshare CM5-NANO-B carrier.
Kernel revision: `ab6f88f04ca73c6958adb39d0e1c717f629e7901`.
Firmware revision was not recorded. Kernel and firmware were unchanged.
Package SHA256: `506dd23b5c20a58803f58e8234334cd51136b8dd02502c06b33723b20a9482c6`.

## Source-analysis boundary

All 144 C++ sources and headers match the verified upstream archive byte for byte.
The port changes CMake and package metadata. Three real target translation units were checked.
Clang 23.1.3 reports no diagnostics for the plugin entry point and upstream probing tool.
The larger input-context translation unit exceeded its 35-second analysis limit.
Cppcheck 2.22 reports no source diagnostic for the probing tool.
Two plugin units remain unparsed because of `QT_VERSION_CHECK` in a preprocessor condition.
The checks use actual GCC16/AArch64 arguments, Qt headers and captured compiler macros.
No diagnostic category or finding was suppressed. Full adapter analysis remains incomplete.
No Valgrind, ASan/UBSan or leak-checking result is claimed for this adapter.
