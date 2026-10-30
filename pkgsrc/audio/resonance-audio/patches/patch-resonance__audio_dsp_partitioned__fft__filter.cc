$NetBSD$

Use the installed common PFFFT header.

--- resonance_audio/dsp/partitioned_fft_filter.cc.orig
+++ resonance_audio/dsp/partitioned_fft_filter.cc
@@ -23,7 +23,7 @@
 
 #include <algorithm>
 
-#include "pffft.h"
+#include <pffft/pffft.h>
 #include "base/constants_and_types.h"
 #include "base/logging.h"
 #include "base/misc_math.h"
