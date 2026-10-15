# FFmpeg video-only configuration

The NetBSD adaptation permits software video without PulseAudio or PipeWire.
Qt retains its upstream no-device audio implementation and configure warning.
This does not provide audio output or an audio device.
Normal package defaults still select GStreamer and PulseAudio.
The recipe uses the common FFmpeg9 provider when PulseAudio is disabled on NetBSD.

Use a verified, unpatched Qt Multimedia 6.12.0 source directory:

```sh
CMAKE=/absolute/native/cmake PATCH=/absolute/GNU/patch \
sh ffmpeg-feature.sh /absolute/qtmultimedia-everywhere-src-6.12.0 /absolute/new-results
```

The test applies the actual patch with zero fuzz and rejects a second application.
It extracts the real upstream `qt_feature("ffmpeg")` blocks before and after the patch.
CMake evaluates their unchanged `CONDITION` expressions in 96 configuration pairs.
Only NetBSD without an audio backend becomes available.
Missing FFmpeg or threads still prevents selection.
Apple, Windows, Android, QNX and audio-backed configurations retain support.
Linux, FreeBSD and OpenBSD without audio retain their previous selection.
The wrapper does not test Qt's forced-feature policy or generated headers.
Full library builds and installed playback remain separate acceptance checks.

Check the production recipe selector with native BSD make:

```sh
BMAKE=/absolute/native/bmake sh options.sh /absolute/new-option-results
```

The fixture evaluates the unchanged `options.mk` across twelve selections.
Dependency includes record markers instead of loading the full pkgsrc closure.
The test checks FFmpeg dependency and manifest selection, retained desktop
defaults, independent GStreamer/PulseAudio options and Darwin's X11 exclusion.
It does not replace normal package dependency or configuration checks.

Qt's `NETBSD` variable comes from `QtPlatformSupport.cmake` in Qtbase.
`QPlatformAudioDevices::create()` uses the existing no-device implementation
when no low-level audio backend was selected.
The FFmpeg integration creates its player and video sink independently.
No audio implementation or diagnostic was replaced.
