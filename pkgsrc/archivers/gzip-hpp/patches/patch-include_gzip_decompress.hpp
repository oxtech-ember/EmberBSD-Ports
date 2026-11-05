$NetBSD$

# Expose the bounded KiCad 10.0.8 decompression API in shared form.

--- include/gzip/decompress.hpp
+++ include/gzip/decompress.hpp
@@ -1,4 +1,9 @@
-#include <gzip/config.hpp>
+#ifndef GZIP_HPP_DECOMPRESS_HPP
+#define GZIP_HPP_DECOMPRESS_HPP
+
+#ifndef ZLIB_CONST
+#define ZLIB_CONST
+#endif
 
 // zlib
 #include <zlib.h>
@@ -10,96 +15,108 @@
 
 namespace gzip {
 
-class Decompressor
+inline void decompress(const char* data,
+                       std::size_t size,
+                       std::string& output,
+                       std::size_t max_uncompressed_size = 0,
+                       std::size_t buffering_size = 0)
 {
-    std::size_t max_;
+    if (buffering_size == 0)
+    {
+        buffering_size = (size * 2) - (size / 2) + 16;
+    }
+    z_stream inflate_s;
+    inflate_s.zalloc = Z_NULL;
+    inflate_s.zfree = Z_NULL;
+    inflate_s.opaque = Z_NULL;
+    inflate_s.avail_in = 0;
+    inflate_s.next_in = Z_NULL;
 
-  public:
-    Decompressor(std::size_t max_bytes = 1000000000) // by default refuse operation if compressed data is > 1GB
-        : max_(max_bytes)
-    {
-    }
+    // The windowBits parameter is the base two logarithm of the window size (the size of the history buffer).
+    // It should be in the range 8..15 for this version of the library.
+    // Larger values of this parameter result in better compression at the expense of memory usage.
+    // This range of values also changes the decoding type:
+    //  -8 to -15 for raw deflate
+    //  8 to 15 for zlib
+    // (8 to 15) + 16 for gzip
+    // (8 to 15) + 32 to automatically detect gzip/zlib header
+    constexpr int window_bits = 15 + 32; // auto with windowbits of 15
 
-    template <typename OutputType>
-    void decompress(OutputType& output,
-                    const char* data,
-                    std::size_t size) const
-    {
-        z_stream inflate_s;
+    constexpr unsigned int max_uint = std::numeric_limits<unsigned int>::max();
+    const unsigned int size_step = buffering_size > max_uint ? max_uint : static_cast<unsigned int>(buffering_size);
+        if( max_uncompressed_size != 0 && size_step > max_uncompressed_size )
+        {
+            throw std::runtime_error(
+                    "buffer size used during decompression of gzip will use more memory then allowed, "
+                    "either increase the limit or reduce the buffer size" );
+        }
 
-        inflate_s.zalloc = Z_NULL;
-        inflate_s.zfree = Z_NULL;
-        inflate_s.opaque = Z_NULL;
-        inflate_s.avail_in = 0;
-        inflate_s.next_in = Z_NULL;
-
-        // The windowBits parameter is the base two logarithm of the window size (the size of the history buffer).
-        // It should be in the range 8..15 for this version of the library.
-        // Larger values of this parameter result in better compression at the expense of memory usage.
-        // This range of values also changes the decoding type:
-        //  -8 to -15 for raw deflate
-        //  8 to 15 for zlib
-        // (8 to 15) + 16 for gzip
-        // (8 to 15) + 32 to automatically detect gzip/zlib header
-        constexpr int window_bits = 15 + 32; // auto with windowbits of 15
-
+#ifdef __GNUC__
 #pragma GCC diagnostic push
 #pragma GCC diagnostic ignored "-Wold-style-cast"
-        if (inflateInit2(&inflate_s, window_bits) != Z_OK)
+#endif
+    if (inflateInit2(&inflate_s, window_bits) != Z_OK)
+    {
+        throw std::runtime_error("inflate init failed");
+    }
+#ifdef __GNUC__
+#pragma GCC diagnostic pop
+#endif
+    inflate_s.next_in = reinterpret_cast<z_const Bytef*>(data);
+    inflate_s.avail_in = static_cast<unsigned int>(size);
+    std::string buffer(static_cast<std::size_t>(size_step), char());
+    do
+    {
+        inflate_s.avail_out = size_step;
+        inflate_s.next_out = reinterpret_cast<Bytef*>(&buffer[0]);
+        const int ret = inflate(&inflate_s, Z_FINISH);
+        if (ret != Z_STREAM_END && ret != Z_OK && ret != Z_BUF_ERROR)
         {
-            throw std::runtime_error("inflate init failed");
+            std::string error_msg = inflate_s.msg;
+            inflateEnd(&inflate_s);
+            throw std::runtime_error(error_msg);
         }
-#pragma GCC diagnostic pop
-        inflate_s.next_in = reinterpret_cast<z_const Bytef*>(data);
-
-#ifdef DEBUG
-        // Verify if size (long type) input will fit into unsigned int, type used for zlib's avail_in
-        std::uint64_t size_64 = size * 2;
-        if (size_64 > std::numeric_limits<unsigned int>::max())
+        if (max_uncompressed_size != 0 && (output.size() + size_step - inflate_s.avail_out) > max_uncompressed_size)
         {
             inflateEnd(&inflate_s);
-            throw std::runtime_error("size arg is too large to fit into unsigned int type x2");
+            throw std::runtime_error("size of output string will use more memory then intended when decompressing");
         }
-#endif
-        if (size > max_ || (size * 2) > max_)
-        {
-            inflateEnd(&inflate_s);
-            throw std::runtime_error("size may use more memory than intended when decompressing");
-        }
-        inflate_s.avail_in = static_cast<unsigned int>(size);
-        std::size_t size_uncompressed = 0;
-        do
-        {
-            std::size_t resize_to = size_uncompressed + 2 * size;
-            if (resize_to > max_)
-            {
-                inflateEnd(&inflate_s);
-                throw std::runtime_error("size of output string will use more memory then intended when decompressing");
-            }
-            output.resize(resize_to);
-            inflate_s.avail_out = static_cast<unsigned int>(2 * size);
-            inflate_s.next_out = reinterpret_cast<Bytef*>(&output[0] + size_uncompressed);
-            int ret = inflate(&inflate_s, Z_FINISH);
-            if (ret != Z_STREAM_END && ret != Z_OK && ret != Z_BUF_ERROR)
-            {
-                std::string error_msg = inflate_s.msg;
-                inflateEnd(&inflate_s);
-                throw std::runtime_error(error_msg);
-            }
+        output.append(buffer, 0, size_step - inflate_s.avail_out);
+    } while (inflate_s.avail_out == 0);
+    const int ret2 = inflateEnd(&inflate_s);
+    if (ret2 != Z_OK)
+    {
+        throw std::runtime_error("Unexpected gzip decompression error, state of stream was inconsistent");
+    }
+}
 
-            size_uncompressed += (2 * size - inflate_s.avail_out);
-        } while (inflate_s.avail_out == 0);
-        inflateEnd(&inflate_s);
-        output.resize(size_uncompressed);
-    }
-};
+inline void decompress(std::string const& input,
+                       std::string& output,
+                       std::size_t max_uncompressed_size = 0,
+                       std::size_t buffering_size = 0)
+{
+    return decompress(input.data(), input.size(), output, max_uncompressed_size, buffering_size);
+}
 
-inline std::string decompress(const char* data, std::size_t size)
+inline std::string decompress(const char* data,
+                              std::size_t size,
+                              std::size_t max_uncompressed_size = 0,
+                              std::size_t buffering_size = 0)
 {
-    Decompressor decomp;
     std::string output;
-    decomp.decompress(output, data, size);
+    decompress(data, size, output, max_uncompressed_size, buffering_size);
+    return output;
+}
+
+inline std::string decompress(std::string const& input,
+                              std::size_t max_uncompressed_size = 0,
+                              std::size_t buffering_size = 0)
+{
+    std::string output;
+    decompress(input.data(), input.size(), output, max_uncompressed_size, buffering_size);
     return output;
 }
 
 } // namespace gzip
+
+#endif // GZIP_HPP_DECOMPRESS_HPP