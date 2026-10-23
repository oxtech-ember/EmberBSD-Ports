# CMake Xcode header portability

CMake 4.4.4 uses `LSOpenCFURLRef` to open a generated Xcode project.
Its ApplicationServices umbrella also imports unrelated Apple Blocks headers.
GCC16 does not support those declarations. The shared recipe includes the
LaunchServices `LSOpen.h` subframework header directly. The existing platform
guards, framework link flags and complete `Open()` implementation stay intact.
The adaptation is AI-assisted EmberBSD work, not submitted upstream.

Run the check with an actual native GCC16 compilation entry for
`cmGlobalXCodeGenerator.cxx`. Use the post-wrapper driver and arguments.
The output directory must be new.

```sh
python3 -B check.py --sdk-source /absolute/sdk \
  --compile-commands /absolute/one-entry.json \
  --baseline /absolute/upstream/cmGlobalXCodeGenerator.cxx \
  --candidate /absolute/patched/cmGlobalXCodeGenerator.cxx \
  --cxx /absolute/g++-16 --output /absolute/new-output \
  --lock-root /absolute/locks --read-root /absolute/native-prefix \
  --read-root /absolute/configured-cmake-source
```

The original complete translation unit must fail in the unrelated SDK headers.
The patched unit must compile with the same flags. Its Mach-O object must still
reference `LSOpenCFURLRef`. The source comparison rejects any other code change,
including removal of the generator or its project-opening implementation.
This check does not open a GUI, execute generated projects, run the full CMake
suite, or establish memory-safety or old-SDK acceptance.
