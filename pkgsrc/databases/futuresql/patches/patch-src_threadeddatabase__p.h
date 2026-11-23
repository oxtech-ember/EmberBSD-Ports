$NetBSD$

Start each queued operation before a caller can wait for its result.
Cancel unfinished work when the receiver discards the queued call.

--- src/threadeddatabase_p.h.orig
+++ src/threadeddatabase_p.h
@@ -10,6 +10,7 @@
 #include <concepts>
 
 #include <QFuture>
+#include <QPromise>
 #include <QFutureWatcher>
 #include <QSqlQuery>
 #include <QSqlDatabase>
@@ -187,19 +188,18 @@
     template <typename Functor>
     QFuture<std::invoke_result_t<Functor>> runAsync(Functor func) {
         using ReturnType = std::invoke_result_t<Functor>;
-        QFutureInterface<ReturnType> interface;
-        QMetaObject::invokeMethod(this, [interface, func]() mutable {
+        QPromise<ReturnType> promise;
+        promise.start();
+        auto future = promise.future();
+        QMetaObject::invokeMethod(this, [promise = std::move(promise), func = std::move(func)]() mutable {
             if constexpr (!std::is_same_v<ReturnType, void>) {
-                auto result = func();
-                interface.reportResult(result);
+                promise.addResult(func());
             } else {
                 func();
             }
-
-            interface.reportFinished();
-        });
-
-        return interface.future();
+            promise.finish();
+        });
+        return future;
     }
 
     Row retrieveRow(const QSqlQuery &query);
