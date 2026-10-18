#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
# Exercise the installed shared Rust/cargo-c providers through a real C ABI.
require 'digest'
require 'fileutils'
require 'open3'
require 'shellwords'

abort 'usage: cargo-c.rb HOST_PREFIX NEW_WORK' unless ARGV.size == 2
host = File.realpath(ARGV[0])
work = File.expand_path(ARGV[1])
abort 'new absolute work directory required' unless ARGV[1].start_with?('/') && !File.exist?(work)
parent = File.realpath(File.dirname(work))
abort 'work overlaps the provider' if parent == host || parent.start_with?(host + '/')
FileUtils.mkdir_p(work + '/src')
File.write(work + '/Cargo.toml', <<~TOML)
  [package]
  name = "ember_cargo_check"
  version = "0.1.0"
  edition = "2024"
  [features]
  capi = []
TOML
File.write(work + '/cbindgen.toml', "language = \"C\"\ninclude_guard = \"EMBER_CARGO_CHECK_H\"\n")
File.write(work + '/src/lib.rs', <<~RUST)
  #[unsafe(no_mangle)]
  pub extern "C" fn ember_answer(value: i32) -> i32 { value + 42 }
  #[test]
  fn answer() { assert_eq!(ember_answer(1), 43); }
RUST
env = {'PATH' => host + '/bin:/usr/bin:/bin:/usr/sbin:/sbin',
       'CARGO_HOME' => work + '/cargo-home', 'CARGO_BUILD_JOBS' => '2',
       'RUSTC' => host + '/bin/rustc', 'RUSTFLAGS' => nil,
       'CARGO_TARGET_DIR' => work + '/target', 'CARGO_BUILD_TARGET' => nil,
       'DYLD_LIBRARY_PATH' => nil, 'DYLD_FRAMEWORK_PATH' => nil,
       'DYLD_INSERT_LIBRARIES' => nil, 'PKG_CONFIG_PATH' => nil,
       'PKG_CONFIG_LIBDIR' => work + '/installed/lib/pkgconfig', 'PKG_CONFIG_SYSROOT_DIR' => nil}
run = lambda do |name, *args|
  output, status = Open3.capture2e(env, *args, chdir: work)
  File.write(work + '/' + name + '.log', output)
  abort "#{name} failed: #{output}" unless status.success?
  output
end
providers = %w[rustc cargo cargo-cbuild cargo-ctest cargo-cinstall].to_h do |name|
  path = host + '/bin/' + name
  [path, Digest::SHA256.file(path).hexdigest]
end
version = run.call('rustc-version', host + '/bin/rustc', '-vV')
abort 'Rust 1.99 required' unless version.include?("release: 1.99.1\n")
version = run.call('cargo-c-version', host + '/bin/cargo-cbuild', '--version')
abort 'cargo-c 0.10.25 required' unless version.match?(/\b0\.10\.25\b/)
run.call('cbuild', host + '/bin/cargo', 'cbuild', '--offline', '--release', '--prefix', work + '/installed')
tests = run.call('ctest', host + '/bin/cargo', 'ctest', '--offline', '--release')
abort 'Rust unit test did not execute' unless tests.include?('test answer ... ok') && tests.include?('1 passed; 0 failed')
run.call('cinstall', host + '/bin/cargo', 'cinstall', '--offline', '--release', '--prefix', work + '/installed', '--libdir', work + '/installed/lib')
pc = Dir.glob(work + '/installed/lib/pkgconfig/*.pc')
abort 'expected one generated pkg-config record' unless pc.size == 1
name = File.basename(pc.first, '.pc')
flags = Shellwords.split(run.call('pkg-config', host + '/bin/pkg-config', '--cflags', '--libs', name))
File.write(work + '/consumer.c', "#include <ember_cargo_check.h>\nint main(void) { return ember_answer(5) != 47; }\n")
run.call('c-link', 'cc', work + '/consumer.c', *flags, '-o', work + '/consumer')
run.call('c-runtime', work + '/consumer')
imports = run.call('c-load-commands', 'otool', '-L', work + '/consumer').lines.drop(1).map { |line| line.split(' (compatibility version', 2).first.strip }
libraries = imports.grep(/\/libember_cargo_check[^\/]*\.dylib\z/)
installed_lib = File.realpath(work + '/installed/lib') + '/'
abort 'C consumer must import the installed library' unless libraries.size == 1 &&
  libraries.first.start_with?(work + '/installed/lib/') &&
  File.realpath(libraries.first).start_with?(installed_lib)
providers.each { |path, hash| abort "provider changed: #{path}" unless Digest::SHA256.file(path).hexdigest == hash }
File.write(work + '/providers.sha256', providers.map { |path, hash| "#{hash}  #{path}\n" }.join)
puts 'PASS: installed Rust/cargo-c, offline C API/header/pkg-config generation, Rust unit test, installed C linkage/runtime and unchanged providers'
