#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), real pkg_create metadata regression.
require 'fileutils'
require 'open3'
abort 'Usage: llvm-python315-packlist.rb HOST_PKG_CREATE NEW_WORK' unless ARGV.size == 2
create, work = ARGV.map { |path| File.expand_path(path) }
Dir.mkdir(work)
source = File.expand_path('../cross/prepare-llvm-python315.rb', __dir__)
# Run the actual small transformation without executing package migration.
method = File.read(source)[/^def prepare_packlist\(contents\)\n.*?^end\n/m]
abort 'Packlist transformation not found' unless method
eval(method, TOPLEVEL_BINDING, source)
FileUtils.mkdir_p(File.join(work, 'payload/bin'))
File.write(File.join(work, 'payload/bin/test'), 'test payload')
File.write(File.join(work, 'comment'), 'Package metadata regression')
File.write(File.join(work, 'description'), 'Not an installed compiler package.')
input = "@cwd /usr/pkg\n@name llvm-plist-fixture-1.0\nbin/test\n@comment MD5:old\n@ignore\n+COMMENT\n@ignore\n+DESC\n"
[false, true].each do |fixed|
  text = fixed ? prepare_packlist(input) : input.lines.reject { |line| line.start_with?('@comment MD5:') }.join
  plist = File.join(work, fixed ? 'fixed.plist' : 'baseline.plist')
  File.write(plist, text)
  archive = File.join(work, fixed ? 'fixed.tgz' : 'baseline.tgz')
  output, status = Open3.capture2e(create, '-p', File.join(work, 'payload'), '-I', '/usr/pkg', '-f', plist,
                                 '-c', File.join(work, 'comment'), '-d', File.join(work, 'description'), archive)
  abort output unless status.success?
  output, status = Open3.capture2e('/usr/bin/tar', '-xOf', archive, '+CONTENTS')
  abort output unless status.success?
  File.write(File.join(work, fixed ? 'fixed-contents' : 'baseline-contents'), output)
  names = output.scan(/^@ignore\n(\+[^\n]+)\n/).flatten
  abort 'Wrong metadata uniqueness result' unless (names.uniq == names) == fixed
end
abort 'Ignored payload was changed' unless prepare_packlist("@ignore\nprivate-file\n") == "@ignore\nprivate-file\n"
puts 'PASS: original packlist duplicates metadata; actual repaired transformation preserves one generated control entry.'
