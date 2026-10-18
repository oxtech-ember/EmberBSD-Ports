# Fcitx Configtool cross package and target checks

Configtool 5.1.16nb1 retains the standalone Qt6 UI and the Frameworks 6 KCM.
Ports `557d004` installs the KCM under `qt6/plugins/plasma/kcms/systemsettings`.
This matches the common Qt6 plugin root and its existing PLIST.
The original recipe installed under `lib/plugins`; normal package checks rejected it.
Native and cross metadata checks reject that original configuration and accept the fix.
No GTK or Qt5 provider is added.

The complete macOS arm64 cross package uses common GCC 16.2, Qt 6.12 and LLD 23.1.3.
PLIST, permissions, PIE, RELRO, RPATH and work-directory checks pass.
All six ELF programs/modules retain AArch64, NetBSD 11 compatibility and RELRO metadata.
Their staged and installed sysroot files match byte for byte.
Package SHA256: `97f75138ab22c3c01e83e95181ca5e81d744c3fab254a49483d891814ff8c01c`.
This is a cross-package result. CM5 execution remains pending because the board was powered off.

## Linker selection

The bootstrap GNU ld 2.42 reports warnings for unused libm compatibility symbols.
Configtool retains `--fatal-warnings` and `--no-undefined`.
The existing native LLD23 links the same objects with these flags enabled.
The [shared GCC16/LLD23 regression](../../../../../../../profiles/common-build-tools/tests/gcc16-lld.md)
checks actual tool selection, ELF metadata, undefined symbols and fatal warnings.
It also prepares a C++ exception DSO and consumer. Their target execution remains separate.

Keep the generated specs with the compiler and sysroot provenance.
For a fresh Configtool build, add the following to the selected cross `mk.conf`.
Replace the example specs path with the regression's `selected-linker.specs` file.

```make
.if ${PKGPATH} == "inputmethod/fcitx5-configtool" && ${USE_CROSS_COMPILE:Uno:tl} == "yes"
LDFLAGS+= -specs=/absolute/selected-linker.specs -fno-use-linker-plugin -Wl,-m,aarch64elf
_EMBER_FCITX_EXE_LDFLAGS=${LDFLAGS} -Wl,--dynamic-linker,/libexec/ld.elf_so
CMAKE_CONFIGURE_ARGS+= -DCMAKE_EXE_LINKER_FLAGS:STRING=${_EMBER_FCITX_EXE_LDFLAGS:Q}
CMAKE_CONFIGURE_ARGS+= -DCMAKE_SHARED_LINKER_FLAGS:STRING=${LDFLAGS:Q}
CMAKE_CONFIGURE_ARGS+= -DCMAKE_MODULE_LINKER_FLAGS:STRING=${LDFLAGS:Q}
.endif
```

Use the public pkgsrc `package` target. It prepares the complete buildlink context.
A direct private `cmake-configure` call can omit dependency flags and cache incomplete RPATHs.
This selection does not change compiler defaults or validate LTO and relocatable links.
Do not remove strict linker flags to accept a package.

## Prepared installed-package check

Install the complete package and its selected dependencies. Run as an ordinary user:

```sh
sh runtime.sh /absolute/new-result-directory
```

The helper checks library resolution without `LD_LIBRARY_PATH`.
It runs help and version entry points for Configtool, Migrator and the Plasma theme generator.
An invalid option must fail. `kcmshell6 --list` must discover the installed Fcitx KCM.
Each invocation has a private HOME/XDG/D-Bus environment, Qt offscreen and a bounded timeout.
These eight checks were prepared from the actual program entry points; they have not run on CM5 yet.
The X11-only keyboard viewer receives a library-resolution check only.

The helper does not change input settings, migrate user data or render a theme.
It does not establish physical input, Wayland text-input, full Plasma, long-run stability or memory safety.

## Source-analysis boundary

All 104 C++ source/header files match the pinned upstream archive.
Three production translation units were checked with actual GCC16/AArch64 parameters.
Clang 23.1.3 reports no diagnostics for the keyboard layout, process runner and Configtool entry point.
Cppcheck 2.22 cannot parse `Q_SLOTS` in two units. The layout unit has 15 inherited style findings.
No finding or category was suppressed. Full static analysis remains incomplete.
No Valgrind, target sanitizer or leak-checking acceptance is claimed.
