#!/usr/bin/env ruby
# Exercise the actual patched bootstrap merge-copy method on a real filesystem.
require 'fileutils'

source, rustc, work = ARGV
abort 'usage: test-bootstrap-copy.rb PATCHED_RUST_SOURCE HOST_RUSTC NEW_WORK' unless ARGV.size == 3
source = File.realpath(source)
rustc = File.realpath(rustc)
work = File.expand_path(work)
abort 'new work directory required' if File.exist?(work)
text = File.read(File.join(source, 'src/bootstrap/src/core/session.rs'))
extract = lambda do |signature|
  start = text.index(signature) or abort "missing #{signature}"
  ending = text.index("\n    }\n", start) or abort "unterminated #{signature}"
  text[start..ending + 6]
end
methods = %w[pub(crate)\ fn\ cp_link_r_excluding pub(crate)\ fn\ cp_link_filtered fn\ cp_link_filtered_recurse].map { |s| extract.call(s) }.join("\n")
FileUtils.mkdir_p(work)
harness = <<'RUST'
use std::fs::{self, DirEntry};
use std::path::{Path, PathBuf};
macro_rules! t { ($e:expr) => { $e.unwrap() }; }
enum FileType { Regular }
struct Config { dry: bool }
impl Config { fn dry_run(&self) -> bool { self.dry } }
struct Build { config: Config }
impl Build {
    fn read_dir(&self, p: &Path) -> Vec<DirEntry> {
        fs::read_dir(p).unwrap().map(Result::unwrap).collect()
    }
    fn create_dir(&self, p: &Path) { fs::create_dir_all(p).unwrap(); }
    fn copy_link(&self, src: &Path, dst: &Path, _: FileType) {
        if dst.exists() { fs::remove_file(dst).unwrap(); }
        fs::hard_link(src, dst).unwrap();
    }
RUST
harness += methods + "\n}\n"
harness += <<'RUST'
fn put(root: &Path, name: &str, data: &str) {
    let path = root.join(name);
    fs::create_dir_all(path.parent().unwrap()).unwrap();
    fs::write(path, data).unwrap();
}
fn seed(root: &Path) {
    put(root, "rustlib/target-a/lib/fresh.rlib", "accepted A");
    put(root, "rustlib/target-b/lib/self-contained/crt.o", "prepared native object");
    put(root, "rustlib/host/lib/preserved.rlib", "host-only output");
}
fn main() {
    let root = PathBuf::from(std::env::args().nth(1).unwrap());
    let src = root.join("input");
    let good = root.join("merge");
    let old = root.join("destructive-control");
    put(&src, "rustlib/host/lib/copied.rlib", "initial host");
    put(&src, "rustlib/target-a/lib/stale.rlib", "stale A");
    put(&src, "rustlib/target-b/lib/stale.rlib", "stale B");
    put(&src, "rustlib/unselected/lib/keep.rlib", "unselected target");
    seed(&good);
    seed(&old);
    let b = Build { config: Config { dry: false } };
    let skip = [src.join("rustlib/target-a"), src.join("rustlib/target-b")];
    b.cp_link_r_excluding(&src, &good, &skip);
    assert_eq!(fs::read_to_string(good.join("rustlib/target-a/lib/fresh.rlib")).unwrap(), "accepted A");
    assert_eq!(fs::read_to_string(good.join("rustlib/target-b/lib/self-contained/crt.o")).unwrap(), "prepared native object");
    assert_eq!(fs::read_to_string(good.join("rustlib/host/lib/preserved.rlib")).unwrap(), "host-only output");
    assert_eq!(fs::read_to_string(good.join("rustlib/host/lib/copied.rlib")).unwrap(), "initial host");
    assert_eq!(fs::read_to_string(good.join("rustlib/unselected/lib/keep.rlib")).unwrap(), "unselected target");
    for target in ["target-a", "target-b"] {
        assert!(!good.join(format!("rustlib/{target}/lib/stale.rlib")).exists());
        assert!(src.join(format!("rustlib/{target}/lib/stale.rlib")).exists());
    }
    // The initially chosen existing helper must reproduce the review defect.
    b.cp_link_filtered(&src, &old, &|p| {
        !p.starts_with("rustlib/target-a") && !p.starts_with("rustlib/target-b")
    });
    assert!(!old.join("rustlib/target-a/lib/fresh.rlib").exists());
    assert!(!old.join("rustlib/target-b/lib/self-contained/crt.o").exists());
    assert!(!old.join("rustlib/host/lib/preserved.rlib").exists());
    let dry = Build { config: Config { dry: true } };
    dry.cp_link_r_excluding(&src, &root.join("must-not-exist"), &skip);
    assert!(!root.join("must-not-exist").exists());
    println!("PASS: actual bootstrap merge preserves targets/native objects/host, excludes stale components, honors dry-run; destructive control reproduced");
}
RUST
File.write(File.join(work, 'copy.rs'), harness)
abort 'host compile failed' unless system(rustc, '--edition=2024', File.join(work, 'copy.rs'), '-o', File.join(work, 'copy'))
abort 'copy contract failed' unless system(File.join(work, 'copy'), work)
