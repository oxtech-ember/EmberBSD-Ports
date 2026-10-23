# Logging backtrace fallback

Qt 6.12.0's execinfo fallback takes a mutable pointer reference but reads const
backtrace storage. The adaptation copies each pointer before symbol lookup.
It handles a null allocation result before reading the returned string array.
NetBSD uses `backtrace_symbols_fmt` to retain symbols through Qt's existing parser.
Its default `backtrace_symbols` text has a different field order.
The adaptation keeps backtrace support enabled.

## Installed public API

Build the probe with the matching Qt SDK and normal cross toolchain:

```sh
cmake -S . -B /absolute/new-build -DCMAKE_TOOLCHAIN_FILE="$TOOLCHAIN" \
  -DCMAKE_PREFIX_PATH="$SYSROOT/usr/pkg/qt6" -DCMAKE_INSTALL_PREFIX=/usr/pkg
cmake --build /absolute/new-build -j2
DESTDIR="$STAGE" cmake --install /absolute/new-build
```

The same CMake project supports a native Qt build without a cross toolchain.
Run the installed `libexec/emberbsd-qt-tests/qt-backtrace-probe` on the target.
It logs from an exported, non-inlined C symbol and formats the actual handler
context through `qSetMessagePattern` and `qFormatLogMessage`.
Success requires the marker and the named function in the backtrace text.
The JSON contains the actual formatted message.
Compilation alone does not establish target symbol lookup.

## Focused source controls

```sh
CXX=/absolute/native/g++ ruby source-contract.rb /absolute/unpatched-qtbase \
  /absolute/target-build/compile_commands.json /absolute/native-qt6 /absolute/new-results
```

Use a configured target build and matching installed native Qt 6.12 Core.
The script verifies the original translation-unit hash and applies the real patch.
It compiles the full translation unit with the actual target command before and after.
Only the copied source/output paths and quoted-header search directory change.
The original const-reference compile failure must disappear.

Native controls extract the actual decoder and cleanup functions from that source.
The wrapper intercepts the symbol-allocation API for null and malformed-result cases.
The success case uses real native `backtrace_symbols` and an exported symbol.
A pointer-only control reproduces the unguarded null-result failure under Memcheck.
The final function must pass all three modes without altering stored addresses.
These are focused controls, not a full Qt memory audit or NetBSD execution.
The result retains exact commands, generated contexts, source hashes and raw logs.
