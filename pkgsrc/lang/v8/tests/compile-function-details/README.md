# Wrapped-function compilation details regression

`test.inc` is an upstream V8 cctest fixture for the shared wrapped-function
compilation details change. `test-node-cctest.inc` exercises the same public V8
API in a selected Node `EnvironmentTest` build: a cold invalid cache is rejected,
then a warm isolate-cache hit leaves the supplied bytes unread. Both variants
require the V8 source produced by this recipe; the Node case does not establish
target execution.
