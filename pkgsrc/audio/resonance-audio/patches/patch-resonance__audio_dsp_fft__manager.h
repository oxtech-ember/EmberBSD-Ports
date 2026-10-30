$NetBSD$

Use the installed common PFFFT header.

--- resonance_audio/dsp/fft_manager.h.orig
+++ resonance_audio/dsp/fft_manager.h
@@ -17,7 +17,7 @@
 #ifndef RESONANCE_AUDIO_DSP_FFT_MANAGER_H_
 #define RESONANCE_AUDIO_DSP_FFT_MANAGER_H_
 
-#include "pffft.h"
+#include <pffft/pffft.h>
 #include "base/audio_buffer.h"
 
 namespace vraudio {
