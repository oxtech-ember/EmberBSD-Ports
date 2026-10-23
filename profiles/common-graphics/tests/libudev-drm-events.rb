#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
require 'digest'
require 'fileutils'
require 'open3'
require 'shellwords'
abort "usage: #{$PROGRAM_NAME} LIBUDEV_ARCHIVE NDEVD_ARCHIVE NEW_OUTPUT" unless ARGV.length == 3
archive, ndevd = ARGV.take(2).map { |path| File.realpath(path) }
work = File.expand_path(ARGV[2])
abort 'output exists' if File.exist?(work)
{
  archive => 'c4a8c30781438a76720f77876ca362b7a5ecd41d15cd603d52097c2cb10425f0',
  ndevd => '3bccf95a3f9bb331d47ee8062192d63ef6997bebe66922efe3810fba84bdf36d'
}.each { |path, sum| abort "archive mismatch: #{path}" unless Digest::SHA256.file(path).hexdigest == sum }
FileUtils.mkdir_p(work)
tests = File.realpath(__dir__)
recipe = File.expand_path('../../../pkgsrc/devel/libudev-bsd', tests)
patches = Dir[recipe + '/patches/patch-*'].sort
patches.each do |path|
  name = File.basename(path)
  expected = File.read(recipe + '/distinfo')[/^SHA1 \(#{Regexp.escape(name)}\) = (\h+)$/, 1]
  canonical = File.readlines(path).reject { |line| line.match?(/\$NetBSD.*/) }.join
  abort "patch mismatch: #{name}" unless expected == Digest::SHA1.hexdigest(canonical)
end
def run(work, label, command, expected: 0, contains: nil, **options)
  output, status = Open3.capture2e(*command, **options)
  File.write(work + '/' + label + '.log', command.shelljoin + "\n" + output + "\nexit=#{status.exitstatus}\n")
  abort "#{label} failed: #{output}" unless status.exitstatus == expected && (!contains || output.include?(contains))
  puts "PASS #{label}"
  output
end
cc = Shellwords.split(ENV.fetch('CC', 'cc'))
flags = Shellwords.split(ENV.fetch('CFLAGS', '-O1 -g'))
if RUBY_PLATFORM.include?('darwin')
  flags << '-DTEST_PACKET_SOCKET=SOCK_DGRAM'
  puts 'LIMIT: Darwin has no AF_UNIX SOCK_SEQPACKET; record-boundary test uses SOCK_DGRAM'
end
config = ''
%w[strlcpy strlcat].each do |name|
  test = work + '/check-' + name + '.c'
  File.write(test, "#include <string.h>\nint main(void) { char b[8] = {0}; return #{name}(b, \"x\", sizeof(b)) != 1; }\n")
  _, status = Open3.capture2e(*cc, '-std=gnu11', '-D_DARWIN_C_SOURCE', '-D_DEFAULT_SOURCE',
    '-Werror=implicit-function-declaration', test, '-o', work + '/check-' + name)
  config += "#define HAVE_#{name.upcase} 1\n" if status.success?
end
%w[baseline patched].each do |variant|
  directory = work + '/' + variant
  FileUtils.mkdir_p(directory)
  run(work, variant + '-extract', ['tar', '-xzf', archive, '-C', directory])
  source = directory + '/libudev-bsd-0.7.0.1'
  File.write(source + '/config.h', config)
  header = run(work, variant + '-header', ['tar', '-xOf', ndevd, 'ndevd-25.12.09/ndevd.h'])
  File.write(source + '/ndevd.h', header)
  patches.each do |patch|
    next if variant == 'baseline' && File.basename(patch) == 'patch-udev-drm-change'
    run(work, variant + '-' + File.basename(patch), ['patch', '-p0', '-i', patch], chdir: source)
  end
  dev = File.read(source + '/udev-dev.c')
  monitor = File.read(source + '/udev-monitor.c')
  native = dev[/^int\nudev_dev_monitor\(struct ndevd_msg.*?^\}/m]
  parser = monitor[/^static int\nparse_ndevd_message\(.*?^\}/m]
  abort 'actual functions absent' unless native && parser
  File.write(source + '/native-monitor.inc', native + "\n" + parser + "\n")
  buffer = monitor[/^\tchar event\[sizeof\(struct ndevd_msg\) \+ 1\];$/]
  if variant == 'patched'
    abort 'bounded receive buffer absent' unless buffer
    abort 'monitor does not pass actual received length' unless monitor.include?('parse_ndevd_message(event, (size_t)len, syspath, sizeof(syspath))')
  else
    buffer = "\tstruct ndevd_msg event[1];"
  end
  File.write(source + '/receive-buffer.inc', buffer + "\n")
  inputs = [tests + '/libudev-drm-events.c'] + %w[udev-filter.c udev-list.c utils.c].map { |name| source + '/' + name }
  command = cc + %w[-std=gnu11 -D_DARWIN_C_SOURCE -D_DEFAULT_SOURCE -Wall -Wextra -Werror] + flags + ['-I', source] + inputs + ['-o', directory + '/events']
  command << '-DBASELINE=1' if variant == 'baseline'
  run(work, variant + '-compile', command)
  if variant == 'baseline'
    run(work, 'baseline-change', [directory + '/events', 'change'], expected: 1, contains: 'FAIL native primary change discarded')
    run(work, 'baseline-filter', [directory + '/events', 'filter'], expected: 1, contains: 'FAIL drm_minor filter')
  else
    run(work, 'patched-contract', [directory + '/events'])
    # A control with the original receive capacity must reject an oversized record.
    File.write(source + '/receive-buffer.inc', "\tchar event[sizeof(struct ndevd_msg)];\n")
    mutant = command.map { |arg| arg == directory + '/events' ? directory + '/short-receive' : arg }
    run(work, 'short-receive-compile', mutant)
    run(work, 'short-receive-causal', [directory + '/short-receive'], expected: 1,
        contains: 'FAIL socket record length lost')
    File.write(source + '/receive-buffer.inc', buffer + "\n")
  end
end
puts 'PASS actual nb2 rejects primary change and drm_minor; patched source passes bounded event contract'
