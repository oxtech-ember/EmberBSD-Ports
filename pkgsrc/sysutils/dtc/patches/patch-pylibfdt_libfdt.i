$NetBSD$

pylibfdt requires Python 3.8 or newer. SWIG 4.5 no longer supplies the
Python 2 PyString and PyInt compatibility aliases; use the Python 3
Unicode and integer interfaces directly.

--- pylibfdt/libfdt.i.orig
+++ pylibfdt/libfdt.i
@@ -1136,7 +1136,7 @@
 	PyObject *buff;
 
 	if ($1) {
-		resultobj = PyString_FromString(
+		resultobj = PyUnicode_FromString(
 			fdt_string(fdt1, fdt32_to_cpu($1->nameoff)));
 		buff = PyByteArray_FromStringAndSize(
 			(const char *)($1 + 1), fdt32_to_cpu($1->len));
@@ -1175,7 +1175,7 @@
 
 /* typemaps used for fdt_next_node() */
 %typemap(in, numinputs=1) int *depth (int depth) {
-   depth = (int) PyInt_AsLong($input);
+   depth = (int) PyLong_AsLong($input);
    $1 = &depth;
 }
 
