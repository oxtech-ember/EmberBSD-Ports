#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted); native actual-main failure-path Memcheck.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
require 'shellwords'
abort 'Usage: check-tempdir-exit.rb RECIPE MAKECONF CMAKE_BUILD NEW_OUTPUT' unless ARGV.size == 4
recipe, makeconf, build = ARGV.take(3).map { |path| File.realpath(path) }
output = File.expand_path(ARGV[3])
abort 'Output exists.' if File.exist?(output) || File.symlink?(output)
FileUtils.mkdir_p(output)
entries = JSON.parse(File.read(build + '/compile_commands.json'))
commands = []
run = lambda do |name, argv, directory, environment|
  out, err, status = Open3.capture3(environment, *argv, chdir: directory)
  File.write(output + '/' + name + '.log', out + err)
  commands << { name: name, argv: argv, directory: directory, environment: environment,
                status: status.exitstatus, signal: status.termsig }
  File.write(output + '/commands.json', JSON.pretty_generate(commands) + "\n")
  [out, err, status]
end
out, err, status = run.call('make-environment',
  [ENV.fetch('BMAKE', 'bmake'), '-C', recipe, "MAKECONF=#{makeconf}",
   '_PKGSRC_BARRIER=yes', 'show-var', 'VARNAME=MAKE_ENV'], output, {})
abort err unless status.success?
environment = Shellwords.split(out).to_h { |item| item.split('=', 2) }
File.write(output + '/entry.cpp', <<~'CPP')
  #include <cstdlib>
  extern int original_main(int, char**);
  int main(int argc, char** argv) {
      if (argc != 3) return 2;
      if (setenv("TMPDIR", argv[1], 1)) return 3;
      return original_main(argc - 1, argv + 1);
  }
CPP
results = []
{ 'OpenEXRTest' => 'testMagic', 'OpenEXRCoreTest' => 'testBase',
  'OpenEXRUtilTest' => 'testImageChannel' }.each do |program, test|
  matching = entries.select { |item| item.fetch('file').end_with?('/src/test/' + program + '/main.cpp') }
  abort 'Expected one actual test entry.' unless matching.size == 1
  entry = matching.first
  args = Shellwords.split(entry.fetch('command'))
  abort 'Explicit dependency outputs are outside this entry contract.' if
    args.any? { |arg| arg.match?(/\A-(?:MF|MT|MQ|MD|MMD)/) }
  compiler = args.first
  machine, _, status = run.call(program + '-machine', [compiler, '-dumpmachine'], output, environment)
  abort 'This memory check requires a native Linux compiler.' unless status.success? && machine.strip.end_with?('-linux-gnu')
  version, _, status = run.call(program + '-version', [compiler, '-dumpfullversion'], output, environment)
  abort 'Use the selected native GCC16.2.' unless status.success? && version.strip == '16.2.0'
  args[args.index('-o') + 1] = output + '/' + program + '-main.o'
  args.insert(1, '-Dmain=original_main')
  _, _, status = run.call(program + '-compile', args, entry.fetch('directory'), environment)
  abort 'Actual entry compilation failed.' unless status.success?
  _, _, status = run.call(program + '-entry', [compiler, '-c', output + '/entry.cpp',
    '-o', output + '/' + program + '-entry.o'], output, environment)
  abort 'Entry wrapper compilation failed.' unless status.success?
  directory = build + '/src/test/' + program
  args = Shellwords.split(File.read(directory + '/CMakeFiles/' + program + '.dir/link.txt'))
  original = 'CMakeFiles/' + program + '.dir/main.cpp.o'
  abort 'Actual link does not contain its original main object.' unless args.count(original) == 1
  args[args.index(original)] = output + '/' + program + '-main.o'
  args << output + '/' + program + '-entry.o'
  args[args.index('-o') + 1] = output + '/' + program
  _, _, status = run.call(program + '-link', args, directory, environment)
  abort 'Actual object linkage failed.' unless status.success?
  missing = output + '/absent'
  # Valgrind itself needs a valid TMPDIR at startup. Set the invalid client
  # value inside the tiny wrapper, then call the unchanged upstream main body.
  args = Shellwords.split(ENV.fetch('MEMCHECK', 'valgrind')) +
    %w[--error-exitcode=99 --leak-check=full --show-leak-kinds=all --errors-for-leak-kinds=all --track-origins=yes] +
    [output + '/' + program, missing, test]
  out, err, status = run.call(program + '-negative-memcheck', args, output, environment.merge('TMPDIR' => output))
  abort 'Expected the explicit invalid-directory failure.' unless status.exitstatus == 1 && (out + err).include?(missing)
  abort 'Memcheck did not finish without live blocks and errors.' unless
    err.include?('in use at exit: 0 bytes in 0 blocks') && err.include?('ERROR SUMMARY: 0 errors from 0 contexts')
  abort 'The missing directory was silently created.' if File.exist?(missing)
  results << { program: program, source_sha256: Digest::SHA256.file(entry.fetch('file')).hexdigest,
               executable_sha256: Digest::SHA256.file(output + '/' + program).hexdigest }
end
File.write(output + '/result.json', JSON.pretty_generate(results) + "\n")
puts 'PASS: actual upstream failure entries retain status 1 and release their owned memory.'
