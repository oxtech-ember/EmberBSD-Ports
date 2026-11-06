$NetBSD$

Export the chord-length helper used by the separately linked C++ wrapper.
It is part of the shared C/C++ library interface and must remain visible when
Tinyspline is built with hidden default visibility.

--- src/tinyspline.h.orig
+++ src/tinyspline.h
@@ -2966,11 +2966,11 @@
  * @return TS_SUCCESS
  * 	On success.
  * @return TS_NO_RESULT
  * 	If \p num is \c 0.
  */
-tsError
+tsError TINYSPLINE_API
 ts_chord_lengths_length_to_knot(const tsReal *knots,
                                 const tsReal *lengths,
                                 size_t num,
                                 tsReal len,
                                 tsReal *knot,
