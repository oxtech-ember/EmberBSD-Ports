#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Actual pkgsrc queries; no LLVM compilation.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
require 'rbconfig'
require_relative '../recipes/lang/llvm/files/prepare-reuse-inputs'

abort 'Usage: llvm-reuse-adapter.rb PKGSRC MAKECONF BMAKE NEW_WORK' unless ARGV.size == 4
pkgsrc, makeconf, bmake = ARGV.first(3).map { |path| File.realpath(path) }
work = File.expand_path(ARGV.last)
abort 'new absolute work required' unless ARGV.last.start_with?('/') && !File.exist?(work)
FileUtils.mkdir_p(work + '/pkgsrc/lang')
tree = work + '/pkgsrc'; profile = File.expand_path('..', __dir__)
Dir.children(pkgsrc).reject { |name| name.start_with?('.') || name == 'lang' }.each { |name| File.symlink(pkgsrc + '/' + name, tree + '/' + name) }
Dir.children(pkgsrc + '/lang').reject { |name| %w[llvm llvm-devel].include?(name) }.each { |name| File.symlink(pkgsrc + '/lang/' + name, tree + '/lang/' + name) }
%w[llvm llvm-devel].each { |name| FileUtils.cp_r(profile + '/recipes/lang/' + name, tree + '/lang/' + name) }
common = work + '/common'; source = common + '/llvm-project-23.1.3.src/llvm'; build = source + '/cmake-pkgsrc-build'
FileUtils.mkdir_p(build)
File.write(common + '/.build_makevars.mk', "_MAKEVARS_MK= defined\nCFLAGS+= -DSTALE_CACHE=1\n")
env = {'MAKECONF' => makeconf}
query = lambda do |role, *args|
  fields = %w[TOOLDIR MACHINE_GNU_PLATFORM MACHINE_ARCH OPSYS OS_VERSION CMAKE]
  out, error, status = Open3.capture3(env, bmake, '-C', tree + '/lang/' + role, '_PKGSRC_BARRIER=yes', '_MAKEVARS_MK=defined', 'WRKDIR=' + common, *args, *fields.flat_map { |key| ['-V', '${' + key + '}'] })
  abort error unless status.success?
  fields.zip(out.lines.map(&:chomp)).to_h
end
row = query.call('llvm')
File.write(work + '/target-abi.fixture', 'Explicit metadata fixture, not target ABI acceptance')
File.write(source + '/runtime.dat', 'runtime data fixture')
File.write(source + '/license.dat', 'license data fixture')
File.write(build + '/object.dat', 'SDK data fixture')
File.write(source + '/CMakeLists.txt', <<~CMAKE)
  cmake_minimum_required(VERSION 3.20)
  project(LLVMAdapterFixture NONE)
  install(FILES "${CMAKE_CURRENT_SOURCE_DIR}/runtime.dat" DESTINATION lib RENAME libLLVM.so.23.1)
  install(FILES "${CMAKE_CURRENT_SOURCE_DIR}/license.dat" DESTINATION include/llvm/Support RENAME LICENSE.TXT)
  install(FILES "${CMAKE_CURRENT_BINARY_DIR}/object.dat" DESTINATION include/llvm/IR RENAME Module.h)
CMAKE
File.open(work + '/configure-fixture.log', 'w') { |log| raise 'CMake fixture configure failed' unless system(row.fetch('CMAKE'), '-S', source, '-B', build, out: log, err: log) }
runtime_paths = {'lib/libLLVM.so.23.1' => source + '/runtime.dat', 'include/llvm/Support/LICENSE.TXT' => source + '/license.dat'}
lists = {'runtime' => runtime_paths.keys, 'devel' => ['include/llvm/IR/Module.h'], 'full' => runtime_paths.keys + ['include/llvm/IR/Module.h']}
lists.each { |name, paths| File.write(work + '/' + name + '.plist', paths.join("\n") + "\n") }
FileUtils.mkdir_p(work + '/package-fixture')
File.write(work + '/package-fixture/+CONTENTS', "@cwd /usr/pkg\n@name llvm-23.1.3nb1\n" + runtime_paths.map { |name, path| name + "\n@comment MD5:" + Digest::MD5.file(path).hexdigest + "\n" }.join)
File.write(work + '/package-fixture/+BUILD_INFO', "OPSYS=NetBSD\nOS_VERSION=11.0\nMACHINE_ARCH=" + row.fetch('MACHINE_ARCH') + "\nOBJECT_FMT=ELF\n")
raise 'archive fixture failed' unless system('/usr/bin/tar', '-czf', work + '/runtime.fixture', '-C', work + '/package-fixture', '+CONTENTS', '+BUILD_INFO')
value = {'schema' => 1, 'version' => '23.1.3', 'runtime_work' => common,
 'target' => {'opsys' => row.fetch('OPSYS'), 'version' => row.fetch('OS_VERSION'), 'arch' => row.fetch('MACHINE_ARCH'), 'triple' => row.fetch('MACHINE_GNU_PLATFORM')},
 'source' => source, 'build' => build, 'recipe' => tree + '/lang/llvm', 'sdk_recipe' => tree + '/lang/llvm-devel',
 'flags' => {'obsolete' => 'must not be copied'}, 'install_strip' => true,
 'cmake' => '/usr/bin/true', 'perl' => '/usr/bin/true', 'tar' => '/usr/bin/tar',
 'files' => {'compiler' => %w[gcc g++ strip].map { |name| row.fetch('TOOLDIR') + '/bin/' + row.fetch('MACHINE_GNU_PLATFORM') + '-' + name },
             'native_tools' => ['/usr/bin/tar'], 'patches' => Dir.glob(tree + '/lang/llvm/patches/patch-*'), 'target_abi' => [work + '/target-abi.fixture']},
 'runtime' => {'archive' => work + '/runtime.fixture', 'sha256' => Digest::SHA256.file(work + '/runtime.fixture').hexdigest},
 'manifests' => %w[full runtime devel].to_h { |name| [name, work + '/' + name + '.plist'] }}
template = work + '/template.json'; File.write(template, JSON.pretty_generate(value))
checks = []
collect = lambda do |role, label, *overrides|
  outer = work + '/' + label; FileUtils.mkdir_p(outer)
  out, error, status = Open3.capture3(env, bmake, '-C', tree + '/lang/' + role, '_PKGSRC_BARRIER=yes', 'WRKDIR=' + outer,
    'EMBERBSD_LLVM_REUSE_INPUTS=' + template, 'EMBERBSD_LLVM_REUSE_RUBY=' + RbConfig.ruby, *overrides, 'llvm-reuse-inputs')
  File.write(work + '/' + label + '.log', out + error)
  raise label + ': ' + out + error unless status.success?
  JSON.parse(File.read(outer + '/.llvm-reuse-inputs.json'))
end
runtime = collect.call('llvm', 'runtime')
sdk = collect.call('llvm-devel', 'sdk')
raise 'current role inputs differ' unless runtime == sdk
raise 'template flags were reused' if sdk.fetch('flags').key?('obsolete')
checks << 'current uncached runtime/SDK inputs are identical at the shared root'
checks << 'obsolete template flags are replaced by current pkgsrc inputs'
raise 'stale phase cache affected current flags' if sdk.fetch('flags').fetch('CFLAGS').include?('STALE_CACHE')
checks << 'current query ignores a deliberately stale phase cache'
query_receipt = work + '/query-receipt.fixture.json'
File.write(query_receipt, JSON.pretty_generate({'schema' => 1, 'context' => runtime, 'inputs' => LLVMStageReuse.snapshot(runtime), 'stage' => {}}))
query_hash = Digest::SHA256.file(query_receipt).hexdigest
reject_contract = lambda do |label|
  begin
    LLVMStageReuse.verify(work + '/' + label + '/.llvm-reuse-inputs.json', query_receipt, query_hash)
  rescue StandardError => error
    raise unless error.message.include?('contract differs')
    next
  end
  raise 'changed current input contract accepted'
end
sdk_path = work + '/sdk'
flag = '-DUSER_PATH="' + sdk_path + '"'
changed = collect.call('llvm-devel', 'literal-flag', 'CFLAGS=' + flag)
raise 'literal command flag lost or rewritten' unless changed.fetch('flags').fetch('CFLAGS').include?(flag) && changed.fetch('flags') != runtime.fetch('flags')
reject_contract.call('literal-flag')
checks << 'literal SDK path inside command-line CFLAGS is preserved and refused'
env_value = 'USER_VALUE=' + sdk_path
changed = collect.call('llvm-devel', 'literal-env', 'CONFIGURE_ENV=' + env_value)
raise 'literal environment lost or rewritten' unless changed.fetch('flags').fetch('CONFIGURE_ENV') == env_value && changed.fetch('flags') != runtime.fetch('flags')
reject_contract.call('literal-env')
checks << 'literal SDK path inside command-line CONFIGURE_ENV is preserved and refused'
changed = collect.call('llvm-devel', 'native-tool', 'EMBERBSD_BUILD_CMAKE=/usr/bin/true') rescue nil
raise 'invalid native tool accepted' if changed
checks << 'invalid current native tool is refused'
fields = %w[NO_BUILD NO_CONFIGURE WRKSRC PKG_FAIL_REASON]
receipt = work + '/receipt.fixture'; File.write(receipt, 'not an accepted receipt')
base = [bmake, '-C', tree + '/lang/llvm-devel', '_PKGSRC_BARRIER=yes', 'WRKDIR=' + work + '/reuse-sdk', 'EMBERBSD_LLVM_REUSE_INPUTS=' + template, 'EMBERBSD_LLVM_REUSE_RUBY=' + RbConfig.ruby, 'EMBERBSD_LLVM_REUSE_RECEIPT=' + receipt, 'EMBERBSD_LLVM_REUSE_SHA256=' + ('0' * 64)]
out, error, status = Open3.capture3(env, *base, *fields.flat_map { |key| ['-V', '${' + key + '}'] })
raise error unless status.success?
active = fields.zip(out.lines.map(&:chomp)).to_h
raise 'reuse adapter would build or share source' unless active.fetch('NO_BUILD') == 'yes' && active.fetch('NO_CONFIGURE') == 'yes' && active.fetch('WRKSRC') == work + '/reuse-sdk/llvm-reuse' && active.fetch('PKG_FAIL_REASON').empty?
checks << 'opt-in uses private source state and disables a second compile'
FileUtils.mkdir_p(work + '/reuse-sdk')
before = LLVMStageReuse.tree(common)
%w[do-extract do-patch do-install].each do |target|
  out, error, status = Open3.capture3(env, *base, target)
  File.write(work + '/' + target + '-refused.log', out + error)
  raise target + ' did not reject the unaccepted receipt' if status.success? || !(out + error).include?('Accepted receipt drift')
  raise target + ' modified common source or objects' unless LLVMStageReuse.tree(common) == before
  raise target + ' installed an unaccepted payload' unless !File.exist?(work + '/reuse-sdk/.destdir') || LLVMStageReuse.tree(work + '/reuse-sdk/.destdir').empty?
  checks << target + ' refuses an unaccepted receipt before shared writes or payload installation'
end
out, error, status = Open3.capture3(env, *base, '-C', tree + '/lang/llvm', '-v', 'PKG_FAIL_REASON')
raise 'runtime role accepted reuse opt-in' unless status.success? && out.include?('requires the separate NetBSD cross SDK')
checks << 'runtime role rejects the SDK reuse opt-in'
reference = work + '/reference'; Dir.mkdir(reference)
accepted = work + '/accepted.fixture.json'
LLVMStageReuse.record(work + '/runtime/.llvm-reuse-inputs.json', reference, accepted)
accepted_hash = Digest::SHA256.file(accepted).hexdigest
accepted_args = base.map { |arg| arg.start_with?('EMBERBSD_LLVM_REUSE_RECEIPT=') ? 'EMBERBSD_LLVM_REUSE_RECEIPT=' + accepted : arg.start_with?('EMBERBSD_LLVM_REUSE_SHA256=') ? 'EMBERBSD_LLVM_REUSE_SHA256=' + accepted_hash : arg }
before = LLVMStageReuse.snapshot(runtime)
%w[do-extract do-patch do-install].each do |target|
  out, error, status = Open3.capture3(env, *accepted_args, target)
  File.write(work + '/' + target + '-accepted.log', out + error)
  raise target + ' failed accepted fixture: ' + out + error unless status.success?
  raise target + ' changed original source or objects' unless LLVMStageReuse.snapshot(runtime) == before
end
stage = work + '/reuse-sdk/.destdir/usr/pkg'
raise 'accepted full stage differs' unless LLVMStageReuse.tree(stage) == JSON.parse(File.read(accepted)).fetch('stage')
checks << 'actual pkgsrc hooks install the exact accepted fixture without recompiling or changing objects'
out, error, status = Open3.capture3(env, *accepted_args, 'llvm-select-stage')
File.write(work + '/ordinary-selector-rejects-incomplete-fixture.log', out + error)
raise 'normal SDK PLIST gate was bypassed' if status.success? || !(out + error).include?('missing complete-stage file:')
checks << 'ordinary SDK PLIST gate rejects the deliberately incomplete LLVM fixture'

File.write(work + '/results.json', JSON.pretty_generate({'checks' => checks, 'scope' => 'Actual pkgsrc metadata and override propagation only; fixture inventory and no LLVM package acceptance.'}) + "\n")
puts "PASS: #{checks.size} LLVM pkgsrc reuse adapter contracts"
