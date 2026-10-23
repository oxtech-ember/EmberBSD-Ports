$NetBSD$

Origin: EmberBSD (AI-assisted), not submitted upstream.

Pass long values to the variadic curl options. These options require long.
Keep the values and upstream behavior unchanged.

https://curl.se/libcurl/c/CURLOPT_NOSIGNAL.html
https://curl.se/libcurl/c/CURLOPT_FOLLOWLOCATION.html
https://curl.se/libcurl/c/CURLOPT_CONNECTTIMEOUT.html

--- src/backend/px-manager.c.orig
+++ src/backend/px-manager.c
@@ -399,10 +399,10 @@
   if (g_str_has_prefix (url, "pac+"))
     url += 4;
 
-  if (curl_easy_setopt (self->curl, CURLOPT_NOSIGNAL, 1) != CURLE_OK)
+  if (curl_easy_setopt (self->curl, CURLOPT_NOSIGNAL, 1L) != CURLE_OK)
     g_debug ("Could not set NOSIGNAL, continue");
 
-  if (curl_easy_setopt (self->curl, CURLOPT_FOLLOWLOCATION, 1) != CURLE_OK)
+  if (curl_easy_setopt (self->curl, CURLOPT_FOLLOWLOCATION, 1L) != CURLE_OK)
     g_debug ("Could not set FOLLOWLOCATION, continue");
 
   if (curl_easy_setopt (self->curl, CURLOPT_NOPROXY, "*") != CURLE_OK) {
@@ -410,7 +410,7 @@
     return NULL;
   }
 
-  if (curl_easy_setopt (self->curl, CURLOPT_CONNECTTIMEOUT, 30) != CURLE_OK)
+  if (curl_easy_setopt (self->curl, CURLOPT_CONNECTTIMEOUT, 30L) != CURLE_OK)
     g_debug ("Could not set CONENCTIONTIMEOUT, continue");
 
   if (curl_easy_setopt (self->curl, CURLOPT_USERAGENT, "libproxy") != CURLE_OK)
