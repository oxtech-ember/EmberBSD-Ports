$NetBSD$

Select input formats and preserve native resource forks safely.

--- a/ResourceFiles/ResourceFork.h
+++ b/ResourceFiles/ResourceFork.h
@@ -39,6 +39,8 @@
 
     Resources() {}
     Resources(std::istream& in);
+    // Reject malformed fork offsets before modifying this collection.
+    bool readChecked(const std::string& bytes);
     void writeFork(std::ostream& out) const;
     void addResource(Resource res) { resources[res.getTypeAndID()] = res; }
     void addResources(const Resources& res);
