$NetBSD$

Origin: EmberBSD (AI-assisted), local, not submitted upstream.
Do not refuse a map tile request when Qt reports no network
reachability. NetBSD has no QNetworkInformation backend, so QGC showed
"Network Not Available" and loaded no tiles. The request itself reports
the result for the tile server.

--- src/QtLocationPlugin/QGeoMapReplyQGC.cpp.orig
+++ src/QtLocationPlugin/QGeoMapReplyQGC.cpp
@@ -197,10 +197,8 @@
 
     Q_ASSERT(type == QGCMapTask::TaskType::taskFetchTile);
 
-    if (!QGCNetworkHelper::isInternetAvailable()) {
-        setError(QGeoTiledMapReply::CommunicationError, tr("Network Not Available"));
-        return;
-    }
+    // Reachability is advisory; this request and its QNetworkReply report the
+    // result for the actual tile endpoint.
 
     _request.setOriginatingObject(this);
 
