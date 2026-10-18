#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted); use the actual configured upstream CLI rules.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
require 'shellwords'

abort 'Usage: build-memory-query.rb SOURCE CLI_BUILD NEW_OUTPUT' unless ARGV.length == 3
source, build = ARGV.take(2).map { |p| File.realpath(p) }
output = File.expand_path(ARGV[2])
abort 'Use absolute portable paths.' unless [source, build, output].all? { |p| p.match?(%r{\A/[A-Za-z0-9_./-]+\z}) }
abort 'Output exists.' if File.exist?(output) || File.symlink?(output)
config = build + '/src/include/ngspice/config.h'
text = File.read(config)
abort 'Use a configured CLI, not a shared callback build.' if text.match?(/^#define SHARED_MODULE /)
%w[CIDER XSPICE OSDI KLU USE_OMP HAVE_LIBFFTW3 HAVE_GNUREADLINE].each do |feature|
  abort "Missing selected feature #{feature}" unless text.match?(/^#define #{feature} /)
end
FileUtils.mkdir_p(output)
commands = []
run = lambda do |name, argv, cwd = output|
  stdout, stderr, status = Open3.capture3(*argv, chdir: cwd)
  File.write(output + '/' + name + '.stdout', stdout)
  File.write(output + '/' + name + '.stderr', stderr)
  commands << { name: name, argv: argv, cwd: cwd, status: status.exitstatus }
  File.write(output + '/commands.json', JSON.pretty_generate(commands) + "\n")
  abort "Failed #{name}; see preserved output." unless status.success?
  stdout
end
makefile = File.read(build + '/src/frontend/Makefile')
value = lambda do |key|
  lines = makefile.lines.select { |line| line.start_with?(key + ' = ') }
  abort "Ambiguous configured #{key}" unless lines.length == 1
  Shellwords.split(lines.first.split(' = ', 2).last)
end
cc = value.call('CC')
abort 'Expected GCC 16.2.0.' unless run.call('compiler', cc + ['-dumpfullversion']).strip == '16.2.0'
recorded_source = value.call('top_srcdir')
abort 'Wrong configured source.' unless recorded_source.length == 1 &&
  File.realpath(recorded_source.first, build + '/src/frontend') == source
modules = %w[get_phys_mem_size get_avail_mem_size get_resident_set_size]
run.call('upstream-objects', [ENV.fetch('MAKE', 'make'), '-j1', *modules.map { |name| name + '.lo' }],
         build + '/src/frontend')
contract = File.join(__dir__, 'memory-query-contract.c')
objects = modules.map do |name|
  metadata = File.read(build + '/src/frontend/' + name + '.lo')
  selected = %w[pic_object non_pic_object].filter_map do |key|
    path = metadata[/^#{key}='([^']+)'$/, 1]
    path unless path.nil? || path == 'none'
  end.first
  abort "Missing configured object #{name}" unless selected &&
    selected.match?(%r{\A(?:\.libs/)?#{Regexp.escape(name)}\.o\z})
  build + '/src/frontend/' + selected
end
argv = cc + value.call('CFLAGS') + value.call('CPPFLAGS') +
  ['-I' + build + '/src/include', '-I' + source + '/src/include', contract] +
  objects + value.call('LDFLAGS') + ['-o', output + '/memory-query']
run.call('link-contract', argv)
inputs = [config, build + '/src/frontend/Makefile', contract] +
  modules.map { |name| source + '/src/frontend/' + name + '.c' } + objects
File.write(output + '/result.json', JSON.pretty_generate({
  scope: 'Three actual upstream object targets and a GCC16 query consumer; execution is a separate check.',
  inputs: inputs.to_h { |path| [path, Digest::SHA256.file(path).hexdigest] },
  output: output + '/memory-query', sha256: Digest::SHA256.file(output + '/memory-query').hexdigest
}) + "\n")
puts 'PASS: configured upstream CLI memory modules and GCC16 consumer linked'
