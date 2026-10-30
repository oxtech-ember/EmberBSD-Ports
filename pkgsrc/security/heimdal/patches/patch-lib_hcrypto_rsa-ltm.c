$NetBSD$

Use the shared LibTomMath provider.

--- lib/hcrypto/rsa-ltm.c.orig
+++ lib/hcrypto/rsa-ltm.c
@@ -39,6 +39,7 @@
 #include <rsa.h>
 
 #include "tommath.h"
+#include "heim_find_prime.h"
 
 static int
 random_num(mp_int *num, size_t len)
@@ -536,7 +537,7 @@
     do {
 	BN_GENCB_call(cb, 2, counter++);
 	CHECK(random_num(&p, bitsp), 0);
-	CHECK(mp_find_prime(&p,128), MP_YES);
+	CHECK(heim_find_prime(&p,128), MP_YES);
 
 	mp_sub_d(&p, 1, &t1);
 	mp_gcd(&t1, &el, &t2);
@@ -548,7 +549,7 @@
     do {
 	BN_GENCB_call(cb, 2, counter++);
 	CHECK(random_num(&q, bits - bitsp), 0);
-	CHECK(mp_find_prime(&q,128), MP_YES);
+	CHECK(heim_find_prime(&q,128), MP_YES);
 
 	if (mp_cmp(&p, &q) == 0) /* don't let p and q be the same */
 	    continue;
