$NetBSD$

Include shared Parson and retain KiCad's natural interpolation workspace layout.
Move the interior solution before writing the first point: their old locations
overlap for three points in dimensions greater than two. This ordering repair
and its public-API regression are local EmberBSD changes (AI-assisted).
--- src/tinyspline.c
+++ src/tinyspline.c
@@ -1,6 +1,6 @@
 #define TINYSPLINE_EXPORT
 #include "tinyspline.h"
-#include "parson.h" /* serialization */
+#include <parson.h> /* serialization */
 
 #include <stdlib.h> /* malloc, free */
 #include <math.h>   /* fabs, sqrt, acos */
@@ -953,7 +953,7 @@
 	const size_t len_points = num_points * dimension;
 	const size_t num_int_points = num_points - 2;
 	const size_t len_int_points = num_int_points * dimension;
-	tsReal *buffer, *a, *b, *c, *d;
+	tsReal *thomas, *a, *b, *c, *d;
 	size_t i, j, k, l;
 	tsError err;
 
@@ -970,28 +970,26 @@
 			points, num_points, dimension, spline, status);
 	}
 	/* `num_points` >= 3 */
-	buffer = NULL;
+	thomas = NULL;
 	TS_TRY(try, err, status)
-		buffer = (tsReal *) malloc(
+		thomas = (tsReal *) malloc(
 			/* `a', `b', `c' (note that `c' is equal to `a') */
 			2 * num_int_points * sizeof(tsReal) +
-			/* At first: `d' Afterwards: The result of the thomas
-			 * algorithm including the first and last point to be
-			 * interpolated. */
+			/* `d' and "result of the thomas algorithm" (which
+			   contains `num_points' points) */
 			num_points * dimension * sizeof(tsReal));
-		if (!buffer) {
+		if (!thomas) {
 			TS_THROW_0(try, err, status, TS_MALLOC,
 			           "out of memory")
 		}
 		/* The system of linear equations is taken from:
 		 *     http://www.bakoma-tex.com/doc/generic/pst-bspline/
 		 *     pst-bspline-doc.pdf */
-		a = c = buffer;
+		a = c = thomas;
 		ts_arr_fill(a, num_int_points, 1);
 		b = a + num_int_points;
 		ts_arr_fill(b, num_int_points, 4);
-		d = b + num_int_points /* shift to the beginning of `d' */
-		      + dimension; /* make space for the first point */
+		d = b + num_int_points;
 		/* 6 * S_{i+1} */
 		for (i = 0; i < num_int_points; i++) {
 			for (j = 0; j < dimension; j++) {
@@ -1019,16 +1017,17 @@
 			        a, b, c, num_int_points, dimension, d,
 			        status))
 		}
-		memcpy(d - dimension, points, sof_ctrlp);
-		memcpy(d + num_int_points * dimension,
-		       points + (num_points-1) * dimension,
-		       sof_ctrlp);
+		memmove(thomas + dimension, d, num_int_points * sof_ctrlp);
+		memcpy(thomas, points, sof_ctrlp);
+		memcpy(thomas + (num_int_points+1) * dimension,
+		       points + (num_points-1) * dimension, sof_ctrlp);
 		TS_CALL(try, err, ts_int_relaxed_uniform_cubic_bspline(
-		        d - dimension, num_points, dimension, spline, status))
+		        thomas, num_points, dimension, spline, status))
 	TS_CATCH(err)
 		ts_bspline_free(spline);
 	TS_FINALLY
-		if (buffer) free(buffer);
+		if (thomas)
+			free(thomas);
 	TS_END_TRY_RETURN(err)
 }
 
