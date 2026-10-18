#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
require 'digest'
require 'fileutils'
require 'json'
require 'open3'

abort 'Usage: CXX=target-g++ HOST_CXX=native-g++ platform-regression.rb ABS_PRISTINE_SOURCE ABS_NEW_WORK' unless ARGV.length == 2
source, work = ARGV.map { |path| File.expand_path(path) }
abort 'Work path already exists' if File.exist?(work) || File.symlink?(work)
target = ENV.fetch('CXX')
native = ENV.fetch('HOST_CXX')
here = File.expand_path(__dir__)
inputs = {
  'include/kiway.h' => '0290e9000940f0c15d4357630c19193983209c5f8a1c680213e22b4dad852b7c',
  'thirdparty/libcontext/libcontext.h' => '44f1833ee5e4a8829ebd7475f082c48716a3ffc8e49098ce4c1127a863d92cbf',
  'thirdparty/libcontext/libcontext.cpp' => '4973bec799321182bb81e3f0cb116b6fa7c9fc1241cb3efe218e087dce107e04',
  'common/import_gfx/dxf_import_plugin.cpp' => '834b018b0f97b1e1c3db3a1afc9b7ced221089f7f296874e9467b9912281b3ee'
}.freeze
inputs.each do |name, hash|
  abort "Not the pinned pristine KiCad 10.0.7 input: #{name}" unless Digest::SHA256.file(File.join(source, name)).hexdigest == hash
end
FileUtils.mkdir_p(work)

def run(work, name, command, reject: nil)
  environment = %w[CPATH C_INCLUDE_PATH CPLUS_INCLUDE_PATH LIBRARY_PATH].to_h { |key| [key, nil] }
  output, status = Open3.capture2e(environment, *command)
  File.write(File.join(work, "#{name}.json"), JSON.pretty_generate(command: command, exit: status.exitstatus, output: output) + "\n")
  if reject
    abort "#{name}: baseline did not fail for the expected reason" unless !status.success? && output.match?(reject)
  else
    abort "#{name} failed; see #{work}/#{name}.json" unless status.success?
  end
  output
end

[[target, 'target'], [native, 'native']].each do |compiler, label|
  run(work, "#{label}-version", [compiler, '--version'])
  macros = run(work, "#{label}-macros", [compiler, '-dM', '-E', '-x', 'c++', '/dev/null'])
  abort "#{label} compiler must be GCC 16" unless macros.match?(/^#define __GNUC__ 16$/) && !macros.match?(/^#define __clang__ /)
  if label == 'target'
    abort 'Target must be AArch64 EmberBSD/NetBSD' unless macros.match?(/^#define __NetBSD__ /) && macros.match?(/^#define __aarch64__ /)
  end
end

%w[pristine patched].each do |tree|
  inputs.each_key do |name|
    destination = File.join(work, tree, name)
    FileUtils.mkdir_p(File.dirname(destination))
    FileUtils.cp(File.join(source, name), destination)
  end
end
patches = %w[netbsd-platform.patch dxf-major-name.patch]
patches.each do |patch|
  run(work, patch, ['patch', '-f', '-F', '0', '-p1', '-d', File.join(work, 'patched'), '-i', File.join(here, 'patches', patch)])
end

pristine_context = File.join(work, 'pristine/thirdparty/libcontext')
context = File.join(work, 'patched/thirdparty/libcontext')
run(work, 'context-before', [target, '-std=c++17', '-O2', '-fno-lto', '-I', pristine_context, '-c', File.join(pristine_context, 'libcontext.cpp'), '-o', File.join(work, 'context-before.o')], reject: /LIBCONTEXT_CALL_CONVENTION/)
run(work, 'context-target-object', [target, '-std=c++17', '-O2', '-fno-lto', '-I', context, '-c', File.join(context, 'libcontext.cpp'), '-o', File.join(work, 'context-target.o')])
run(work, 'context-target-link', [target, '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror', '-I', context, File.join(here, 'context-contract.cpp'), File.join(work, 'context-target.o'), '-o', File.join(work, 'context-target')])
run(work, 'context-native-object', [native, '-std=c++17', '-O2', '-fno-lto', '-I', context, '-c', File.join(context, 'libcontext.cpp'), '-o', File.join(work, 'context-native.o')])
run(work, 'context-native-link', [native, '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror', '-I', context, File.join(here, 'context-contract.cpp'), File.join(work, 'context-native.o'), '-o', File.join(work, 'context-native')])
run(work, 'context-native-run', [File.join(work, 'context-native')])

%w[pristine patched].each do |tree|
  dxf = File.read(File.join(work, tree, 'common/import_gfx/dxf_import_plugin.cpp'))
  ellipse = dxf[/void DXF_IMPORT_PLUGIN::addEllipse\(.*?(?=\nvoid DXF_IMPORT_PLUGIN::addText\()/m]
  abort 'Cannot locate the actual ellipse function' unless ellipse
  input = File.join(work, "#{tree}-ellipse.cpp")
  File.write(input, "#include <sys/types.h>\n#{ellipse}\n#ifndef major\n#error System major macro was removed\n#endif\n")
  run(work, "#{tree}-ellipse", [target, '-E', '-P', input, '-o', "#{input}.ii"], reject: tree == 'pristine' ? /macro .major. passed 2 arguments/ : nil)

  kiway = File.read(File.join(work, tree, 'include/kiway.h'))
  loader = kiway[/#ifndef SWIG\n#if defined\(__linux__\).*?#endif  \/\/ SWIG/m]
  abort 'Cannot locate the actual loader branch' unless loader
  input = File.join(work, "#{tree}-loader.cpp")
  File.write(input, "#{loader}\nLIB_ENV_VAR\n")
  run(work, "#{tree}-loader", [target, '-E', '-P', input, '-o', "#{input}.ii"], reject: tree == 'pristine' ? /Platform support missing/ : nil)
  if tree == 'patched'
    abort 'Unexpected loader path variable' unless File.read("#{input}.ii").match?(/wxT\(\s*"LD_LIBRARY_PATH"\s*\)/)
  end
end

iso = File.join(work, 'iso646.cpp')
File.write(iso, "#include <iso646.h>\nstatic_assert(true and not false);\n")
run(work, 'iso646', [target, '-std=c++17', '-Wall', '-Wextra', '-Werror', '-c', iso, '-o', File.join(work, 'iso646.o')])
receipt = {
  source_sha256: inputs,
  patch_sha256: patches.to_h { |name| [name, Digest::SHA256.file(File.join(here, 'patches', name)).hexdigest] },
  target_binary_sha256: Digest::SHA256.file(File.join(work, 'context-target')).hexdigest,
  native_context_runtime: 'passed',
  target_context_runtime: 'unrun; execute context-target on EmberBSD',
  loader_and_ellipse_scope: 'actual source excerpts, preprocessing only',
  full_kicad: 'unrun'
}
File.write(File.join(work, 'receipt.json'), JSON.pretty_generate(receipt) + "\n")
puts 'PASS: causal cross-compile/preprocessor regressions and native context runtime; target runtime remains unrun.'
