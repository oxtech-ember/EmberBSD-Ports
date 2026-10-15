# VNC screen lifetime regression

The Qt 6.12.0 VNC plugin initialized its screen in both the screen constructor
and the integration initializer. The second call replaced an allocated dirty
map. The screen destructor also failed to release its final dirty map.
Each map owns a tile array and a full-screen comparison buffer.

The canonical `qvncscreen.cpp` patch leaves initialization to the integration
and deletes the final map during screen destruction. It preserves Qt ownership
of the platform screen and the VNC server shutdown order.

Run this small native regression against a real installed Qt prefix:

```sh
CXX=/path/to/native/g++ sh run.sh /absolute/qt6/prefix /absolute/new-results
```

Run once with the unpatched provider and once with the rebuilt provider.
Keep both result directories. The test builds a strict C++17 consumer with
the native GCC16 compiler. It creates the real installed `vnc` QPA screen,
checks its 160×128 geometry, runs the event loop, and destroys the application.
The server requests port zero, so the kernel selects a free port.

Memcheck checks definite, indirect and possible leaks. Any such error fails.
No suppression file or replacement VNC implementation is used.
Compiler versions, the actual compilation database, environment, raw output
and the complete Memcheck log remain in the result directory.

This test isolates the initialization and teardown defect. It does not require
a VNC client and does not prove displayed frames, RTP reception or playback.
The four-stream Qt Multimedia example must also pass its actual display and
full-player Memcheck scenario after the provider is rebuilt.

## Matched native plugin control

For an incremental native control, build the actual upstream VNC subdirectory
against the same installed Qt 6.12.0 private libraries:

```sh
cmake -S build-plugin -B /absolute/new-plugin-build -G Ninja \
    -DCMAKE_C_COMPILER=/path/to/native/gcc \
    -DCMAKE_CXX_COMPILER=/path/to/native/g++ \
    -DCMAKE_PREFIX_PATH=/absolute/qt6/prefix \
    -DQTBASE_SOURCE_DIR=/absolute/matching/qtbase-source \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
cmake --build /absolute/new-plugin-build --target QVncIntegrationPlugin -j2
```

The source directory must contain the real `src/plugins/platforms/vnc`
subdirectory with the canonical patch. An isolated byte-verified copy of that
subdirectory is sufficient. The helper uses Qt BuildInternals and the original
upstream CMake target. It does not copy the VNC implementation into the test.
Keep the original plugin and its hash before replacing an installed control.
Record source hashes, the exact SDK identity, commands and final plugin hash.
This plugin-only control is not a fresh build of the whole Qt SDK.
