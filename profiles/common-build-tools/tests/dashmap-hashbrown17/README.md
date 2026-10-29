# DashMap hashbrown compatibility

The shared patch adapts DashMap 6.2.1 to hashbrown 0.17 using its HashTable
API while retaining DashMap's SharedValue and guard semantics. With `raw-api`,
the public shard type changes from RawTable to HashTable; callers using the
old RawTable API must migrate. Ordinary DashMap operations retain their API.

For the regression, add `hashbrown17.rs` as an integration test to the patched
DashMap source and run `cargo test --offline --all-features` with the selected
host SDK and the common prepared Cargo dependencies. The test covers entry,
guard lifetime, key-drop and concurrency behavior. The source test is kept
outside the registry patch because crate preparation requires patched files to
exist in the upstream archive.
