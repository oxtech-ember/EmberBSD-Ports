$NetBSD$

Initialize the extra Huffman decoder look-ahead word before serializing it.
PushValue initializes the data words, but not this final padding word.
The outer Lerc2 checksum covers the padding too. Its uninitialized bytes
cause an uninitialized conditional in the upstream lossless float sample.
This preserves the stream size, code table, payload bits and decoder ABI.
Origin: EmberBSD (AI-assisted).

--- src/LercLib/fpl_EsriHuffman.cpp.orig
+++ src/LercLib/fpl_EsriHuffman.cpp
@@ -441,6 +441,9 @@ int fpl_EsriHuffman::EncodeHuffman (const char *input, size_t input_len, unsigned cha
     }
 
     size_t numUInts = (bitPos > 0 ? 1 : 0) + 1;    // add one more as the decode LUT can read ahead
+    // The checksum includes the extra look-ahead word as well as the data.
+    memset(*ppByte + (numUInts - 1) * sizeof(unsigned int), 0,
+        sizeof(unsigned int));
     *ppByte += numUInts * sizeof(unsigned int);
 
     int ret = (int)(*ppByte - originalPtr);
