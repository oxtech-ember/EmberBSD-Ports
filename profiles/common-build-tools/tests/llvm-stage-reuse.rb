#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Fixture contracts, not LLVM package acceptance.
require 'fileutils'
require 'json'
require 'digest'
require 'open3'
require 'rbconfig'
require_relative '../recipes/lang/llvm/files/reuse-package-stage'

abort 'Usage: llvm-stage-reuse.rb CMAKE PERL NEW_WORK' unless ARGV.size == 3
cmake, perl = ARGV.first(2).map { |p| File.realpath(p) }
work = File.expand_path(ARGV.last)
abort 'new absolute work directory required' unless ARGV.last.start_with?('/') && !File.exist?(work)
FileUtils.mkdir_p(work)
source = work + '/source'; build = source + '/build'; recipe = work + '/recipe'; sdk = work + '/sdk-recipe'
[source, build, recipe + '/files', sdk, work + '/bin', work + '/lists'].each { |p| FileUtils.mkdir_p(p) }
FileUtils.cp(File.expand_path('../recipes/lang/llvm/files/select-package-stage.pl', __dir__), recipe + '/files/')
File.write(recipe + '/patch', 'prepared patch'); File.write(sdk + '/PLIST', 'declared SDK')
File.write(work + '/target-abi.h', 'target ABI fixture'); File.write(work + '/bin/gcc', 'GCC16 fixture'); File.write(work + '/bin/tblgen', 'LLVM23 fixture')
File.write(source + '/empty.dat', ''); File.write(source + '/runtime.dat', "runtime fixture\n"); File.write(source + '/license', "license fixture\n")
File.write(build + '/object.dat', "SDK object fixture\n")
File.write(source + '/CMakeLists.txt', <<~CMAKE)
  cmake_minimum_required(VERSION 3.20)
  project(LLVMReuseFixture NONE)
  install(FILES "${CMAKE_CURRENT_SOURCE_DIR}/runtime.dat" DESTINATION lib RENAME libLLVM.so.23.1)
  install(FILES "${CMAKE_CURRENT_SOURCE_DIR}/empty.dat" DESTINATION include/llvm/IR RENAME Empty.h)
  install(FILES "${CMAKE_CURRENT_SOURCE_DIR}/license" DESTINATION include/llvm/Support RENAME LICENSE.TXT)
  install(FILES "${CMAKE_CURRENT_BINARY_DIR}/object.dat" DESTINATION include/llvm/IR RENAME Module.h)
CMAKE
log = File.open(work + '/commands.log', 'w')
def run(log, *args)
  raise "command failed: #{args.first}" unless system(*args, out: log, err: log)
end
run(log, cmake, '-S', source, '-B', build)
wrapper = work + '/bin/cmake'
File.write(wrapper, <<~WRAPPER)
  #!#{RbConfig.ruby}
  require 'fileutils'
  require 'json'
  File.write(#{(work + '/last-install-args.json').inspect}, JSON.generate(ARGV))
  File.open(#{(work + '/install-invocations.log').inspect}, 'a') { |log| log.puts(ENV.fetch('DESTDIR')) }
  object = #{(build + '/object.dat').inspect}
  original = File.binread(object)
  mode = ENV['LLVM_REUSE_TEST_MUTATE']
  begin
    File.binwrite(object, 'temporary wrong SDK bytes') if mode == 'aba'
    ok = system(#{cmake.inspect}, *ARGV)
    if mode == 'missing'
      File.unlink(ENV.fetch('DESTDIR') + '/usr/pkg/include/llvm/IR/Module.h')
    elsif mode == 'outside'
      File.write(ENV.fetch('DESTDIR') + '/outside-prefix', 'unexpected output')
    elsif mode == 'after'
      File.binwrite(object, 'changed after installation')
    end
    exit(ok ? 0 : 1)
  ensure
    File.binwrite(object, original) if mode == 'aba'
  end
WRAPPER
File.chmod(0o755, wrapper)
reference = work + '/reference'; FileUtils.mkdir_p(reference)
run(log, {'DESTDIR' => reference}, wrapper, '--install', build, '--prefix', '/usr/pkg', '--strip')
stage = reference + '/usr/pkg'
runtime = %w[lib/libLLVM.so.23.1 include/llvm/Support/LICENSE.TXT]
devel = %w[include/llvm/IR/Module.h include/llvm/IR/Empty.h]
lists = {'full' => runtime + devel, 'runtime' => runtime, 'devel' => devel}.to_h do |kind, paths|
  p = work + '/lists/' + kind; File.write(p, paths.join("\n") + "\n"); [kind, p]
end
pack = work + '/archive-input'; FileUtils.mkdir_p(pack)
contents = "@cwd /usr/pkg\n@name llvm-23.1.3nb1\n"
runtime.each { |p| contents += p + "\n@comment MD5:" + Digest::MD5.file(stage + '/' + p).hexdigest + "\n" }
File.write(pack + '/+CONTENTS', contents)
File.write(pack + '/+BUILD_INFO', "OPSYS=NetBSD\nOS_VERSION=11.0\nMACHINE_ARCH=aarch64\nOBJECT_FMT=ELF\n")
archive = work + '/llvm-23.1.3nb1.tgz'
run(log, '/usr/bin/tar', '-czf', archive, '-C', pack, '+CONTENTS', '+BUILD_INFO')
value = {'schema' => 1, 'version' => '23.1.3',
         'target' => {'opsys' => 'NetBSD', 'version' => '11.0', 'arch' => 'aarch64', 'triple' => 'aarch64--netbsd'},
         'source' => source, 'build' => build, 'recipe' => recipe, 'sdk_recipe' => sdk,
         'install_strip' => true, 'flags' => {'CXXFLAGS' => '-O2', 'CMAKE_CONFIGURE_ARGS' => '-DCMAKE_SYSTEM_NAME=NetBSD'},
         'cmake' => wrapper, 'perl' => perl, 'tar' => '/usr/bin/tar', 'manifests' => lists,
         'files' => {'compiler' => [work + '/bin/gcc'], 'native_tools' => [wrapper, cmake, perl, '/usr/bin/tar', work + '/bin/tblgen'], 'patches' => [recipe + '/patch'], 'target_abi' => [work + '/target-abi.h']},
         'runtime' => {'archive' => archive, 'sha256' => Digest::SHA256.file(archive).hexdigest}}
config = work + '/inputs.json'; File.write(config, JSON.pretty_generate(value))
receipt = work + '/receipt.json'; reference_dest = work + '/captured-reference'; Dir.mkdir(reference_dest)
LLVMStageReuse.record(config, reference_dest, receipt)
receipt_hash = Digest::SHA256.file(receipt).hexdigest
checks = []
def refused(checks, label, expected)
  begin
    yield
  rescue StandardError => e
    raise "#{label}: wrong failure: #{e.message}" unless e.message.include?(expected)
    checks << label
    return
  end
  raise "#{label}: invalid input accepted"
end
before = LLVMStageReuse.snapshot(value)
dest = work + '/valid'; Dir.mkdir(dest)
LLVMStageReuse.install(config, receipt, receipt_hash, dest)
raise 'CMake lost the recorded strip mode' unless JSON.parse(File.read(work + '/last-install-args.json')).include?('--strip')
raise 'SDK changed original objects' unless LLVMStageReuse.snapshot(value) == before
checks << 'valid CMake install preserves original source and objects'
raise 'empty installed file changed' unless File.zero?(dest + '/usr/pkg/include/llvm/IR/Empty.h')
checks << 'valid empty installed file'
%w[recipe sdk_recipe].each do |kind|
  destination = value.fetch(kind) + '/private-stage'; Dir.mkdir(destination)
  invocations = File.binread(work + '/install-invocations.log')
  refused(checks, kind + ' destination overlap', 'overlaps LLVM inputs') do
    LLVMStageReuse.install(config, receipt, receipt_hash, destination)
  end
  raise 'CMake ran for overlapping destination' unless File.binread(work + '/install-invocations.log') == invocations && Dir.children(destination).empty?
end
%w[source build recipe sdk_recipe].each do |kind|
  output = value.fetch(kind) + '/rejected-receipt.json'
  destination = work + '/record-overlap-' + kind; Dir.mkdir(destination)
  invocations = File.binread(work + '/install-invocations.log')
  refused(checks, kind + ' receipt overlap', 'Receipt overlaps LLVM inputs') do
    LLVMStageReuse.record(config, destination, output)
  end
  raise 'overlapping receipt or stage was written' unless !File.exist?(output) && Dir.children(destination).empty? && File.binread(work + '/install-invocations.log') == invocations
end

%w[source patch compiler native-tool object normalized-plist target-ABI-header].zip([
  source + '/runtime.dat', recipe + '/patch', work + '/bin/gcc', work + '/bin/tblgen', build + '/object.dat', lists.fetch('full'), work + '/target-abi.h'
]).each do |label, path|
  bytes = File.binread(path); File.binwrite(path, bytes + 'changed')
  refused(checks, label + ' drift', 'drift') { LLVMStageReuse.verify(config, receipt, receipt_hash) }
  File.binwrite(path, bytes)
end
[build + '/object.dat', work + '/bin/gcc'].each do |path|
  mode = File.stat(path).mode & 0o7777; File.chmod(mode ^ 0o100, path)
  refused(checks, File.basename(path) + ' mode drift', 'drift') { LLVMStageReuse.verify(config, receipt, receipt_hash) }
  File.chmod(mode, path)
end
changed = Marshal.load(Marshal.dump(value)); changed['flags']['CXXFLAGS'] = '-O0'
File.write(config, JSON.pretty_generate(changed))
refused(checks, 'flag drift', 'contract differs') { LLVMStageReuse.verify(config, receipt, receipt_hash) }
changed['target']['triple'] = 'x86_64--netbsd'; File.write(config, JSON.pretty_generate(changed))
refused(checks, 'ABI drift', 'target ABI') { LLVMStageReuse.verify(config, receipt, receipt_hash) }
changed = Marshal.load(Marshal.dump(value)); changed['install_strip'] = false
File.write(config, JSON.pretty_generate(changed))
refused(checks, 'install strip mode drift', 'contract differs') { LLVMStageReuse.verify(config, receipt, receipt_hash) }
File.write(config, JSON.pretty_generate(value))
bytes = File.binread(receipt); File.binwrite(receipt, bytes + ' ')
refused(checks, 'receipt drift', 'receipt drift') { LLVMStageReuse.verify(config, receipt, receipt_hash) }
File.binwrite(receipt, bytes)
Dir.mkdir(work + '/incomplete')
ENV['LLVM_REUSE_TEST_MUTATE'] = 'missing'
begin
  refused(checks, 'incomplete full stage', 'Command failed') { LLVMStageReuse.record(config, work + '/incomplete', work + '/invalid-receipt.json') }
ensure
  ENV.delete('LLVM_REUSE_TEST_MUTATE')
end
raise 'invalid receipt published' if File.exist?(work + '/invalid-receipt.json')
%w[aba missing after outside].each do |mode|
  dest = work + '/install-' + mode; Dir.mkdir(dest)
  object = File.binread(build + '/object.dat')
  ENV['LLVM_REUSE_TEST_MUTATE'] = mode
  expected = {'after' => 'drift', 'outside' => 'outside the target prefix'}.fetch(mode, 'Installed LLVM stage differs')
  refused(checks, mode + ' during install', expected) { LLVMStageReuse.install(config, receipt, receipt_hash, dest) }
  ENV.delete('LLVM_REUSE_TEST_MUTATE')
  File.binwrite(build + '/object.dat', object)
end
object = File.binread(build + '/object.dat')
elf = "\0".b * 64
elf[0, 4] = "\x7fELF".b
elf.setbyte(4, 2) # ELFCLASS64
elf.setbyte(5, 1) # ELFDATA2LSB
elf.setbyte(6, 1) # EV_CURRENT
elf[16, 2] = [3].pack('v') # ET_DYN
elf[18, 2] = [183].pack('v') # EM_AARCH64
raise 'invalid positive ELF fixture' unless elf.bytesize == 64 && elf[18, 2].unpack1('v') == 183
File.binwrite(build + '/object.dat', elf)
destination = work + '/valid-elf'; Dir.mkdir(destination)
LLVMStageReuse.record(config, destination, work + '/valid-elf-receipt.json')
checks << 'matching AArch64 ELF header'
elf[18, 2] = [62].pack('v') # EM_X86_64; this is the only changed field.
raise 'invalid negative ELF fixture' unless elf.bytesize == 64 && elf[18, 2].unpack1('v') == 62
{'wrong-elf' => [elf, 'Wrong staged ELF ABI'],
 'host-macho' => [["cafebabf"].pack('H*') + ("\0".b * 16), 'Host Mach-O']}.each do |label, (bytes, message)|
  File.binwrite(build + '/object.dat', bytes); destination = work + '/' + label; Dir.mkdir(destination)
  refused(checks, label + ' reference', message) { LLVMStageReuse.record(config, destination, work + '/' + label + '-receipt.json') }
  File.binwrite(build + '/object.dat', object)
end

LLVMStageReuse.verify(config, receipt, receipt_hash)
File.write(work + '/results.json', JSON.pretty_generate({'scope' => 'CMake installation and integrity fixtures only; no LLVM package, compiler or hardware acceptance.', 'checks' => checks}) + "\n")
puts "PASS: #{checks.size} LLVM stage reuse fixture contracts"
