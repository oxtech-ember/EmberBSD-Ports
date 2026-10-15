#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
require 'digest'
require 'fileutils'
require 'open3'
require 'shellwords'

abort "usage: #{$PROGRAM_NAME} SOURCE_ARCHIVE NEW_WORK_DIRECTORY" unless ARGV.length == 2
archive = File.realpath(ARGV[0])
work = File.expand_path(ARGV[1])
abort "work directory already exists: #{work}" if File.exist?(work)
expected = 'c4a8c30781438a76720f77876ca362b7a5ecd41d15cd603d52097c2cb10425f0'
abort 'libudev-bsd 0.7.0.1 archive SHA256 mismatch' unless Digest::SHA256.file(archive).hexdigest == expected
FileUtils.mkdir_p(work)
tests = File.realpath(__dir__)
recipe = File.expand_path('../recipes/devel/libudev-bsd', tests)
patch = File.join(recipe, 'patches/patch-render-nodes')
patch_sum = File.read(File.join(recipe, 'distinfo'))[/^SHA1 \(patch-render-nodes\) = ([a-f0-9]{40})$/, 1]
abort 'patch SHA1 mismatch' unless Digest::SHA1.file(patch).hexdigest == patch_sum

def run(work, label, *command, expected_failure: false, **options)
  output, status = Open3.capture2e(*command, **options)
  File.write(File.join(work, "#{label}.log"), "#{command.shelljoin}\n#{output}")
  if expected_failure
    abort "#{label}: missing causal baseline failure\n#{output}" unless status.exitstatus == 1 &&
      output.include?('FAIL path=/dev/dri/renderD128 drm=0 kwin=0 expected=1/1')
  else
    abort "#{label} failed\n#{output}" unless status.success?
  end
  puts "PASS #{label}"
end

cc = Shellwords.split(ENV.fetch('CC', 'cc'))
flags = Shellwords.split(ENV.fetch('CFLAGS', '-O1 -g'))
config = "/* Host-only classifier/filter contract. */\n"
%w[strlcpy strlcat].each do |name|
  check = File.join(work, "check-#{name}.c")
  File.write(check, "#include <string.h>\nint main(void) { char b[8] = {0}; return #{name}(b, \"x\", sizeof(b)) != 1; }\n")
  output, status = Open3.capture2e(*cc, '-std=gnu11', '-D_DARWIN_C_SOURCE', '-D_DEFAULT_SOURCE',
    '-Werror=implicit-function-declaration', check, '-o', File.join(work, "check-#{name}"))
  File.write(File.join(work, "check-#{name}.log"), output)
  config += "#define HAVE_#{name.upcase} 1\n" if status.success?
end
%w[baseline patched].each do |variant|
  directory = File.join(work, variant)
  FileUtils.mkdir_p(directory)
  run(work, "#{variant}-extract", 'tar', '-xzf', archive, '-C', directory)
  source = File.join(directory, 'libudev-bsd-0.7.0.1')
  File.write(File.join(source, 'config.h'), config)
  run(work, 'patch', 'patch', '-p0', '-i', patch, chdir: source) if variant == 'patched'
  inputs = [File.join(tests, 'libudev-render-nodes.c')] + %w[udev-filter.c udev-list.c utils.c].map { |f| File.join(source, f) }
  binary = File.join(directory, 'classify')
  run(work, "#{variant}-compile", *cc, '-std=gnu11', '-D_DARWIN_C_SOURCE', '-D_DEFAULT_SOURCE',
      *flags, '-I', source, *inputs, '-o', binary)
  run(work, "#{variant}-run", binary, expected_failure: variant == 'baseline')
end
puts 'PASS pinned source rejects renderD128; patched source passes classification and real filters'
