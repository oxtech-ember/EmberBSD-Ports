#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Real native ELF closure, not LLVM acceptance.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
require_relative '../cross/llvm-native'

abort 'Usage: HOST_CXX=/absolute/g++ llvm-native-runtime.rb ABS_NEW_WORK' unless ARGV.length == 1
work = ARGV.fetch(0)
abort 'Use a new absolute work directory' unless work.start_with?('/') && !File.exist?(work) && !File.symlink?(work)
cxx = ENV.fetch('HOST_CXX')
abort 'HOST_CXX must be an absolute executable' unless cxx.start_with?('/') && File.executable?(cxx)
FileUtils.mkdir_p(work)
native = EmberGraphicsLLVMNative
checks = []
check = lambda do |name, &block|
  raise "FAIL: #{name}" unless block.call
  checks << name
  puts "PASS: #{name}"
end
reject = lambda do |name, pattern, &block|
  message = nil
  begin
    block.call
  rescue ArgumentError => error
    message = error.message
  end
  check.call(name) { message && message.match?(pattern) }
end
run = lambda do |name, *command|
  out, err, status = Open3.capture3(*command)
  File.write("#{work}/#{name}.json", JSON.pretty_generate(command: command, stdout: out, stderr: err, exit: status.exitstatus) + "\n")
  raise "#{name} failed: #{err}" unless status.success?
  out
end

check.call('GNU Linux selectors accept ordinary and unknown-vendor spellings') do
  %w[x86_64-linux-gnu x86_64-unknown-linux-gnu aarch64-linux-gnu aarch64-unknown-linux-gnu].all? { |triple| native.platform(triple) == 'linux-gnu' }
end
%w[x86_64--linux-gnu aarch64--linux-gnu x86_64-linux-musl aarch64--netbsd riscv64-linux-gnu].each do |triple|
  reject.call("rejects unsupported native selector #{triple}", /unsupported native LLVM triple/) { native.platform(triple) }
end
check.call('Darwin selector remains available') { native.platform('arm64-apple-darwin25.0.0') == 'darwin' }
triple = native.capture(cxx, '-dumpmachine').strip
compiler = native.compiler(cxx, triple, [])
File.write("#{work}/compiler.json", JSON.pretty_generate(triple: triple, version: native.capture(cxx, '--version'), **compiler) + "\n")
check.call('real GCC16 reports existing native header roots and runtime libraries') do
  !compiler.fetch(:header_roots).empty? && compiler.fetch(:compiler_libraries).length == 2 &&
    compiler.fetch(:compiler_libraries).all? { |path| File.file?(path) }
end
other = triple.start_with?('aarch64-') ? 'x86_64-linux-gnu' : 'aarch64-linux-gnu'
reject.call('rejects a compiler/LLVM architecture mismatch', /architectures differ/) { native.compiler(cxx, other, []) }

original = "#{work}/original"
FileUtils.mkdir_p("#{original}/bin")
source = File.expand_path('llvm-native-runtime.cpp', __dir__)
binary = "#{original}/bin/llvm-config.real"
run.call('compile', cxx, '-std=c++20', '-O2', '-Wall', '-Wextra', '-Werror', '-pthread', source, '-o', binary)
runtime = native.retain(binary, original, triple, compiler.fetch(:compiler_libraries))
File.write("#{original}/runtime.json", JSON.pretty_generate(runtime) + "\n")
trace = native.verify(binary, original, runtime)
File.write("#{work}/original-loader.txt", trace)
check.call('real copied loader resolves the complete native ELF closure inside its payload') do
  native.loaded(trace).values.all? { |path| path.start_with?(original + '/native/lib/') }
end
expected = "PASS: native threads, containers, exceptions and I/O\n"
check.call('real GCC16 native contract executes with the retained loader and runtime') do
  run.call('original-run', "#{original}/#{runtime.fetch('loader')}", '--inhibit-cache', '--library-path', "#{original}/native/lib", binary) == expected
end

sealed = "#{work}/sealed"
FileUtils.mkdir_p("#{sealed}/bin")
FileUtils.cp(binary, "#{sealed}/bin/llvm-config.real")
native.copy(binary, original, sealed, runtime, copied_binary: "#{sealed}/bin/llvm-config.real")
check.call('native seal copies the executable, loader and each GCC/system DSO byte for byte') do
  paths = ['bin/llvm-config.real', *runtime.fetch('files').map { |file| file.fetch('path') }]
  paths.all? { |path| Digest::SHA256.file("#{original}/#{path}").hexdigest == Digest::SHA256.file("#{sealed}/#{path}").hexdigest }
end
File.write("#{sealed}/bin/llvm-config", "#!/bin/sh\nset -eu\nbase=$(CDPATH= cd -- \"$(dirname -- \"$0\")/..\" && pwd -P)\n#{native.launcher(runtime)}\n")
File.chmod(0755, "#{sealed}/bin/llvm-config")
File.rename(original, "#{work}/retained-original")
check.call('sealed native program survives removal of the original helper path') do
  run.call('sealed-run', "#{sealed}/bin/llvm-config") == expected &&
    native.loaded(native.verify("#{sealed}/bin/llvm-config.real", sealed, runtime)).values.all? { |path| path.start_with?(sealed + '/native/lib/') }
end

# Each negative changes only this contract's private copy. Shared native tools
# and the real GCC16 provider are never modified or removed.
library = runtime.fetch('files').find { |file| file.fetch('name') == 'libstdc++.so.6' }
raise 'GCC16 libstdc++ is missing from the real closure' unless library
%w[changed missing symlink].each do |mutation|
  clone = "#{work}/#{mutation}"
  FileUtils.cp_r(sealed, clone)
  path = "#{clone}/#{library.fetch('path')}"
  case mutation
  when 'changed' then File.open(path, 'ab') { |file| file.write('changed runtime') }
  when 'missing' then File.unlink(path)
  when 'symlink'
    File.unlink(path)
    File.symlink(library.fetch('source'), path)
  end
  reject.call("rejects #{mutation} copied GCC runtime before loading", /retained native runtime changed/) { native.verify("#{clone}/bin/llvm-config.real", clone, runtime) }
end
clone = "#{work}/escaped"
FileUtils.cp_r(sealed, clone)
File.rename("#{clone}/native/lib", "#{clone}/outside")
File.symlink('../outside', "#{clone}/native/lib")
reject.call('rejects a native library-directory symlink escape', /escapes the payload/) { native.verify("#{clone}/bin/llvm-config.real", clone, runtime) }

wrong_elf = "#{work}/wrong-machine"
data = File.binread("#{sealed}/bin/llvm-config.real")
data[18, 2] = [native.machine(triple) == 62 ? 183 : 62].pack('v')
File.binwrite(wrong_elf, data)
reject.call('rejects wrong native ELF machine without executing it', /wrong native ELF architecture/) { native.verify(wrong_elf, sealed, runtime) }
reject.call('rejects an unresolved loader dependency', /unresolved native loader entry/) { native.loaded("libmissing.so.1 => not found\n") }
reject.call('rejects duplicate loader entries', /duplicate or unsafe/) { native.loaded("libc.so.6 => /lib/x86_64-linux-gnu/libc.so.6 (0x1)\n" * 2) } if triple.start_with?('x86_64-')
File.write("#{work}/receipt.json", JSON.pretty_generate(scope: 'native GCC16 ELF runtime retention and copy only; no LLVM or target metadata acceptance',
  source_sha256: Digest::SHA256.file(source).hexdigest, binary_sha256: Digest::SHA256.file("#{sealed}/bin/llvm-config.real").hexdigest,
  runtime: runtime, checks: checks) + "\n")
puts "PASS: #{checks.length} native runtime checks. LLVM build/seal and target-query agreement remain unrun."
