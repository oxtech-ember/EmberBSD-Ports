#!/usr/bin/env ruby
# Build only target std and its acceptance consumers; never install packages.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
require 'rbconfig'
require 'shellwords'

abort 'usage: build.rb HOST_RUST CROSS_TOOLS TARGET_SYSROOT RUST_SOURCE_ARCHIVE NEW_WORK' unless ARGV.size == 5
host, tools, sysroot, archive = ARGV.first(4).map { |p| File.realpath(p) }
work = File.expand_path(ARGV[4])
abort 'new absolute work directory required' unless ARGV[4].start_with?('/') && !File.exist?(work)
parent = File.realpath(File.dirname(work))
abort 'work cannot be inside any input' if [host, tools, sysroot].any? { |p| parent == p || parent.start_with?(p + '/') }
abort 'source SHA256 mismatch' unless Digest::SHA256.file(archive).hexdigest == '6451598a99e77f07571960f6b21d577399d3a30f33e80cbd2e3a4aae6535d265'
rustc = File.join(host, 'bin/rustc')
cargo = File.join(host, 'bin/cargo')
version, status = Open3.capture2e(rustc, '-vV')
abort 'official Rust 1.99 macOS/AArch64 compiler required' unless status.success? &&
  version.lines.first.chomp == 'rustc 1.99.1 (58cf8f9c3 2026-10-13)' &&
  version.include?("commit-hash: 58cf8f9c35b355199727627d07ae34a4e2846d67\n") &&
  version.include?("host: aarch64-apple-darwin\n")
cv, status = Open3.capture2e(cargo, '-V')
abort 'matching cargo 1.99 required' unless status.success? && cv.start_with?('cargo 1.99.1 ')
cc = File.join(tools, 'bin/aarch64--netbsd-gcc')
cxx = File.join(tools, 'bin/aarch64--netbsd-g++')
ar = File.join(tools, 'bin/aarch64--netbsd-ar')
cross_prefix = File.dirname(File.dirname(File.realpath(cc)))
abort 'work cannot be inside the resolved GCC provider' if parent == cross_prefix || parent.start_with?(cross_prefix + '/')
gv, status = Open3.capture2e(cc, '-dumpfullversion')
abort 'accepted GCC 16.2.0 required' unless status.success? && gv.strip == '16.2.0'
crt = File.join(sysroot, 'usr/pkg/gcc16/lib/gcc/aarch64--netbsd/16.2.0')
abort 'target GCC16 CRT missing' unless File.file?(File.join(crt, 'crtbeginS.o'))
space, status = Open3.capture2e('df', '-Pk', parent)
abort 'at least 8 GiB free required' unless status.success? && space.lines.last.split[3].to_i >= 8 * 1024 * 1024
Dir.mkdir(work)
recipe = File.join(work, 'recipe')
FileUtils.mkdir_p(File.join(recipe, 'patches'))
recipe_files = %w[build.rb test-bootstrap-copy.rb runtime.rs consumer.c run-on-target.sh sources.tsv patches/stage0-cross-std.patch]
recipe_files.each { |p| FileUtils.cp(File.join(__dir__, p), File.join(recipe, p)) }
recipe_hashes = recipe_files.to_h { |p| [p, Digest::SHA256.file(File.join(recipe, p)).hexdigest] }
File.write(File.join(work, 'recipe.sha256'), recipe_hashes.map { |p, h| "#{h}  recipe/#{p}\n" }.join)
input_roots = [host, cross_prefix] + %w[usr/include usr/lib libexec usr/pkg/gcc16/lib].map { |p| File.join(sysroot, p) }
snapshot = lambda do
  paths = input_roots.flat_map { |root| Dir.glob(File.join(root, '**/*'), File::FNM_DOTMATCH) }
  paths.select { |p| File.file?(p) }.uniq.sort.to_h { |p| [p, Digest::SHA256.file(p).hexdigest] }
end
input_hashes = snapshot.call
File.write(File.join(work, 'provider-inputs.sha256'), input_hashes.map { |p, h| "#{h}  #{p}\n" }.join)
source = File.join(work, 'source')
FileUtils.mkdir_p([source, File.join(work, 'tmp')])
env = {'TMPDIR' => File.join(work, 'tmp'), 'CARGO_HOME' => File.join(work, 'cargo-home'),
       'CARGO_NET_OFFLINE' => 'true'}
run = lambda do |name, *args, **options|
  File.open(File.join(work, name + '.log'), 'w') do |log|
    abort "#{name} failed; see preserved log" unless system(env, *args, **options, out: log, err: log)
  end
end
run.call('extract', 'tar', '-xf', archive, '--strip-components', '1', '-C', source)
patch = File.join(recipe, 'patches/stage0-cross-std.patch')
run.call('patch', 'patch', '-p1', '-F0', '--batch', '-i', patch, chdir: source)
flags = ["--sysroot=#{sysroot}", "-B#{crt}/", "-L#{sysroot}/usr/pkg/gcc16/lib", '-Wl,-rpath,/usr/pkg/gcc16/lib']
{'netbsd-cc' => cc, 'netbsd-cxx' => cxx}.each do |name, compiler|
  path = File.join(work, name)
  File.write(path, "#!/bin/sh\nexec #{([compiler] + flags).shelljoin} \"$@\"\n")
  File.chmod(0755, path)
end
config = <<~TOML
  change-id = "ignore"
  [build]
  build = "aarch64-apple-darwin"
  host = ["aarch64-apple-darwin"]
  target = ["aarch64-unknown-netbsd"]
  rustc = #{rustc.to_json}
  cargo = #{cargo.to_json}
  local-rebuild = true
  locked-deps = true
  vendor = true
  extended = false
  jobs = 2
  build-dir = #{File.join(work, 'out').to_json}
  [llvm]
  download-ci-llvm = false
  [rust]
  channel = "stable"
  download-rustc = false
  [target.aarch64-unknown-netbsd]
  cc = #{File.join(work, 'netbsd-cc').to_json}
  cxx = #{File.join(work, 'netbsd-cxx').to_json}
  ar = #{ar.to_json}
  linker = #{File.join(work, 'netbsd-cc').to_json}
TOML
File.write(File.join(source, 'bootstrap.toml'), config)
python = ENV.fetch('PYTHON', 'python3') # Existing interpreter for upstream bootstrap.
command = [python, 'x.py', 'build', 'library', '--stage', '0', '--target', 'aarch64-unknown-netbsd', '-j2']
run.call('dry-run', *command, '--dry-run', chdir: source)
plan = File.read(File.join(work, 'dry-run.log'))
abort 'unexpected bootstrap plan' unless plan.include?('Building stage0 library artifacts') &&
  !plan.match?(/Building (?:stage[1-9]|LLVM|LLD|stage0 compiler)/)
run.call('build-std', *command, chdir: source)
stage0 = File.join(work, 'out/aarch64-apple-darwin/stage0-sysroot')
component = File.join(stage0, 'lib/rustlib/aarch64-unknown-netbsd')
%w[std core alloc panic_unwind].each do |name|
  abort "missing #{name} metadata" if Dir.glob(File.join(component, "lib/lib#{name}-*.rmeta")).empty?
end
files = Dir.glob('**/*', base: component).select { |p| File.file?(File.join(component, p)) }.sort
File.write(File.join(work, 'std.sha256'), files.map { |p| "#{Digest::SHA256.file(File.join(component, p)).hexdigest}  #{p}\n" }.join)
run.call('copy-contract', RbConfig.ruby, File.join(recipe, 'test-bootstrap-copy.rb'), source, rustc, File.join(work, 'copy-contract'))
runtime = File.join(work, 'runtime')
Dir.mkdir(runtime)
%w[runtime.rs consumer.c run-on-target.sh].each { |p| FileUtils.cp(File.join(recipe, p), runtime) }
rust_flags = ['--sysroot', stage0, '--target', 'aarch64-unknown-netbsd', '--edition=2024', '-C', 'opt-level=2', '-C', "linker=#{work}/netbsd-cc"]
run.call('link-bin', rustc, *rust_flags, File.join(runtime, 'runtime.rs'), '-o', File.join(runtime, 'rust-runtime'))
run.call('link-dso', rustc, *rust_flags, '--crate-type', 'cdylib', File.join(runtime, 'runtime.rs'), '-o', File.join(runtime, 'librust-runtime.so'))
run.call('link-c', File.join(work, 'netbsd-cc'), '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', '-pthread', File.join(runtime, 'consumer.c'), '-o', File.join(runtime, 'rust-c-consumer'))
run.call('native-link', rustc, '--sysroot', stage0, '--edition=2024', File.join(runtime, 'runtime.rs'), '-o', File.join(work, 'native-control'))
run.call('native-run', File.join(work, 'native-control'))
abort 'input providers changed during build' unless snapshot.call == input_hashes
recipe_hashes.each do |p, h|
  abort "recipe changed during build: #{p}" unless Digest::SHA256.file(File.join(recipe, p)).hexdigest == h &&
    Digest::SHA256.file(File.join(__dir__, p)).hexdigest == h
end
inputs = [archive, rustc, cargo, cc, cxx, ar]
File.write(File.join(work, 'inputs.sha256'), inputs.map { |p| "#{Digest::SHA256.file(p).hexdigest}  #{p}\n" }.join)
File.write(File.join(work, 'compiler.txt'), version + cv + "GCC #{gv}")
puts 'PASS: target std and ELF consumers built; native control/copy contracts pass; target execution is still required'
