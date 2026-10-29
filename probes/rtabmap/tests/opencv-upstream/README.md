# Selected upstream OpenCV tests

Build 37 explicit OpenCV 5.0.0 core cases against the installed shared provider.
The cases check matrix values, SVD orthogonality, Eigen conversions, ROI bounds,
sparse storage, empty inputs and rejected operations. They need no external data.
The filter excludes disabled tests and the multi-gigabyte BigData cases.

This adapter compiles nine unchanged upstream translation units. They include
the real TS framework, bundled GoogleTest and two core test files. The installed
OpenCV libraries remain the only OpenCV implementation. The source highgui header
supplies declarations used by TS headers; this subset makes no GUI calls.
No highgui implementation or replacement API is linked.

Use the exact source and build trees of the selected installed provider.
The provider build must export `compile_commands.json`. The adapter reads its
actual `core/src/matrix.cpp` command. It retains the effective ABI, optimization,
warning and private-interface definitions, except the library export marker.
Installed public headers precede the source private-header fallback.
OpenCV 5.0.0 and Eigen 5.0.1 imports must come from the specified prefixes.

```sh
cmake -S probes/rtabmap/tests/opencv-upstream -B /absolute/new-tests -G Ninja \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
  -DOPENCV_SOURCE=/absolute/opencv-source \
  -DOPENCV_BUILD=/absolute/opencv-provider-build \
  -DOPENCV_PREFIX=/absolute/opencv-install \
  -DEIGEN_PREFIX=/absolute/eigen-install
cmake --build /absolute/new-tests --parallel 1
LD_LIBRARY_PATH=/absolute/opencv-install/lib \
  sh probes/rtabmap/tests/opencv-upstream/run.sh \
  /absolute/new-tests/opencv-core-upstream /absolute/new-results
OPENCV_UPSTREAM_MEMCHECK=1 LD_LIBRARY_PATH=/absolute/opencv-install/lib \
  sh probes/rtabmap/tests/opencv-upstream/run.sh \
  /absolute/new-tests/opencv-core-upstream /absolute/new-memcheck-results
```

For a cross build, add a Clang CMake toolchain file like the one
`../../cross-build.sh` writes (Ports `aarch64--netbsd-clang` wrappers).
Use target prefixes and set the executable install RPATH to the target paths.
Execute that binary on EmberBSD with the same runner and selection file.
Keep the upstream license notices beside a redistributed executable.

The runner checks the process status and the actual GoogleTest XML count.
Every selected case must pass without a skip. The fixed seed is 809564;
the framework uses one test thread. Memcheck enables origins, all leak reports
and failure for definite, indirect or possible leaks. Reachable global state
is reported separately. Native checks do not establish target execution.
This selection does not establish the full OpenCV test suite or GUI support.

See [source provenance](PROVENANCE.md). The adapter is [MIT licensed](LICENSE).
