# Plasma 6.8 volume controls

The `audio/plasma6-plasma-pa` recipe supplies the volume applet, audio KCM,
shortcut service and `org.kde.plasma.private.volume` QML module.
Plasma Workspace notifications import that module. Their recipe has a runtime
dependency on `plasma6-plasma-pa`; the provider has no Workspace dependency.

The common providers are Qt 6.12.0, Frameworks 6.31.0 and PulseAudio 17.0.
`audio/pulseaudio-qt` adds the current PulseAudioQt 1.9.0 client library.
The recipes use the shared GCC16 cross profile and native Qt/KF6 generators.
They do not require GTK or a compiler on the target device.

## Sources and adaptation

[sources.tsv](../sources.tsv) pins both original KDE archives and SHA256 values.
The Plasma PA hash matches the KDE 6.8.0 release checksum page.
The PulseAudioQt hash matches the KDE download mirror metadata.
Release signatures were not verified.

PulseAudioQt 1.9.0 uses an undefined KF5 include variable in its pkg-config rule.
Its headers are installed with the Qt 6 `KDE_INSTALL_INCLUDEDIR_KF` variable.
The recipe patch uses the same variable for both paths. It removes the invalid
`/KF6PulseAudioQt` include path without changing the PulseAudioQt C++ sources or library ABI.

Plasma PA allocates callback data before it tries its speaker-test sounds.
libcanberra transfers that data to the callback only after `CA_SUCCESS`.
The recipe releases the allocation when all fallback requests fail.
The source regression checks both failure and successful callback ownership.

## Build and acceptance

Use the [cross workflow](README.md) and the
[provider checks](../tests/plasma-volume/README.md).
Build and install PulseAudioQt into the audited build sysroot first.
Then build Plasma PA with normal pkgsrc staging and package checks.
The complete package retains translations, the KCM, applet and documentation.
Upstream tests are built as separate execution artifacts.

The package and source checks do not establish a working audio device.
Installed QML import, notifications and the intended Plasma session require
separate target acceptance. Volume feedback also needs the optional Canberra
Pulse backend and sound theme.
