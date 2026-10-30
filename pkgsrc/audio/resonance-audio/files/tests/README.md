# Resonance Audio consumer check

Build `qt-wrapper-consumer.cpp` and Qt Multimedia's `src/resonance-audio/resonance_audio.cpp` against the installed `resonance_audio::resonance_audio`
CMake target. It exercises the public factory, a spatial sound source, and
the Qt wrapper's ambisonic and room-reverb buffers. The Qt wrapper stays in
Qt Multimedia under its original license.

Repeat on each selected native and target ABI. Test the provider's dependency
exports and PFFFT separately; the existence of a CMake target alone does not
establish spatial audio output.
