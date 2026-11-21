$NetBSD$

Verify Twidget element depth budget using bounded widget parse mode.

--- tests/core_tests.cpp.orig
+++ tests/core_tests.cpp
@@ -98,6 +98,30 @@
     // Unbuffered: a crash still shows the last check that ran.
     std::setvbuf(stdout, nullptr, _IONBF, 0);
     StubBackend backend;
+    {
+        Renderer bounded(300, 1, false, backend);
+        std::string ops = R"({"type":"ops","ops":[
+ {"op":"el","id":2,"tag":"html","adopt":"html","attrs":[]},
+ {"op":"el","id":3,"tag":"head","adopt":"head","attrs":[]},
+ {"op":"el","id":4,"tag":"body","adopt":"body","attrs":[]})";
+        constexpr int first = 10, last = 140;
+        for (int id = first; id <= last; ++id) {
+            ops += ", {\"op\":\"el\",\"id\":" + std::to_string(id) +
+                   ",\"tag\":\"div\",\"attrs\":[[\"style\",\"width:10px;height:10px\"]]}";
+        }
+        ops += ", {\"op\":\"ins\",\"parent\":4,\"id\":10,\"before\":null}";
+        for (int id = first + 1; id <= last; ++id) {
+            ops += ", {\"op\":\"ins\",\"parent\":" + std::to_string(id - 1) +
+                   ",\"id\":" + std::to_string(id) + ",\"before\":null}";
+        }
+        ops += "]}";
+        bounded.receive(parse(ops));
+        Json leaf = bounded.receive(parse(
+            "{\"type\":\"query\",\"qid\":1,\"query\":{\"q\":\"rect\",\"id\":" +
+            std::to_string(last) + "}}"))[0]["result"];
+        check(leaf["width"].asNumber() == 0,
+              "widget document depth budget omits content beyond the bounded parse depth");
+    }
     Renderer r(300, 1, false, backend);
     r.receive(parse(PAGE));
     r.receive(parse(R"({"type":"listen","types":["mouseover","mouseout","mouseenter","mouseleave","pointerenter","pointermove","dblclick","wheel","keydown","animationstart","animationiteration","transitionend"]})"));
