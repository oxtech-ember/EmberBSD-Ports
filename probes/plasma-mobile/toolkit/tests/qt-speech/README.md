# Installed Qt TextToSpeech on CM5

The full Qt TextToSpeech 6.12.0nb1 package uses the common
[speech providers](../../../../../profiles/common-media/speech.md).
Its Flite plugin now finds shared voice libraries under the package prefix;
previously it initialized with `No voices available`. The actual process
`LD_LIBRARY_PATH` is also read instead of consulting an empty environment.
No older Flite, Qt or C++ runtime is installed alongside the common provider.

```sh
CMAKE=/absolute/native-cmake NINJA=/absolute/native-ninja \
  PKG_CONFIG=/absolute/native-pkg-config \
  sh build.sh CROSS_TOOLS SYSROOT HOST_QT NEW_BUILD
```

Copy `NEW_BUILD/qt-speech` and `run.sh` to the board after installing the full
packages. With `/usr/pkg/bin` and `/usr/pkg/sbin` in PATH, run:

```sh
sh run.sh /absolute/qt-speech /absolute/new-results
```

The consumer explicitly selects `flite` or `speechd`, verifies available
voices/capabilities and waits for an active state followed by Ready. Flite
must supply nonempty Int16 mono PCM with bounded sample count and nonzero
energy. The speechd plugin speaks through an isolated Unix-socket server,
eSpeak and libao's null driver. An unavailable engine must be refused.
The mock plugin is never selected. Each mode runs in two separate processes.

Private HOME/XDG paths, timeouts and bounded service shutdown keep the check
separate from a desktop session. Service logs survive a failure. Forced
shutdown fails acceptance; successful output requires graceful termination.
A physical audio device is not opened by the speechd path. Flite's consumer
requests synthesis into memory, not playback.

On 2026-10-12, both engines, both processes, missing-engine refusal and service
shutdown pass on CM5 Rev 1.0 / BCM2712 D0. Flite supplies 46,640 samples per
process; speechd transitions Speaking → Ready through the real eSpeak module.
No claim is made that this Qt API test compares synthesized words semantically.
The [eSpeak checks](../../../../../profiles/common-media/speech.md) separately
compare upstream phoneme/WAV expectations and exact repeated file outputs.

The package SHA256 is
`60e29277bc26acba17efb0e7e70bd848bb0b22320b22c0687220e68d0caad9c1`.
The results archive SHA256 is
`4c22e30113665a404d638c7f6e4d72ca63497e058cc92c7c3bec66951558613a`.
Cppcheck 2.22 with the actual consumer compile database and GCC16's analyzer
pass. Valgrind is unavailable. Physical sound and full Plasma remain unaccepted.
