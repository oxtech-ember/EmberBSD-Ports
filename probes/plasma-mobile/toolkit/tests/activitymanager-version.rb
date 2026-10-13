#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Compile the real daemon with both version headers.
require 'fileutils'
require 'json'
require 'shellwords'

abort 'Usage: activitymanager-version.rb UPSTREAM_SOURCE CONFIGURED_BUILD NEW_OUTPUT' unless ARGV.length == 3
source, build, output = ARGV.map { |path| File.expand_path(path) }
abort 'Output already exists' if File.exist?(output)
recipe = File.expand_path('../recipes/x11/plasma6-kactivitymanagerd', __dir__)
entry = JSON.parse(File.read(File.join(build, 'compile_commands.json'))).find do |item|
  item.fetch('file').end_with?('/src/service/Application.cpp')
end
abort 'The compilation database has no daemon Application.cpp' unless entry
args = entry['arguments'] || Shellwords.split(entry.fetch('command'))
compiler = args.shift
flags = []
skip = false
args.each do |arg|
  if skip
    skip = false
  elsif arg == '-o'
    skip = true
  elsif arg != '-c' && arg != entry.fetch('file')
    flags << arg
  end
end
FileUtils.mkdir_p(File.join(output, 'patched', 'src', 'service'))
%w[CMakeLists.txt src/service/Application.cpp].each do |path|
  FileUtils.cp(File.join(source, path), File.join(output, 'patched', path))
end
Dir[File.join(recipe, 'patches', 'patch-*')].sort.each do |path|
  File.open(path) do |input|
    abort "Patch failed: #{path}" unless system('patch', '-f', '-F', '0', '-p0', '-d', File.join(output, 'patched'), in: input)
  end
end
# Preserve the real protocol header. Copy it as lowercase to reproduce the
# include collision even on a case-sensitive test host.
shadow = File.join(output, 'shadow')
generated = File.join(output, 'generated')
FileUtils.mkdir_p([shadow, generated])
protocol = File.join(source, 'src', 'service', 'Version.h')
FileUtils.cp(protocol, File.join(shadow, 'version.h'))
version = %w[kactivitymanagerd_version.h version.h].map { |name| File.join(build, name) }.find { |path| File.file?(path) }
abort 'No generated package version header' unless version
version_text = File.read(version)
abort 'Wrong package version header' unless version_text.include?('#define KACTIVITYMANAGERD_VERSION_STRING "6.7.5"')
FileUtils.cp(version, File.join(generated, 'kactivitymanagerd_version.h'))
# The generated include name must match the production CMake declaration.
cmake = File.read(File.join(output, 'patched', 'CMakeLists.txt'))
abort 'CMake does not generate the unique header' unless cmake.include?('VERSION_HEADER ${CMAKE_BINARY_DIR}/kactivitymanagerd_version.h')
FileUtils.cp(version, File.join(generated, 'version.h'))
# Keep pkgsrc dependency rewriting. Give only this test directory an identity
# mapping, and write wrapper diagnostics beside the test results.
environment = { 'LC_ALL' => 'C' }
wrapper_config = ENV['CWRAPPERS_CONFIG_DIR'] || File.expand_path('../config', File.dirname(compiler))
if File.file?(File.join(wrapper_config, 'c++'))
  scoped_config = File.join(output, 'wrapper-config')
  FileUtils.mkdir_p(scoped_config)
  configuration = File.read(File.join(wrapper_config, 'c++'))
  configuration = configuration.sub(/^worklog=.*$/, "worklog=#{output}/wrapper.log")
  configuration += "\ntransform=I:#{output}:#{output}\n"
  File.write(File.join(scoped_config, 'c++'), configuration)
  environment['CWRAPPERS_CONFIG_DIR'] = scoped_config
end
commands = {}
%w[upstream patched].each do |label|
  file = label == 'upstream' ? File.join(source, 'src/service/Application.cpp') : File.join(output, 'patched/src/service/Application.cpp')
  command = [compiler, "-I#{shadow}", "-I#{generated}", *flags, '-fsyntax-only', file]
  commands[label] = command
  status = system(environment, *command, chdir: entry.fetch('directory'), out: File.join(output, "#{label}.out"), err: File.join(output, "#{label}.err"))
  errors = File.read(File.join(output, "#{label}.err"))
  if label == 'upstream'
    abort 'Original source did not reproduce the version-header error' if status || !errors.match?(/KACTIVITYMANAGERD_VERSION_STRING.*(not declared|undeclared)/)
  else
    abort 'Patched source did not compile; inspect patched.err' unless status
  end
end
File.write(File.join(output, 'environment.json'), JSON.pretty_generate(environment) + "\n")
File.write(File.join(output, 'commands.json'), JSON.pretty_generate(commands) + "\n")
File.write(File.join(output, 'compile_commands.json'), JSON.pretty_generate([
  { 'directory' => entry.fetch('directory'), 'arguments' => commands.fetch('patched'),
    'file' => File.join(output, 'patched/src/service/Application.cpp') }
]) + "\n")
abort 'The protocol version header changed' unless File.binread(protocol) == File.binread(File.join(shadow, 'version.h'))
puts 'PASS: the original daemon reproduces header shadowing; the patched daemon compiles with both version definitions'
