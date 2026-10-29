$NetBSD$

Carry MIT-licensed bounds and lifetime fixes from Assimp 6.0.5
(commits 36c3a19aa853, aadd49311abb, 3a0ee8792fad, e3f9cf5564a4,
13316790aaae and earlier changes), retaining the C++11 callback.
Preserve scalar length when a valid primitive ends at the buffer boundary,
and report release tag 0.5.2. The boundary fix is EmberBSD AI-assisted.

--- code/OpenDDLParser.cpp.orig
+++ code/OpenDDLParser.cpp
@@ -1,7 +1,7 @@
 /*-----------------------------------------------------------------------------------------------
 The MIT License (MIT)
 
-Copyright (c) 2014-2020 Kim Kulling
+Copyright (c) 2014-2025 Kim Kulling
 
 Permission is hereby granted, free of charge, to any person obtaining a copy of
 this software and associated documentation files (the "Software"), to deal in
@@ -38,7 +38,7 @@
 
 BEGIN_ODDLPARSER_NS
 
-static const char *Version = "0.4.0";
+static const char *Version = "0.5.2";
 
 namespace Grammar {
 
@@ -289,8 +289,8 @@
         if (nullptr != name && nullptr != node && nullptr != name->m_id->m_buffer) {
             const std::string nodeName(name->m_id->m_buffer);
             node->setName(nodeName);
-            delete name;
-        }
+        }
+        delete name;
 
         Property *first(nullptr);
         in = lookForNextToken(in, end);
@@ -583,6 +583,9 @@
     size_t prim_len(0);
     for (size_t i = 0; i < (size_t) Value::ValueType::ddl_types_max; i++) {
         prim_len = strlen(Grammar::PrimitiveTypeToken[i]);
+        if (static_cast<size_t>(end - in) < prim_len) {
+            continue;
+        }
         if (0 == strncmp(in, Grammar::PrimitiveTypeToken[i], prim_len)) {
             type = static_cast<Value::ValueType>(i);
             break;
@@ -595,6 +598,10 @@
     } else {
         in += prim_len;
     }
+    if (in >= end) {
+        len = 1;
+        return in;
+    }
 
     bool ok(true);
     if (*in == Grammar::OpenArrayToken[0]) {
@@ -602,13 +609,13 @@
         ++in;
         char *start(in);
         while (in != end) {
-            ++in;
             if (*in == Grammar::CloseArrayToken[0]) {
                 len = ::atoi(start);
                 ok = true;
                 ++in;
                 break;
             }
+            ++in;
         }
     } else {
         len = 1;
@@ -630,9 +637,9 @@
     if (nextName) {
         names.push_back(nextName);
     }
-    while (Grammar::CommaSeparator[0] == *in) {
+    while (in != end && Grammar::CommaSeparator[0] == *in) {
         in = getNextSeparator(in, end);
-        if (Grammar::CommaSeparator[0] == *in) {
+        if (in != end && Grammar::CommaSeparator[0] == *in) {
             in = parseName(in, end, &nextName);
             if (nextName) {
                 names.push_back(nextName);
@@ -655,7 +662,7 @@
     char *start(in);
 
     size_t len(0);
-    while (!isSeparator(*in) && in != end) {
+    while (in != end && !isSeparator(*in)) {
         ++in;
         ++len;
     }
@@ -688,7 +695,7 @@
 
     in = lookForNextToken(in, end);
     char *start(in);
-    while (!isSeparator(*in) && in != end) {
+    while (in != end && !isSeparator(*in)) {
         ++in;
     }
 
@@ -790,9 +797,12 @@
     if (*start == '\"') {
         ++start;
         ++in;
-        while (*in != '\"' && in != end) {
+        while (in != end && *in != '\"') {
             ++in;
             ++len;
+        }
+        if (in == end) {
+            return in;
         }
 
         *stringData = ValueAllocator::allocPrimData(Value::ValueType::ddl_string, len);
@@ -831,7 +841,7 @@
     bool ok(true);
     char *start(in);
     int pos(0);
-    while (!isSeparator(*in) && in != end) {
+    while (in != end && !isSeparator(*in)) {
         if ((*in < '0' && *in > '9') || (*in < 'a' && *in > 'f') || (*in < 'A' && *in > 'F')) {
             ok = false;
             break;
