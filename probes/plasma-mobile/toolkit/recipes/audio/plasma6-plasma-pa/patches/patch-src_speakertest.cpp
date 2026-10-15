# Origin: EmberBSD (AI-assisted).
# libcanberra calls the finish callback only after CA_SUCCESS.
# Free the callback data when all fallback requests fail synchronously.
# Upstream: not submitted.

--- src/speakertest.cpp.orig
+++ src/speakertest.cpp
@@ -69,7 +69,7 @@ void SpeakerTest::testChannel(const QString &name)
     snprintf(dev, sizeof(dev), "%lu", (unsigned long)m_sink->index());
     ca_context_change_device(context, dev);
 
-    void *cb_data = new CallbackData{this, name};
+    auto *cb_data = new CallbackData{this, name};
 
     ca_proplist *proplist;
     ca_proplist_create(&proplist);
@@ -90,6 +90,7 @@ void SpeakerTest::testChannel(const QString &name)
                                      QString()}) {
         if (soundName.isEmpty()) {
             // We are here because all of the fallback sounds failed to play
+            delete cb_data;
             playingFinished(name, error_code);
             break;
         }
