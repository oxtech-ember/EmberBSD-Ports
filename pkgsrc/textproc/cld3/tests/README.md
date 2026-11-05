# CLD3 consumer checks

Configure this directory with the selected target CMake toolchain and installed
CLD3 package. Set CLD3_UPSTREAM_SOURCE to the corresponding CLD3 source tree
to also build the unchanged upstream feature, script-span, mixed-language and
prediction checks. Run target executables on the target as separate tests.

With the upstream 3.0.13 model, the full prediction test classifies the bs and
id fixtures as hr and ms respectively on both the native and target builds;
the independent mixed-language, feature and script-span tests pass.
