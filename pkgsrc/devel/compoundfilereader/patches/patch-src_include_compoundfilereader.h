$NetBSD$

# Carry KiCad 10.0.8's reader API and malformed-file guards. Supply the
# uint16_t char_traits compatibility when the selected implementation is libc++ 17+.
--- src/include/compoundfilereader.h
+++ src/include/compoundfilereader.h
@@ -1,23 +1,23 @@
 /**
     Microsoft Compound File (and Property Set) Reader
     http://en.wikipedia.org/wiki/Compound_File_Binary_Format
-    
+
     Format specification:
         MS-CFB: https://msdn.microsoft.com/en-us/library/dd942138.aspx
         MS-OLEPS: https://msdn.microsoft.com/en-us/library/dd942421.aspx
 
-    Note: 
+    Note:
     1. For simplification, the code assumes that the target system is little-endian.
-       
+
     2. The reader operates the passed buffer in-place.
        You must keep the input buffer valid when you are using the reader.
-       
+
     3. Single thread usage.
 
     Example 1: print all streams in a compound file
     \code
         CFB::CompoundFileReader reader(buffer, len);
-        reader.EnumFiles(reader.GetRootEntry(), -1, 
+        reader.EnumFiles(reader.GetRootEntry(), -1,
             [&](const CFB::COMPOUND_FILE_ENTRY* entry, const CFB::utf16string& dir, int level)->void
         {
             bool isDirectory = !reader.IsStream(entry);
@@ -31,12 +31,145 @@
 #pragma once
 
 #include <algorithm>
+#include <set>
 #include <stdint.h>
 #include <string.h>
 #include <exception>
 #include <stdexcept>
 #include <functional>
+#include <cstdio>
+#include <cwchar>
+#include <ios>
 #include <string>
+
+/***********************************************************************************************************************
+ * libc++ 17 and later no longer provide a generic char_traits template for non-standard character types.
+ * Define the required uint16_t specialization for this header-only provider when using that library.
+ * The specialization supplies the operations needed by
+ * the JSON library.
+ *
+ * From: https://github.com/llvm/llvm-project/commit/c3668779c13596e223c26fbd49670d18cd638c40
+ *
+ * Part of the LLVM Project, under the Apache License v2.0 with LLVM Exceptions.
+ * See https://llvm.org/LICENSE.txt for license information.
+ * SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
+ *
+ **********************************************************************************************************************/
+
+#if defined(_LIBCPP_VERSION) && _LIBCPP_VERSION >= 170000
+
+template <>
+struct std::char_traits<uint16_t>
+{
+    using char_type = uint16_t;
+    using int_type = int;
+    using off_type = std::streamoff;
+    using pos_type = std::streampos;
+    using state_type = mbstate_t;
+
+    static inline void assign( char_type& __c1, const char_type& __c2 ) noexcept { __c1 = __c2; }
+
+    static inline bool eq( char_type __c1, char_type __c2 ) noexcept { return __c1 == __c2; }
+
+    static inline bool lt( char_type __c1, char_type __c2 ) noexcept { return __c1 < __c2; }
+
+    static constexpr int compare( const char_type* __s1, const char_type* __s2, size_t __n )
+    {
+        for( ; __n; --__n, ++__s1, ++__s2 )
+        {
+            if( lt( *__s1, *__s2 ) )
+                return -1;
+
+            if( lt( *__s2, *__s1 ) )
+                return 1;
+        }
+
+        return 0;
+    }
+
+    static size_t length( const char_type* __s )
+    {
+        size_t __len = 0;
+
+        for( ; !eq( *__s, char_type( 0 ) ); ++__s )
+            ++__len;
+
+        return __len;
+    }
+
+    static constexpr const char_type* find( const char_type* __s, size_t __n, const char_type& __a )
+    {
+        for( ; __n; --__n )
+        {
+            if( eq( *__s, __a ) )
+                return __s;
+            ++__s;
+        }
+
+        return nullptr;
+    }
+
+    static constexpr char_type* move( char_type* __s1, const char_type* __s2, size_t __n )
+    {
+        if( __n == 0 )
+            return __s1;
+
+        char_type* __r = __s1;
+
+        if( __s1 < __s2 )
+        {
+            for( ; __n; --__n, ++__s1, ++__s2 )
+                assign( *__s1, *__s2 );
+        }
+        else if( __s2 < __s1 )
+        {
+            __s1 += __n;
+            __s2 += __n;
+
+            for( ; __n; --__n )
+                assign( *--__s1, *--__s2 );
+        }
+
+        return __r;
+    }
+
+    static constexpr char_type* copy( char_type* __s1, const char_type* __s2, size_t __n )
+    {
+        char_type* __r = __s1;
+
+        for( ; __n; --__n, ++__s1, ++__s2 )
+            assign( *__s1, *__s2 );
+
+        return __r;
+    }
+
+    static char_type* assign( char_type* __s, size_t __n, char_type __a )
+    {
+        char_type* __r = __s;
+
+        for( ; __n; --__n, ++__s )
+            assign( *__s, __a );
+
+        return __r;
+    }
+
+    static inline constexpr int_type not_eof( int_type __c ) noexcept
+    {
+        return eq_int_type( __c, eof() ) ? ~eof() : __c;
+    }
+
+    static inline char_type to_char_type( int_type __c ) noexcept { return char_type( __c ); }
+
+    static inline int_type to_int_type( char_type __c ) noexcept { return static_cast<int_type>( __c ); }
+
+    static inline constexpr bool eq_int_type( int_type __c1, int_type __c2 ) noexcept { return __c1 == __c2; }
+
+    static inline constexpr int_type eof() noexcept { return static_cast<int_type>( EOF ); }
+};
+
+#endif
+
+/**********************************************************************************************************************/
 
 namespace CFB
 {
@@ -102,7 +235,7 @@
     uint32_t systemIdentifier;
     unsigned char clsid[16];
     uint32_t numPropertySets;
-    struct 
+    struct
     {
         char fmtid[16];
         uint32_t offset;
@@ -132,7 +265,8 @@
     }
 };
 
-typedef std::function<void(const COMPOUND_FILE_ENTRY*, const std::u16string& dir, int level)> 
+typedef std::basic_string<uint16_t> utf16string;
+typedef std::function<int(const COMPOUND_FILE_ENTRY*, const utf16string& dir, int level)>
     EnumFilesCallback;
 
 class CompoundFileReader
@@ -165,7 +299,7 @@
         m_miniStreamStartSector = root->startSectorLocation;
     }
 
-    /// Get entry (directory or file) by its ID. 
+    /// Get entry (directory or file) by its ID.
     /// Pass "0" to get the root directory entry. -- This is the start point to navigate the compound file.
     /// Use the returned object to access child entries.
     const COMPOUND_FILE_ENTRY* GetEntry(size_t entryID) const
@@ -225,35 +359,61 @@
 
     void EnumFiles(const COMPOUND_FILE_ENTRY* entry, int maxLevel, EnumFilesCallback callback) const
     {
-        std::u16string dir;
-        EnumNodes(GetEntry(entry->childID), 0, maxLevel, dir, callback);
+        // KiCad: the directory ids come from an untrusted file, so a cyclic or self-referential
+        // sibling recursed here until the stack was gone. Sibling recursion carries the same
+        // level, so maxLevel cannot bound it; track the ids already visited instead.
+        utf16string dir;
+        std::set<uint32_t> visited;
+        visited.insert(entry->childID);
+        EnumNodes(GetEntry(entry->childID), 0, maxLevel, dir, callback, visited);
     }
 
 private:
 
+    // KiCad: nameLen is a file-supplied byte count over a fixed 32-unit array, and the callbacks
+    // hand it straight to UTF16ToWstring or rely on the name being terminated. MS-CFB requires it
+    // to be even, to include the terminator and to be at most 64, so validate before the callback
+    // rather than truncating a bad name into a different valid-looking one.
+    static bool HasValidName(const COMPOUND_FILE_ENTRY* entry)
+    {
+        if (entry->nameLen < 2 || entry->nameLen > 64 || (entry->nameLen % 2) != 0)
+            return false;
+
+        return entry->name[entry->nameLen / 2 - 1] == 0;
+    }
+
     // Enum entries with same level, including 'entry' itself
-    void EnumNodes(const COMPOUND_FILE_ENTRY* entry, int currentLevel, int maxLevel, 
-        const std::u16string& dir, EnumFilesCallback callback) const
+    void EnumNodes(const COMPOUND_FILE_ENTRY* entry, int currentLevel, int maxLevel,
+        const utf16string& dir, EnumFilesCallback callback, std::set<uint32_t>& visited) const
     {
         if (maxLevel > 0 && currentLevel >= maxLevel)
             return;
         if (entry == nullptr)
             return;
 
-        callback(entry, dir, currentLevel + 1);
+        // Only linked entries are reached, and MS-CFB requires every one of those to carry a
+        // valid name, so a bad length here means the directory is corrupt
+        if (!HasValidName(entry))
+            throw FileCorrupted();
+
+        if( callback(entry, dir, currentLevel + 1) != 0 )
+            return;
 
         const COMPOUND_FILE_ENTRY* child = GetEntry(entry->childID);
-        if (child != nullptr)
-        {
-            std::u16string newDir = dir;
+        if (child != nullptr && visited.insert(entry->childID).second)
+        {
+            utf16string newDir = dir;
             if (dir.length() != 0)
-                newDir.append(1, '\\');
-            newDir.append(reinterpret_cast<const char16_t*>(entry->name), entry->nameLen / 2 - 1);
-            EnumNodes(GetEntry(entry->childID), currentLevel + 1, maxLevel, newDir, callback);
-        }
-
-        EnumNodes(GetEntry(entry->leftSiblingID), currentLevel, maxLevel, dir, callback);
-        EnumNodes(GetEntry(entry->rightSiblingID), currentLevel, maxLevel, dir, callback);
+                newDir.append(1, '\n');
+            newDir.append(entry->name, entry->nameLen / 2 - 1);
+            EnumNodes(child, currentLevel + 1, maxLevel, newDir, callback, visited);
+        }
+
+        if (entry->leftSiblingID != 0xFFFFFFFF && visited.insert(entry->leftSiblingID).second)
+            EnumNodes(GetEntry(entry->leftSiblingID), currentLevel, maxLevel, dir, callback, visited);
+
+        if (entry->rightSiblingID != 0xFFFFFFFF && visited.insert(entry->rightSiblingID).second)
+            EnumNodes(GetEntry(entry->rightSiblingID), currentLevel, maxLevel, dir, callback, visited);
     }
 
     void ReadStream(size_t sector, size_t offset, char* buffer, size_t len) const
@@ -334,8 +494,8 @@
         {
             throw FileCorrupted();
         }
-        
-        
+
+
         LocateFinalSector(m_miniStreamStartSector, sector * m_minisectorSize + offset, &sector, &offset);
         return SectorOffsetToAddress(sector, offset);
     }
@@ -479,4 +639,4 @@
     const PROPERTY_SET_STREAM_HDR* m_hdr;
 };
 
-}
+}