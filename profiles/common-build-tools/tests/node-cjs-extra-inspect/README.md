# Node CJS embedder regression

Build the selected Node work's `node` and `cctest` targets with the shared CJS patch. For the inspector scenario, build its existing `embedtest` target using the adjacent `embedtest.cc` fixture. Run `run.py` with the selected SDK source, host prefix, work, Node source and lock root. The fixture opts in only for its embedding environment; it verifies the actual inspector pause/resume path as well as the default and opt-in CJS cases.

The adjacent `embedtest.cc` derives from Node’s `test/embedding/embedtest.cc` and retains the Node project license.
