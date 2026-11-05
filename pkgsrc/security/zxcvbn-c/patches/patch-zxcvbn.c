# Add immutable per-call dictionary view plumbing while preserving the default API.
# Origin: EmberBSD.
--- zxcvbn.c.orig
+++ zxcvbn.c
@@ -23,6 +23,8 @@
  **********************************************************************************/
 
 #include <zxcvbn.h>
+#include "zxcvbn-dictionary-internal.h"
+#include <errno.h>
 #include <ctype.h>
 #include <string.h>
 #include <stdint.h>
@@ -496,18 +498,18 @@
     uint8_t UnLeet[sizeof L33TChr];
     uint8_t LeetCnv[sizeof L33TCnv / LEET_NORM_MAP_SIZE + 1];
     uint8_t First;
-    uint8_t PossChars[CHARSET_SIZE];
+    uint8_t PossChars[ZXCVBN_DICTIONARY_CHAR_CAPACITY];
 } DictWork_t;
 
 /**********************************************************************************
  * Given a map entry create a string of all possible characters for following to
  * a child node
  */
-static int ListPossibleChars(uint8_t *List, const uint8_t *Map)
+static int ListPossibleChars(const ZxcvbnDictionaryData *data, uint8_t *List, const uint8_t *Map)
 {
     unsigned int i, j, k;
     int Len = 0;
-    for(k = i = 0; i < SizeChildMapEntry; ++i, ++Map)
+    for(k = i = 0; i < data->ChildMapWidth; ++i, ++Map)
     {
         if (!*Map)
         {
@@ -518,7 +520,7 @@
         {
             if (*Map & (1<<j))
             {
-                *List++ = CharSet[k];
+                *List++ = data->CharSet[k];
                 ++Len;
             }
             ++k;
@@ -625,7 +627,7 @@
 /**********************************************************************************
  * Function that does the word matching
  */
-static void DoDictMatch(const uint8_t *Passwd, int Start, int MaxLen, DictWork_t *Wrk, ZxcMatch_t **Result, DictMatchInfo_t *Extra, int Lev)
+static void DoDictMatch(const ZxcvbnDictionaryData *data, const uint8_t *Passwd, int Start, int MaxLen, DictWork_t *Wrk, ZxcMatch_t **Result, DictMatchInfo_t *Extra, int Lev)
 {
     int Len;
     uint8_t TempLeet[LEET_NORM_MAP_SIZE];
@@ -636,7 +638,7 @@
     uint8_t *PossChars = Wrk->PossChars;
     int NumPossChrs = Wrk->NumPossChrs;
     const uint8_t *Pwd = Passwd;
-    uint32_t NodeData = DictNodes[NodeLoc];
+    uint32_t NodeData = data->Nodes[NodeLoc];
     Passwd += Start;
     for(Len = 0; *Passwd && (Len < MaxLen); ++Len, ++Passwd)
     {
@@ -653,8 +655,8 @@
             /* Get char and set of possible chars at current point in word. */
             const uint8_t *Bmap;
             c = *Passwd;
-            Bmap = ChildMap + (NodeData & ((1<<BITS_CHILD_PATT_INDEX)-1)) * SizeChildMapEntry;
-            NumPossChrs = ListPossibleChars(PossChars, Bmap);
+            Bmap = data->ChildMap + (NodeData & ((1<<BITS_CHILD_PATT_INDEX)-1)) * data->ChildMapWidth;
+            NumPossChrs = ListPossibleChars(data, PossChars, Bmap);
 
             /* Make it lowercase and update lowercase, uppercase counts */
             if (isupper(c))
@@ -702,7 +704,7 @@
                             w.LeetCnv[i] = *r;
                             AddLeetChr(*r, -1, w.Leeted, w.UnLeet);
                         }
-                        DoDictMatch(Pwd, Passwd - Pwd, MaxLen - Len, &w, Result, Extra, Lev+1);
+                        DoDictMatch(data, Pwd, Passwd - Pwd, MaxLen - Len, &w, Result, Extra, Lev+1);
                     }
                 }
                 return;
@@ -726,24 +728,24 @@
         /* Add all the end counts of the child nodes before the one that matches */
         x = (q - Wrk->PossChars);
         y = (NodeData >> BITS_CHILD_PATT_INDEX) & ((1 << BITS_CHILD_MAP_INDEX) - 1);
-        NodeLoc = ChildLocs[x+y];
+        NodeLoc = zxcvbn_dictionary_child(data, x+y);
         for(w=0; w<x; ++w)
         {
-            unsigned int Cloc = ChildLocs[w+y];
-            z = EndCountSml[Cloc];
-            if (Cloc < NumLargeCounts)
-                z += EndCountLge[Cloc]*256;
+            unsigned int Cloc = zxcvbn_dictionary_child(data, w+y);
+            z = data->SmallCounts[Cloc];
+            if (Cloc < data->LargeCount)
+                z += data->LargeCounts[Cloc]*256;
             Ord += z;
         }
 
         /* Move to next node */
-        NodeData = DictNodes[NodeLoc];
-        if (WordEndBits[NodeLoc >> 3] & (1<<(NodeLoc & 7)))
+        NodeData = data->Nodes[NodeLoc];
+        if (data->WordEnds[NodeLoc >> 3] & (1<<(NodeLoc & 7)))
         {
             /* Word matches, save result */
             unsigned int v;
             ZxcMatch_t *p;
-            v = Ranks[Ord];
+            v = data->Ranks[Ord];
             if (v & (1<<15))
                 v = (v & ((1 << 15) - 1)) * 4 + (1 << 15);
             Extra->Caps = Caps;
@@ -900,7 +902,7 @@
  *  Start   Where in the password to start attempting to match
  *  MaxLen  Maximum number characters to consider
  */
-static void DictionaryMatch(ZxcMatch_t **Result, const uint8_t *Passwd, int Start, int MaxLen)
+static void DictionaryMatch(const ZxcvbnDictionaryData *data, ZxcMatch_t **Result, const uint8_t *Passwd, int Start, int MaxLen)
 {
     DictWork_t Wrk;
     DictMatchInfo_t Extra;
@@ -908,9 +910,9 @@
     memset(&Extra, 0, sizeof Extra);
     memset(&Wrk, 0, sizeof Wrk);
     Wrk.Ordinal = 1;
-    Wrk.StartLoc = ROOT_NODE_LOC;
+    Wrk.StartLoc = data->Root;
     Wrk.Begin = Start;
-    DoDictMatch(Passwd+Start, 0, MaxLen, &Wrk, Result, &Extra, 0);
+    DoDictMatch(data, Passwd+Start, 0, MaxLen, &Wrk, Result, &Extra, 0);
 }
 
 
@@ -1573,7 +1575,7 @@
 /**********************************************************************************
  * Main function of the zxcvbn password entropy estimation
  */
-double ZxcvbnMatch(const char *Pwd, const char *UserDict[], ZxcMatch_t **Info)
+static double ZxcvbnMatchImpl(const ZxcvbnDictionaryData *data, const char *Pwd, const char *UserDict[], ZxcMatch_t **Info)
 {
     int i, j;
     ZxcMatch_t *Zp;
@@ -1599,7 +1601,7 @@
         int MaxLen = Len - i;
         /* Add all the 'paths' between groups of chars in the password, for current starting char */
         UserMatch(&(Nodes[i].Paths), UserDict, Passwd, i, MaxLen);
-        DictionaryMatch(&(Nodes[i].Paths), Passwd, i, MaxLen);
+        DictionaryMatch(data, &(Nodes[i].Paths), Passwd, i, MaxLen);
         DateMatch(&(Nodes[i].Paths), Passwd, i, MaxLen);
         SpatialMatch(&(Nodes[i].Paths), Passwd, i, MaxLen);
         SequenceMatch(&(Nodes[i].Paths), Passwd, i, MaxLen);
@@ -1618,7 +1620,7 @@
     {
         ZxcMatch_t *Path = 0;
         int MaxLen = Len - i;
-        DictionaryMatch(&Path, RevPwd, i, MaxLen);
+        DictionaryMatch(data, &Path, RevPwd, i, MaxLen);
         UserMatch(&Path, UserDict, RevPwd, i, MaxLen);
 
         /* Now transfer any reverse matches to the normal results */
@@ -1793,3 +1795,33 @@
         Info = p;
     }
 }
+
+/* The historical API continues to use the built-in or loaded dictionary. */
+double ZxcvbnMatch(const char *Pwd, const char *UserDict[], ZxcMatch_t **Info)
+{
+#ifdef USE_DICT_FILE
+    ZxcvbnDictionaryData data = { ZXCVBN_DICTIONARY_ABI, sizeof(ZxcvbnDictionaryData),
+        DictNodes, NumNodes, WordEndBits, NumWordEnd, ChildLocs, NumChildLocs, sizeof(*ChildLocs),
+        Ranks, NumRanks, ChildMap, NumChildMaps * SizeChildMapEntry, SizeChildMapEntry,
+        EndCountLge, NumLargeCounts, EndCountSml, NumSmallCounts, CharSet, SizeCharSet + 1, ROOT_NODE_LOC };
+#else
+    ZxcvbnDictionaryData data = { ZXCVBN_DICTIONARY_ABI, sizeof(ZxcvbnDictionaryData),
+        DictNodes, sizeof(DictNodes)/sizeof(*DictNodes), WordEndBits, sizeof(WordEndBits),
+        ChildLocs, sizeof(ChildLocs)/sizeof(*ChildLocs), sizeof(*ChildLocs),
+        Ranks, sizeof(Ranks)/sizeof(*Ranks), ChildMap, sizeof(ChildMap), SizeChildMapEntry,
+        EndCountLge, sizeof(EndCountLge), EndCountSml, sizeof(EndCountSml),
+        CharSet, sizeof(CharSet), ROOT_NODE_LOC };
+#endif
+    return ZxcvbnMatchImpl(&data, Pwd, UserDict, Info);
+}
+
+double ZxcvbnMatchWithDictionary(const ZxcvbnDictionary *dictionary, const char *Pwd,
+    const char *UserDict[], ZxcMatch_t **Info)
+{
+    if (!dictionary || !Pwd) {
+        if (Info) *Info = NULL;
+        errno = EINVAL;
+        return -1;
+    }
+    return ZxcvbnMatchImpl(&dictionary->Data, Pwd, UserDict, Info);
+}
