$NetBSD$

Origin: EmberBSD (AI-assisted), local, not submitted upstream.
Include <cstdlib> for malloc(), realloc() and free(). libc++ does not
provide them through the other headers.

--- pkgsrc-deps/ulog_cpp/ulog_cpp/reader.cpp.orig
+++ pkgsrc-deps/ulog_cpp/ulog_cpp/reader.cpp
@@ -5,6 +5,7 @@
 
 #include "reader.hpp"
 
+#include <cstdlib>
 #include <cstring>
 
 #include "raw_messages.hpp"
@@ -45,14 +46,14 @@
     _data_handler_interface->error("Reader requires little endian", false);
     _state = State::InvalidData;
   }
-  _partial_message_buffer = static_cast<uint8_t*>(malloc(kBufferSizeInit));
+  _partial_message_buffer = static_cast<uint8_t*>(std::malloc(kBufferSizeInit));
   _partial_message_buffer_length_capacity = kBufferSizeInit;
 }
 
 Reader::~Reader()
 {
   if (_partial_message_buffer) {
-    free(_partial_message_buffer);
+    std::free(_partial_message_buffer);
   }
 }
 
@@ -94,7 +95,7 @@
             // Overflow, resize buffer
             _partial_message_buffer_length_capacity = _partial_message_buffer_length + num_append;
             _partial_message_buffer = static_cast<uint8_t*>(
-                realloc(_partial_message_buffer, _partial_message_buffer_length_capacity));
+                std::realloc(_partial_message_buffer, _partial_message_buffer_length_capacity));
             DBG_PRINTF("%i: resized partial buffer to %i\n", _total_num_read,
                        _partial_message_buffer_length_capacity);
           }
