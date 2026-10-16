#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Link with the normally installed target data.
require 'digest'
require 'fileutils'
require 'open3'
require 'shellwords'

abort 'usage: rust-target-package.rb HOST_PREFIX CROSS_TOOLS TARGET_SYSROOT NEW_WORK' unless ARGV.size == 4
host, tools, sysroot = ARGV.first(3).map { |p| File.realpath(p) }
work = File.expand_path(ARGV[3])
abort 'new absolute work directory required' unless ARGV[3].start_with?('/') && !File.exist?(work)
parent = File.realpath(File.dirname(work))
cross_provider = File.dirname(File.dirname(File.realpath(tools + '/bin/aarch64--netbsd-gcc')))
abort 'work overlaps providers' if [host, tools, sysroot, cross_provider].any? { |p| parent == p || parent.start_with?(p + '/') }
FileUtils.mkdir_p(work)
env = {'PATH' => host + '/bin:/usr/bin:/bin:/usr/sbin:/sbin',
       'RUSTFLAGS' => nil, 'CARGO_ENCODED_RUSTFLAGS' => nil, 'RUSTC_BOOTSTRAP' => nil,
       'RUSTC_WRAPPER' => nil, 'RUSTC_WORKSPACE_WRAPPER' => nil,
       'DYLD_LIBRARY_PATH' => nil, 'DYLD_FRAMEWORK_PATH' => nil,
       'DYLD_INSERT_LIBRARIES' => nil, 'CARGO_BUILD_TARGET' => nil,
       'CARGO_HOME' => work + '/cargo-home', 'CARGO_NET_OFFLINE' => 'true',
       'CARGO_TARGET_DIR' => work + '/cargo-target', 'CARGO_BUILD_JOBS' => '2',
       'RUSTC' => host + '/bin/rustc'}
run = lambda do |name, *args, **opts|
  output, status = Open3.capture2e(env, *args, **opts)
  File.write(work + '/' + name + '.log', output)
  abort "#{name} failed: #{output}" unless status.success?
  output
end
rustc = host + '/bin/rustc'
pkg_info = host + '/sbin/pkg_info'
pkg = run.call('package', pkg_info, '-e', 'rust-std-aarch64-netbsd-1.99.0{,nb[0-9]*}').strip
abort 'target package is not registered uniquely' unless pkg.match?(/\Arust-std-aarch64-netbsd-1\.99\.0(?:nb[0-9]+)?\z/)
run.call('package-check', host + '/sbin/pkg_admin', 'check', pkg)
component = run.call('target-libdir', rustc, '--target', 'aarch64-unknown-netbsd', '--print', 'target-libdir').strip
abort 'std outside shared host prefix' unless File.realpath(component) == host + '/lib/rustlib/aarch64-unknown-netbsd/lib'
files = Dir.glob(component + '/**/*').select { |p| File.file?(p) }.sort
owned = run.call('package-files', pkg_info, '-qL', pkg).lines.map(&:chomp).select { |p| File.file?(p) }.map { |p| File.realpath(p) }
abort 'empty or unowned target component' unless files.size == 53 && files.all? { |p| owned.include?(File.realpath(p)) }
providers = [rustc, host + '/bin/cargo', host + '/bin/cargo-cbuild', host + '/bin/cargo-cinstall'] + files
hashes = providers.to_h { |p| [p, Digest::SHA256.file(p).hexdigest] }
File.write(work + '/providers.sha256', hashes.map { |p, h| "#{h}  #{p}\n" }.join)
probe = File.expand_path('../../../probes/rust-cross-std', __dir__)
%w[runtime.rs consumer.c run-on-target.sh].each { |p| FileUtils.cp(probe + '/' + p, work + '/' + p) }
cc = tools + '/bin/aarch64--netbsd-gcc'
crt = sysroot + '/usr/pkg/gcc16/lib/gcc/aarch64--netbsd/16.2.0/'
flags = ['--sysroot=' + sysroot, '-B' + crt, '-L' + sysroot + '/usr/pkg/gcc16/lib', '-Wl,-rpath,/usr/pkg/gcc16/lib']
File.write(work + '/netbsd-cc', "#!/bin/sh\nexec #{([cc] + flags).shelljoin} \"$@\"\n")
File.chmod(0755, work + '/netbsd-cc')
rustflags = ['--target', 'aarch64-unknown-netbsd', '--edition=2024', '-C', 'opt-level=2', '-C', 'linker=' + work + '/netbsd-cc']
# No --sysroot override: these consumers must use the registered shared package.
run.call('rust-bin', rustc, *rustflags, work + '/runtime.rs', '-o', work + '/rust-runtime')
run.call('rust-dso', rustc, *rustflags, '--crate-type', 'cdylib', work + '/runtime.rs', '-o', work + '/librust-runtime.so')
run.call('c-consumer', work + '/netbsd-cc', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', '-pthread', work + '/consumer.c', '-o', work + '/rust-c-consumer')
run.call('native-build', rustc, '--edition=2024', work + '/runtime.rs', '-o', work + '/native-control')
run.call('native-run', work + '/native-control')
# A local proc macro and build script must execute on macOS during a target build.
FileUtils.mkdir_p([work + '/cargo/src', work + '/cargo/macros/src'])
File.write(work + '/cargo/Cargo.toml', <<~TOML)
  [package]
  name = "ember_target_std_check"
  version = "0.1.0"
  edition = "2024"
  [dependencies]
  ember_macro = { path = "macros" }
TOML
File.write(work + '/cargo/macros/Cargo.toml', <<~TOML)
  [package]
  name = "ember_macro"
  version = "0.1.0"
  edition = "2024"
  [lib]
  proc-macro = true
TOML
File.write(work + '/cargo/macros/src/lib.rs', <<~RUST)
  use proc_macro::TokenStream;
  #[proc_macro]
  pub fn answer(_: TokenStream) -> TokenStream {
      assert_eq!(std::env::consts::OS, "macos");
      "42usize".parse().unwrap()
  }
RUST
File.write(work + '/cargo/build.rs', <<~RUST)
  fn main() {
      assert_eq!(std::env::var("HOST").unwrap(), "aarch64-apple-darwin");
      assert_eq!(std::env::var("TARGET").unwrap(), "aarch64-unknown-netbsd");
      println!("cargo::rustc-check-cfg=cfg(ember_cross_checked)");
      println!("cargo::rustc-cfg=ember_cross_checked");
  }
RUST
File.write(work + '/cargo/src/main.rs', <<~RUST)
  #[cfg(not(ember_cross_checked))]
  compile_error!("host build script did not run");
  #[cfg(not(target_os = "netbsd"))]
  compile_error!("consumer is not NetBSD");
  fn main() {
      assert_eq!(std::thread::spawn(|| ember_macro::answer!()).join().unwrap(), 42);
      println!("PASS: packaged std with host proc macro and build script");
  }
RUST
env['CARGO_TARGET_AARCH64_UNKNOWN_NETBSD_LINKER'] = work + '/netbsd-cc'
run.call('cargo-cross', host + '/bin/cargo', 'build', '--offline', '--release', '--target', 'aarch64-unknown-netbsd', chdir: work + '/cargo')
FileUtils.cp(work + '/cargo-target/aarch64-unknown-netbsd/release/ember_target_std_check', work + '/rust-cargo-consumer')
hashes.each { |p, h| abort "provider changed: #{p}" unless Digest::SHA256.file(p).hexdigest == h }
puts 'PASS: package ownership/integrity, unchanged shared providers, native TLS/unwind, target bin/cdylib/C and Cargo proc-macro consumers linked; target execution required'
