# Resonance Audio validation boundary

This provider uses the final archived upstream commit and retains the Qt 6.12.0
core changes needed by Spatial Audio. Its factory retains upstream C linkage;
the Qt wrapper uses the versioned C++ interface and the shared Eigen and PFFFT
providers. The upstream SADIE generated assets and their license and origin
notice are retained. The recipe keeps the previous Qt 32-bit scalar fallback.

The native Darwin arm64 package built. An installed CMake consumer compiled
the actual Qt wrapper and rendered a nonzero stereo buffer; it also exercised
the ambisonic and two room-reverb buffers. The same bounded consumer passed
ASan, UBSan and enabled LeakSanitizer against an instrumented provider.
Clang Static Analyzer reported no diagnostics for the three changed graph
translation units. Cppcheck reported existing upstream findings in those units;
comparison identified the same findings aside from a namespace change in one
style message and two upstream pointer-cast findings removed by Qt's fix.
This is not a claim of a clean upstream Cppcheck run.

The EmberBSD amd64 package built against the common providers. Its ELF records
`libpffft.so.1` and `libpthread.so.1` and exports the factory and Qt wrapper's
required C++ methods. The same standalone Qt wrapper consumer passed on the
target in an isolated runtime environment. The standalone wrapper uses only
Resonance and standard C++ headers; the executable has no Qt DSO dependency.
This does not claim a Qt Multimedia module build or a Plasma audio session.
