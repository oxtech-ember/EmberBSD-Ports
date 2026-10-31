$NetBSD$

Origin: EmberBSD contributors (AI-assisted), not submitted upstream.

Use OpenSSL 4 APIs and preserve valid ad-hoc signing with safe empty buffers.

--- ldid.cpp
+++ ldid.cpp
@@ -534,9 +534,9 @@
 }
 
 static inline void pad(std::streambuf &stream, size_t size) {
-    char padding[size];
-    memset(padding, 0, size);
-    put(stream, padding, size);
+    std::vector<char> padding(size, 0);
+    if (!padding.empty())
+        put(stream, padding.data(), padding.size());
 }
 
 template <typename Type_>
@@ -1374,6 +1374,8 @@
     }
 
     operator std::string() const {
+        if (size_ == 0)
+            return std::string();
         return std::string(static_cast<char *>(data_), size_);
     }
 };
@@ -2011,14 +2013,14 @@
             // however, I don't want to rely on that or detect the bypass before it
             // so, instead, I create my own compatible attribute and re-serialize it :/
 
-            ASN1_STRING *seq(ASN1_STRING_new());
-            _assert(seq != NULL);
-            _scope({ ASN1_STRING_free(seq); });
-            seq->length = ASN1_item_i2d((ASN1_VALUE *) cdattr, &seq->data, ASN1_ITEM_rptr(APPLE_CDATTR));
+            unsigned char *encoded(NULL);
+            int length = ASN1_item_i2d((ASN1_VALUE *) cdattr, &encoded, ASN1_ITEM_rptr(APPLE_CDATTR));
+            _assert(length > 0 && encoded != NULL);
+            _scope({ OPENSSL_free(encoded); });
 
             X509_ATTRIBUTE *attribute(NULL);
-            const unsigned char *data(seq->data);
-            _assert(d2i_X509_ATTRIBUTE(&attribute, &data, seq->length) != 0);
+            const unsigned char *data(encoded);
+            _assert(d2i_X509_ATTRIBUTE(&attribute, &data, length) != 0);
             _assert(attribute != NULL);
             _assert(sk_X509_ATTRIBUTE_push(attributes, attribute) != 0);
         }
@@ -2200,7 +2202,7 @@
 
 namespace ldid {
 
-static void get(std::string &value, X509_NAME *name, int nid) {
+static void get(std::string &value, const X509_NAME *name, int nid) {
     auto index(X509_NAME_get_index_by_NID(name, nid, -1));
     if (index < 0) {
         fprintf(stderr, "ldid: An error occursed while parsing the certificate: %s\n", ERR_error_string(ERR_get_error(), NULL));
@@ -2270,24 +2272,27 @@
     } else {
         Blobs blobs;
 
-        std::stringbuf requirement;
-        req(requirement, exprForm);
-        req(requirement, opAnd);
-        req(requirement, opIdent);
-        req(requirement, identifier);
-        req(requirement, opAnd);
-        req(requirement, opAppleGenericAnchor);
-        req(requirement, opAnd);
-        req(requirement, opCertField);
-        req(requirement, 0);
-        req(requirement, "subject.CN");
-        req(requirement, matchEqual);
-        req(requirement, common);
-        req(requirement, opCertGeneric);
-        req(requirement, 1);
-        req(requirement, (uint8_t []) {APPLE_EXTENSION_OID, 2, 1});
-        req(requirement, matchExists);
-        insert(blobs, 3, CSMAGIC_REQUIREMENT, requirement);
+        if (!key.empty()) {
+            std::stringbuf requirement;
+            req(requirement, exprForm);
+            req(requirement, opAnd);
+            req(requirement, opIdent);
+            req(requirement, identifier);
+            req(requirement, opAnd);
+            req(requirement, opAppleGenericAnchor);
+            req(requirement, opAnd);
+            req(requirement, opCertField);
+            req(requirement, 0);
+            req(requirement, "subject.CN");
+            req(requirement, matchEqual);
+            req(requirement, common);
+            req(requirement, opCertGeneric);
+            req(requirement, 1);
+            req(requirement, (uint8_t []) {APPLE_EXTENSION_OID, 2, 1});
+            req(requirement, matchExists);
+            insert(blobs, 3, CSMAGIC_REQUIREMENT, requirement);
+
+        }
 
         put(backing, CSMAGIC_REQUIREMENTS, blobs);
     }
@@ -3836,15 +3841,15 @@
                             for (int i = 0; i < sk_X509_num(certs); i++) {
                                 x = sk_X509_value(certs, i);
                                 int lastpos = -1;
-                                X509_NAME *nm = X509_get_subject_name(x);
-                                X509_NAME_ENTRY *e;
+                                const X509_NAME *nm = X509_get_subject_name(x);
+                                const X509_NAME_ENTRY *e;
 
                                 for (;;) {
                                     lastpos = X509_NAME_get_index_by_NID(nm, NID_commonName, lastpos);
                                     if (lastpos == -1)
                                         break;
                                     e = X509_NAME_get_entry(nm, lastpos);
-                                    ASN1_STRING *s = X509_NAME_ENTRY_get_data(e);
+                                    const ASN1_STRING *s = X509_NAME_ENTRY_get_data(e);
                                     printf("Authority=%s\n", reinterpret_cast<const char *>(ASN1_STRING_get0_data(s)));
                                 }
                             }
