# Strict GIR lookup regression

Run `python3 strict-gir.py CPPGIR IGNORE_DIR TARGET_GIR_DIR HOST_GIR_DIR`
with the selected native generator and the target and host GIR data directories.
The test checks target and generated top-level metadata as well as rejection of
host XDG and working-directory fallbacks for missing target dependencies.

The CMake consumer compiles against the selected target `CppGir::gi` and GIO.
Set `GENERATED_GIR_DIR` to generated target GIR headers and run its executable
on the target; it checks a GFile path round trip.
