#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Real bmake selection and actual Rust metadata import; no Cargo build or VM.
require 'fileutils'
require 'json'
require 'open3'
require 'rbconfig'
require 'shellwords'
abort 'Usage: librsvg-targets.rb HOST_PREFIX CROSS_TOOLS NEW_WORK' unless ARGV.length == 3
host, tools = ARGV.first(2).map { |p| File.realpath(p) }
work = File.expand_path(ARGV[2])
abort 'new absolute work required' unless ARGV[2].start_with?('/') && !File.exist?(work)
FileUtils.mkdir_p(work)
root = File.expand_path('..', __dir__)
recipe = work + '/pkgsrc/graphics/librsvg'
FileUtils.mkdir_p([recipe, work + '/pkgsrc/devel/gobject-introspection', work + '/pkgsrc/mk', work + '/sysroot', work + '/wrappers'])
File.write(work + '/pkgsrc/mk/bsd.prefs.mk', '')
File.write(recipe + '/Makefile', ".include \"cross.mk\"\n")
FileUtils.cp(root + '/recipes/graphics/librsvg/cross.mk', recipe + '/cross.mk')
FileUtils.cp(root + '/recipes/devel/gobject-introspection/cross.mk', work + '/pkgsrc/devel/gobject-introspection/cross.mk')
File.write(work + '/query.json', '{}') # Existence only: this test never runs a GI query.
%w[cc c++].zip(%w[gcc g++]).each { |name, driver| File.symlink(tools + '/bin/x86_64--netbsd-' + driver, work + '/wrappers/' + name) }
base = [ENV.fetch('BMAKE', 'bmake'), '-C', recipe, 'USE_CROSS_COMPILE=yes',
  'OPSYS=NetBSD', 'CROSS_OPSYS=NetBSD', 'CROSS_OS_VERSION=11.0',
  'TOOLBASE=' + host, 'TOOLDIR=' + tools, 'CROSS_DESTDIR=' + work + '/sysroot',
  'WRAPPER_BINDIR=' + work + '/wrappers', 'PREFIX=/usr/pkg', 'BUILDLINK_DIR=' + work + '/buildlink',
  'EMBERBSD_GI_RUBY=' + RbConfig.ruby, 'EMBERBSD_GI_QUERY_CONFIG=' + work + '/query.json',
  'EMBERBSD_CROSS_BUILD_CC=/usr/bin/cc', 'EMBERBSD_CROSS_BUILD_CXX=/usr/bin/c++',
  'GREP=/usr/bin/grep', 'TEST=/bin/test', 'FIND=/usr/bin/find', 'PRINTF=printf']
run = lambda do |name, *args|
  out, status = Open3.capture2e(*base, *args)
  File.write(work + '/' + name + '.log', out)
  abort name + ': ' + out unless status.success?
  out
end
native, status = Open3.capture2(host + '/bin/rustc', '-vV')
abort 'real Rust version query failed' unless status.success?
native_host = native[/^host: (\S+)$/, 1] || abort('real Rust host missing')
{
  'amd64' => ['x86_64', 'x86_64--netbsd', 'x86_64-unknown-netbsd', 'rust-std-x86_64-netbsd'],
  'aarch64' => ['aarch64', 'aarch64--netbsd', 'aarch64-unknown-netbsd', 'rust-std-aarch64-netbsd']
}.each do |target, (arch, triplet, rust, std)|
  args = ['MACHINE_ARCH=' + arch, 'CROSS_MACHINE_ARCH=' + arch, 'MACHINE_GNU_PLATFORM=' + triplet, 'EMBERBSD_CROSS_TARGET=' + target, 'WRKDIR=' + work]
  reason = run.call(target + '-reason', *args, '-V', '${PKG_FAIL_REASON}')
  abort 'supported target rejected: ' + reason unless reason.strip.empty?
  settings = run.call(target + '-settings', *args, '-V', '${TOOL_DEPENDS}', '-V', '${MESON_ARGS}', '-V', '${MESON_BINARY.nm}', '-V', '${MESON_BINARY.strip}', '-V', '${MAKE_ENV}')
  key = rust.upcase.tr('-', '_'); cc_key = rust.tr('-', '_')
  [std + '-1.99.1', '-Dtriplet=' + rust, triplet + '-nm', triplet + '-strip', triplet + '-ar',
   'CARGO_TARGET_' + key + '_LINKER=', 'CC_' + cc_key + '=', 'CXX_' + cc_key + '=', 'AR_' + cc_key + '=',
   'CARGO_TARGET_' + native_host.upcase.tr('-', '_') + '_LINKER=/usr/bin/cc'].each do |expected|
    abort 'wrong target/native provider setting: ' + expected unless settings.include?(expected)
  end
  other_std = target == 'amd64' ? 'rust-std-aarch64-netbsd' : 'rust-std-x86_64-netbsd'
  other_gnu = target == 'amd64' ? 'aarch64--netbsd' : 'x86_64--netbsd'
  abort 'unselected std or GNU provider leaked into target settings' if settings.include?(other_std) || settings.include?(other_gnu)
  [['CROSS_MACHINE_ARCH', arch == 'x86_64' ? 'aarch64' : 'x86_64'], ['MACHINE_GNU_PLATFORM', 'foreign--netbsd'], ['RUST_TARGET', rust == 'x86_64-unknown-netbsd' ? 'aarch64-unknown-netbsd' : 'x86_64-unknown-netbsd']].each do |key_name, foreign|
    rejected = run.call(target + '-mixed-' + key_name, *args, key_name + '=' + foreign, '-V', '${PKG_FAIL_REASON}')
    abort 'mixed provider accepted: ' + key_name if rejected.strip.empty?
  end
end
unknown = run.call('unknown', 'MACHINE_ARCH=riscv64', 'CROSS_MACHINE_ARCH=riscv64', 'MACHINE_GNU_PLATFORM=riscv64--netbsd', '-V', '${PKG_FAIL_REASON}')
abort 'unknown target accepted' if unknown.strip.empty?
common = ['MACHINE_ARCH=x86_64', 'CROSS_MACHINE_ARCH=x86_64', 'MACHINE_GNU_PLATFORM=x86_64--netbsd', 'EMBERBSD_CROSS_TARGET=amd64']
FileUtils.mkdir_p(work + '/positive')
run.call('actual-std-positive', *common, 'WRKDIR=' + work + '/positive', 'emberbsd-librsvg-rust')
abort 'actual compiler did not emit target std metadata' unless File.size?(work + '/positive/target-std-check.rmeta')
FileUtils.mkdir_p([work + '/native-wrappers', work + '/foreign-compiler'])
%w[cc c++].each { |name| File.symlink('/usr/bin/' + name, work + '/native-wrappers/' + name) }
out, status = Open3.capture2e(*base, *common, 'WRAPPER_BINDIR=' + work + '/native-wrappers', 'WRKDIR=' + work + '/foreign-compiler', 'emberbsd-librsvg-rust')
File.write(work + '/actual-foreign-compiler-negative.log', out)
abort 'native compiler accepted as selected target wrapper' if status.success? || File.exist?(work + '/foreign-compiler/target-std-check.rmeta')
# A private fixture changes only rustc's sysroot, using real compiler responses
# and genuine native Darwin std/core bytes. It never rewrites the shared host.
foreign_host = work + '/foreign-host'
FileUtils.mkdir_p([foreign_host + '/bin', foreign_host + '/lib/rustlib/x86_64-unknown-netbsd/lib', work + '/negative'])
File.symlink(host + '/bin/cargo', foreign_host + '/bin/cargo')
File.write(foreign_host + '/bin/rustc', "#!/bin/sh\nexec #{(host + '/bin/rustc').shellescape} --sysroot #{foreign_host.shellescape} \"$@\"\n")
File.chmod(0755, foreign_host + '/bin/rustc')
%w[std core].each do |library|
  files = Dir.glob(host + '/lib/rustlib/' + native_host + '/lib/lib' + library + '-*.rlib')
  abort 'one genuine foreign std/core input required' unless files.length == 1
  FileUtils.cp(files.first, foreign_host + '/lib/rustlib/x86_64-unknown-netbsd/lib')
end
out, status = Open3.capture2e(*base, *common, 'TOOLBASE=' + foreign_host, 'WRKDIR=' + work + '/negative', 'emberbsd-librsvg-rust')
File.write(work + '/actual-foreign-std-negative.log', out)
abort 'foreign std metadata was accepted or not read by rustc' if status.success? || !out.match?(/E0461|E0514|incompatible|couldn.t find crate.*(?:std|core).*expected target/i)
abort 'foreign metadata published a success output' if File.exist?(work + '/negative/target-std-check.rmeta')
FileUtils.mkdir_p(work + '/ambiguous')
std = Dir.glob(foreign_host + '/lib/rustlib/x86_64-unknown-netbsd/lib/libstd-*.rlib').fetch(0)
FileUtils.cp(std, File.dirname(std) + '/libstd-duplicate.rlib')
out, status = Open3.capture2e(*base, *common, 'TOOLBASE=' + foreign_host, 'WRKDIR=' + work + '/ambiguous', 'emberbsd-librsvg-rust')
File.write(work + '/actual-ambiguous-std-negative.log', out)
abort 'ambiguous std was not rejected before metadata import' if status.success? || !out.include?('Missing, ambiguous or linked target std rlib.')
abort 'ambiguous std published a success output' if File.exist?(work + '/ambiguous/target-std-check.rmeta')
puts 'PASS: real bmake selects both canonical target providers and native Rust host linker; mixed/unknown inputs fail'
puts 'PASS: actual official Rust 1.99 imports matching amd64 std metadata; genuine native foreign std is rejected'
puts 'PASS: duplicate genuine std archives fail the early uniqueness guard'
puts 'SCOPE: no Cargo build, target linking, GI execution, target package or VM acceptance'
