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
patches = %w[patch-evdev-sysctl patch-render-nodes patch-udev-drm-change].map do |name|
  path = File.join(recipe, 'patches', name)
  patch_sum = File.read(File.join(recipe, 'distinfo'))[/^SHA1 \(#{Regexp.escape(name)}\) = ([a-f0-9]{40})$/, 1]
  abort "patch SHA1 mismatch: #{name}" unless Digest::SHA1.file(path).hexdigest == patch_sum
  path
end

def run(work, label, *command, expected_failure: false, failure_text: 'FAIL path=/dev/dri/renderD128 drm=0 kwin=0 expected=1/1', **options)
  output, status = Open3.capture2e(*command, **options)
  File.write(File.join(work, "#{label}.log"), "#{command.shelljoin}\n#{output}")
  if expected_failure
    abort "#{label}: missing causal baseline failure\n#{output}" unless status.exitstatus == 1 &&
      output.include?(failure_text)
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
  patches.each { |patch| run(work, File.basename(patch), 'patch', '-p0', '-i', patch, chdir: source) } if variant == 'patched'
  inputs = [File.join(tests, 'libudev-render-nodes.c')] + %w[udev-filter.c udev-list.c utils.c].map { |f| File.join(source, f) }
  binary = File.join(directory, 'classify')
  run(work, "#{variant}-compile", *cc, '-std=gnu11', '-D_DARWIN_C_SOURCE', '-D_DEFAULT_SOURCE',
      *flags, '-I', source, *inputs, '-o', binary)
  run(work, "#{variant}-run", binary, expected_failure: variant == 'baseline')
end
puts 'PASS pinned source rejects renderD128; patched source passes classification and real filters'
# Use a syscall declaration boundary, not host kernel state, for cache tests.
headers = File.join(work, 'sysctl-headers')
FileUtils.mkdir_p(File.join(headers, 'sys'))
File.write(File.join(headers, 'sys/sysctl.h'), "#include <stddef.h>\nint sysctlbyname(const char *, void *, size_t *, const void *, size_t);\n")
length_only = File.join(work, 'length-only/libudev-bsd-0.7.0.1')
FileUtils.mkdir_p(File.dirname(length_only))
FileUtils.cp_r(File.join(work, 'baseline/libudev-bsd-0.7.0.1'), length_only)
path = File.join(length_only, 'udev-utils.c')
text = File.read(path)
anchor = "#ifdef HAVE_SYSCTLBYNAME\n\tsize_t len;\n#endif"
abort 'missing length-only negative-control anchor' unless text.include?(anchor)
File.write(path, text.sub(anchor, "#ifdef HAVE_SYSCTLBYNAME\n\tsize_t len = sizeof(enabled);\n#endif"))
%w[baseline length-only patched].each do |variant|
  source = File.join(work, variant, 'libudev-bsd-0.7.0.1')
  inputs = [File.join(tests, 'libudev-evdev-sysctl.c')] + %w[udev-filter.c udev-list.c utils.c].map { |f| File.join(source, f) }
  binary = File.join(work, variant, 'sysctl-cache')
  run(work, "#{variant}-sysctl-compile", *cc, '-std=gnu11', '-D_DARWIN_C_SOURCE', '-D_DEFAULT_SOURCE',
      '-DHAVE_SYSCTLBYNAME=1', '-ftrivial-auto-var-init=pattern', *flags,
      '-I', headers, '-I', source, *inputs, '-o', binary)
  if variant == 'baseline'
    run(work, 'baseline-sysctl-length', binary, 'present', expected_failure: true,
        failure_text: 'FAIL: uninitialized sysctl buffer length')
  elsif variant == 'length-only'
    run(work, 'length-only-sysctl-cache', binary, 'error', expected_failure: true,
        failure_text: 'FAIL: failed sysctl populated cache')
  else
    %w[present nonzero absent error short oversize].each { |mode| run(work, "patched-sysctl-#{mode}", binary, mode) }
  end
end
puts 'PASS initialized sysctl length and complete-read cache; both causal negative controls reject'
