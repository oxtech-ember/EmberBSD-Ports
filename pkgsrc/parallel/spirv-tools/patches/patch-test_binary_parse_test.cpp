$NetBSD$

Use unsigned literals for 32-bit expected words.
GCC treats the two low-bit hexadecimal constants as signed int. GoogleTest
1.18 compares them with uint32_t words and -Werror rejects the signedness.

Origin: EmberBSD contributors (AI-assisted).
Source: Khronos SPIRV-Tools v2026.4,
commit ef96ed763b43b59b33b31b362f09a02b729fa1c9.
The upstream Apache-2.0 licence and authorship are unchanged.

--- test/binary_parse_test.cpp.orig
+++ test/binary_parse_test.cpp
@@ -55,6 +55,6 @@
   std::vector<uint32_t> words{0x01234567, 0x89abcdef};
   MaybeFlipWords(false, words.begin(), words.end());
   EXPECT_EQ(words.size(), size_t(2));
-  EXPECT_EQ(words[0], 0x01234567);
+  EXPECT_EQ(words[0], 0x01234567u);
   EXPECT_EQ(words[1], 0x89abcdef);
 }
@@ -63,6 +63,6 @@
   std::vector<uint32_t> words{0x01234567, 0x89abcdef};
   MaybeFlipWords(true, words.begin(), words.end());
   EXPECT_EQ(words.size(), size_t(2));
-  EXPECT_EQ(words[0], 0x67452301);
+  EXPECT_EQ(words[0], 0x67452301u);
   EXPECT_EQ(words[1], 0xefcdab89);
 }
