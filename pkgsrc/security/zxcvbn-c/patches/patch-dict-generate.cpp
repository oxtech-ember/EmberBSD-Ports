# Add a named compiled dictionary descriptor without changing default output.
# Origin: EmberBSD.
--- dict-generate.cpp.orig
+++ dict-generate.cpp
@@ -23,6 +23,7 @@
  **********************************************************************************/
 
 #include <algorithm>
+#include <sstream>
 #include <cstdint>
 #include <iostream>
 #include <string>
@@ -1557,6 +1558,63 @@
     *Out << "#define ROOT_NODE_LOC " << Root->GetAddr() << "\n";
     return OutputSize + sizeof(unsigned int);
 }
+static bool ValidCIdentifier(const string &name)
+{
+    // Leave reserved implementation identifiers and POSIX typedef names to headers.
+    if (name.empty() || name[0] == '_' ||
+        (name.size() >= 2 && name.compare(name.size() - 2, 2, "_t") == 0) ||
+        !((name[0] >= 'A' && name[0] <= 'Z') ||
+                          (name[0] >= 'a' && name[0] <= 'z')))
+        return false;
+    for (size_t i = 1; i < name.size(); ++i)
+        if (!(name[i] == '_' || (name[i] >= 'A' && name[i] <= 'Z') ||
+              (name[i] >= 'a' && name[i] <= 'z') || (name[i] >= '0' && name[i] <= '9')))
+            return false;
+    static const char *const keywords[] = {
+        "auto", "break", "case", "char", "const", "continue", "default", "do", "double",
+        "else", "enum", "extern", "float", "for", "goto", "if", "inline", "int", "long",
+        "register", "restrict", "return", "short", "signed", "sizeof", "static", "struct",
+        "switch", "typedef", "union", "unsigned", "void", "volatile", "while", "_Alignas",
+        "_Alignof", "_Atomic", "_Bool", "_Complex", "_Generic", "_Imaginary", "_Noreturn",
+        "_Static_assert", "_Thread_local", "alignas", "alignof", "bool", "constexpr",
+        "false", "nullptr", "static_assert", "thread_local", "true", "typeof", "typeof_unqual"
+    };
+    for (size_t i = 0; i < sizeof(keywords) / sizeof(keywords[0]); ++i)
+        if (name == keywords[i]) return false;
+    // Generated arrays, macros and public API names share the C identifier namespace.
+    static const char *const reserved[] = {
+        "DictNodes", "Ranks", "ChildLocs", "WordEndBits", "ChildMap",
+        "EndCountLge", "EndCountSml", "CharSet", "SizeChildMapEntry", "NumLargeCounts",
+        "ND", "ROOT_NODE_LOC", "BITS_CHILD_PATT_INDEX", "BITS_CHILD_MAP_INDEX",
+        "SHIFT_CHILD_MAP_INDEX", "SHIFT_WORD_ENDING_BIT", "CHARSET_SIZE",
+        "ZXCVBN_DICTIONARY_H", "ZXCVBN_DICTIONARY_ABI", "ZXCVBN_DICTIONARY_CHAR_CAPACITY",
+        "ZXCVBN_H_F98183CE2A01_INCLUDED", "ZXCVBN_DETAIL_LEN", "MallocFn", "FreeFn",
+        "ZxcvbnDictionaryData", "ZxcvbnDictionary", "ZxcvbnDictionaryCreate",
+        "ZxcvbnDictionaryFree", "ZxcvbnMatchWithDictionary", "ZxcvbnInit", "ZxcvbnUnInit",
+        "ZxcvbnMatch", "ZxcvbnFreeInfo", "ZxcMatch_t", "ZxcTypeMatch_t",
+        "NON_MATCH", "BRUTE_MATCH", "DICTIONARY_MATCH", "DICT_LEET_MATCH", "USER_MATCH",
+        "USER_LEET_MATCH", "REPEATS_MATCH", "SEQUENCE_MATCH", "SPATIAL_MATCH", "DATE_MATCH",
+        "YEAR_MATCH", "LONG_PWD_MATCH", "MULTIPLE_MATCH", "size_t", "ptrdiff_t", "max_align_t",
+        "int8_t", "int16_t", "int32_t", "int64_t", "uint8_t", "uint16_t", "uint32_t", "uint64_t",
+        "int_least8_t", "int_least16_t", "int_least32_t", "int_least64_t",
+        "uint_least8_t", "uint_least16_t", "uint_least32_t", "uint_least64_t",
+        "int_fast8_t", "int_fast16_t", "int_fast32_t", "int_fast64_t",
+        "uint_fast8_t", "uint_fast16_t", "uint_fast32_t", "uint_fast64_t",
+        "intptr_t", "uintptr_t", "intmax_t", "uintmax_t"
+    };
+    for (size_t i = 0; i < sizeof(reserved) / sizeof(reserved[0]); ++i)
+        if (name == reserved[i]) return false;
+    return true;
+}
+
+static void ReplaceOnce(string &text, const string &from, const string &to)
+{
+    string::size_type pos = text.find(from);
+    if (pos == string::npos || text.find(from, pos + from.size()) != string::npos)
+        throw "unexpected generated dictionary declaration";
+    text.replace(pos, from.size(), to);
+}
+
 enum { OUT_C_CODE, OUT_BINARY, OUT_TESTER };
 /**********************************************************************************
  */
@@ -1567,7 +1625,7 @@
     int OutType = OUT_C_CODE;
     bool Verbose = false;
     bool Comments = false;
-    string FileName, HashFile;
+    string FileName, HashFile, ViewName;
     char *OutFile = 0;
     EntryMap_t Entries;
     FileInfo InInfo[10];
@@ -1623,6 +1681,13 @@
                     continue;
                 }
             }
+            if (FileName == "--descriptor")
+            {
+                if (++i >= argc || !ValidCIdentifier(argv[i]))
+                    throw "--descriptor requires a non-reserved C identifier";
+                ViewName = argv[i];
+                continue;
+            }
             if (FileName == "-v")
             {
                 Verbose = true;
@@ -1635,6 +1700,7 @@
                         "     -b        Generate a binary output file\n"
                         "     -t        Generate a test file for testing zxcvbn\n"
                         "     -c        Add comments to output file if C code mode\n"
+                        "     --descriptor NAME  Emit a named compiled dictionary descriptor (C mode)\n                        Use an unreserved name that does not conflict with included headers\n"
                         "     -r number Ignore words with rank greater than number (must be >=1000)\n"
                         "     -v        Additional information output\n"
                         "     -h Hfile  Write file checksum to file Hfile as C code (for -b mode)\n"
@@ -1649,6 +1715,8 @@
             if (NumFiles < int(sizeof InInfo / sizeof InInfo[0] - 1))
                 ++NumFiles;
         }
+        if (!ViewName.empty() && OutType != OUT_C_CODE)
+            throw "--descriptor requires C source output";
         CombineWordLists(Entries, InInfo, NumFiles);
         if (Verbose)
         {
@@ -1767,15 +1835,37 @@
                 fout->open(OutFile, ios_base::trunc);
             Out = fout.get();
         }
-        if (!OutFile && (OutType == OUT_C_CODE))
+        if (!OutFile && (OutType == OUT_C_CODE) && (ViewName.empty() || Verbose))
             cout << "*/\n";
 
         if (OutType == OUT_BINARY)
             i = OutputBinary(Out, HashFile, CharSet, ChildBits, ChildAddrs, NodeData, NodeEnds, Ranks);
         else if (OutType == OUT_TESTER)
             i = OutputTester(Out, Comments, Ranks);
-        else
+        else if (ViewName.empty())
             i = OutputCode(Out, Comments, CharSet, ChildBits, Root, ChildAddrs, NodeData, NodeEnds, Ranks);
+        else
+        {
+            std::ostringstream code;
+            i = OutputCode(&code, Comments, CharSet, ChildBits, Root, ChildAddrs, NodeData, NodeEnds, Ranks);
+            string text = code.str();
+            ReplaceOnce(text, "static const unsigned int DictNodes[", "static const uint32_t DictNodes[");
+            ReplaceOnce(text, NodeData.size() > numeric_limits<unsigned short>::max() ?
+                "static const unsigned int ChildLocs[" : "static const unsigned short ChildLocs[",
+                NodeData.size() > numeric_limits<unsigned short>::max() ?
+                "static const uint32_t ChildLocs[" : "static const uint16_t ChildLocs[");
+            ReplaceOnce(text, "static const unsigned short Ranks[", "static const uint16_t Ranks[");
+            *Out << "#include <stdint.h>\n#include <zxcvbn-dictionary.h>\n" << text;
+            *Out << "const ZxcvbnDictionaryData " << ViewName << " = {\n"
+                    "    ZXCVBN_DICTIONARY_ABI, sizeof(ZxcvbnDictionaryData),\n"
+                    "    DictNodes, sizeof(DictNodes) / sizeof(DictNodes[0]),\n"
+                    "    WordEndBits, sizeof(WordEndBits),\n"
+                    "    ChildLocs, sizeof(ChildLocs) / sizeof(ChildLocs[0]), sizeof(ChildLocs[0]),\n"
+                    "    Ranks, sizeof(Ranks) / sizeof(Ranks[0]),\n"
+                    "    ChildMap, sizeof(ChildMap), SizeChildMapEntry,\n"
+                    "    EndCountLge, sizeof(EndCountLge), EndCountSml, sizeof(EndCountSml),\n"
+                    "    CharSet, sizeof(CharSet), ROOT_NODE_LOC\n};\n";
+        }
 
         if (fout)
         {
