# CppGir sibling scope regression

Configure this fixture with the selected CMake and `cppgir_DIR` pointing to the
common target package's `lib/cmake/cppgir`. Without `TEST_GLOBAL`, generation
must fail because the sibling cannot see the imported `CppGir::gi` target.
Set `-DTEST_GLOBAL=ON` in a separate build directory: configure and generate
must succeed. The fixture does not compile or execute target code.
