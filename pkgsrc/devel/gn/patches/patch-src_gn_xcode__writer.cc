$NetBSD$

Validate Xcode project attributes before constructing the project.
Propagate invalid platform errors through the existing writer Err argument.
Keep platform parsing and GCC diagnostics unchanged.
Origin: EmberBSD (AI-assisted), not submitted upstream.

--- src/gn/xcode_writer.cc.orig
+++ src/gn/xcode_writer.cc
@@ -719,7 +719,8 @@
 class XcodeProject {
  public:
   XcodeProject(const BuildSettings* build_settings,
-               XcodeWriter::Options options);
+               XcodeWriter::Options options,
+               const PBXAttributes& attributes);
   ~XcodeProject();
 
   // Recursively finds "source" files from |builder| and adds them to the
@@ -787,15 +788,14 @@
 };
 
 XcodeProject::XcodeProject(const BuildSettings* build_settings,
-                           XcodeWriter::Options options)
+                           XcodeWriter::Options options,
+                           const PBXAttributes& attributes)
     : build_settings_(build_settings),
       options_(options),
       project_(options.project_name,
                ConfigListFromOptions(options.configurations),
                SourcePathFromBuildSettings(build_settings),
-               ProjectAttributesFromBuildSettings(build_settings,
-                                                  /*node=*/nullptr,
-                                                  /*err=*/nullptr)) {}
+               attributes) {}
 
 XcodeProject::~XcodeProject() = default;
 
@@ -1231,7 +1231,12 @@
                                    const Builder& builder,
                                    Options options,
                                    Err* err) {
-  XcodeProject project(build_settings, options);
+  const PBXAttributes attributes = ProjectAttributesFromBuildSettings(
+      build_settings, /*node=*/nullptr, err);
+  if (err->has_error())
+    return false;
+
+  XcodeProject project(build_settings, options, attributes);
   if (!project.AddSourcesFromBuilder(builder, err))
     return false;
 
