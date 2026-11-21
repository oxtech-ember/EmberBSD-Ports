$NetBSD$

Origin: EmberBSD contributors (AI-assisted).
Normalize Python dictionary keys at the libplist boundary and recognize
binary plist bytes from memory and file-like objects.

--- cython/plist.pyx.orig
+++ cython/plist.pyx
@@ -599,15 +599,28 @@
     instance._c_node = c_node
     return instance
 
-cdef plist_t create_dict_plist(object value=None):
-    cdef plist_t node = NULL
-    cdef plist_t c_node = NULL
-    node = plist_new_dict()
-    if value is not None and isinstance(value, dict):
-        for key, item in value.items():
-            c_node = native_to_plist_t(item)
-            plist_dict_set_item(node, key, c_node)
-            c_node = NULL
+cdef unicode dict_text_key(object key):
+    if isinstance(key, bytes):
+        key = key.decode('utf-8')
+    if not isinstance(key, unicode):
+        raise TypeError('plist dictionary keys must be str or UTF-8 bytes')
+    if '\0' in key:
+        raise ValueError('plist dictionary keys cannot contain NUL')
+    return key
+
+cdef plist_t create_dict_plist(object value=None) except NULL:
+    cdef plist_t node = plist_new_dict()
+    cdef bytes encoded_key
+    if node is NULL:
+        raise MemoryError()
+    try:
+        if value is not None and isinstance(value, dict):
+            for key, item in value.items():
+                encoded_key = dict_text_key(key).encode('utf-8')
+                plist_dict_set_item(node, encoded_key, native_to_plist_t(item))
+    except:
+        plist_free(node)
+        raise
     return node
 
 cimport cpython
@@ -670,20 +683,20 @@
         return dict([(key, value.get_value()) for key, value in self.items()])
 
     cpdef set_value(self, dict value):
+        cdef plist_t replacement = create_dict_plist(value)
         plist_free(self._c_node)
         self._map = {}
-        self._c_node = NULL
-        self._c_node = create_dict_plist(value)
+        self._c_node = replacement
         self._init()
 
     def __iter__(self):
         return self._map.__iter__()
 
     cpdef bint has_key(self, key):
-        return self._map.has_key(key)
+        return dict_text_key(key) in self._map
 
     cpdef object get(self, key, default=None):
-        return self._map.get(key, default)
+        return self._map.get(dict_text_key(key), default)
 
     cpdef list keys(self):
         return cpython.PyDict_Keys(self._map)
@@ -704,21 +717,26 @@
         return self._map.itervalues()
 
     def __getitem__(self, key):
-        return self._map[key]
+        return self._map[dict_text_key(key)]
 
     def __setitem__(self, key, value):
+        cdef unicode text_key = dict_text_key(key)
+        cdef bytes encoded_key = text_key.encode("utf-8")
         cdef Node n
         if isinstance(value, Node):
             n = value.copy()
         else:
             n = plist_t_to_node(native_to_plist_t(value), False)
 
-        plist_dict_set_item(self._c_node, key, n._c_node)
-        self._map[key] = n
+        plist_dict_set_item(self._c_node, encoded_key, n._c_node)
+        n._c_managed = False
+        self._map[text_key] = n
 
     def __delitem__(self, key):
-        cpython.PyDict_DelItem(self._map, key)
-        plist_dict_remove_item(self._c_node, key.encode('utf-8'))
+        cdef unicode text_key = dict_text_key(key)
+        cdef bytes encoded_key = text_key.encode('utf-8')
+        cpython.PyDict_DelItem(self._map, text_key)
+        plist_dict_remove_item(self._c_node, encoded_key)
 
 cdef Dict Dict_factory(plist_t c_node, bint managed=True):
     cdef Dict instance = Dict.__new__(Dict)
@@ -899,14 +917,14 @@
 FMT_BINARY = 2
 
 cpdef object load(fp, fmt=None, use_builtin_types=True, dict_type=dict):
-    is_binary = fp.read(6) == 'bplist'
+    is_binary = fp.read(6) == b'bplist'
     fp.seek(0)
 
     cdef object cb = None
 
     if not fmt:
         if is_binary:
-            if 'b' not in fp.mode:
+            if 'b' not in getattr(fp, 'mode', 'b'):
                 raise IOError('File handle must be opened in binary (b) mode to read binary property lists')
             cb = from_bin
         else:
@@ -927,7 +945,7 @@
     return cb(fp.read())
 
 cpdef object loads(data, fmt=None, use_builtin_types=True, dict_type=dict):
-    is_binary = data[0:6] == 'bplist'
+    is_binary = data[0:6] == b'bplist'
 
     cdef object cb = None
 
