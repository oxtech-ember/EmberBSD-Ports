#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted); actual small FFS2 image metadata contract.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'

abort 'Usage: check-fstat-metadata.rb BASE SOURCE_ETC NETBSD_TOOLS NEW_WORK' unless ARGV.size == 4
base, etc, tools = ARGV.take(3).map { |p| File.realpath(p) }
work = File.expand_path(ARGV.last)
abort 'Output exists.' if File.exist?(work) || File.symlink?(work)
input = base + '/usr/bin/fstat'
abort 'Use the canonical kmem group.' unless File.readlines(etc + '/group').count { |s| s.split(':').take(3) == %w[kmem * 2] } == 1
snapshot = lambda do
  s = File.stat(input)
  {sha256: Digest::SHA256.file(input).hexdigest, mode: s.mode, uid: s.uid,
   gid: s.gid, device: s.dev, inode: s.ino, bytes: s.size, mtime: s.mtime.to_r.to_s}
end
before = snapshot.call
abort 'Fixture requires the genuine setgid executable mode.' unless before[:mode] & 07777 == 02555
source = File.read(__dir__ + '/build.rb')
literal = source.lines.grep(/^mtree << "\.\/usr\/bin\/fstat /)
abort 'Expected one explicit builder metadata record.' unless literal.size == 1
override = JSON.parse(literal.first.delete_prefix('mtree << ').strip)
FileUtils.mkdir_p(work + '/root/usr/bin')
# NEW_WORK must be on BASE's filesystem, as for the real image builder.
File.link(input, work + '/root/usr/bin/fstat')
commands = []
run = lambda do |label, *argv|
  out, err, status = Open3.capture3(*argv)
  File.write(work + '/' + label + '.stdout', out)
  File.write(work + '/' + label + '.stderr', err)
  commands << {name: label, argv: argv, status: status.exitstatus}
  File.write(work + '/commands.json', JSON.pretty_generate(commands) + "\n")
  abort "Command failed: #{label}" unless status.success?
  out
end
generated = "/set uid=0 gid=0\n" + run.call('mtree', tools + '/nbmtree', '-c', '-k', 'type,mode,link', '-p', work + '/root')
results = {}
{ 'before' => [generated, 0], 'fixed' => [generated + override, 2] }.each do |label, (spec, gid)|
  File.write(work + '/' + label + '.mtree', spec)
  flat = run.call(label + '-flat', tools + '/nbmtree', '-C', '-N', etc, '-f', work + '/' + label + '.mtree')
  records = flat.lines.grep(%r{\A\./usr/bin/fstat })
  abort 'Incorrect resolved metadata.' unless records.size == 1 &&
    records.first.split.drop(1).sort == ["gid=#{gid}", 'mode=02555', 'type=file', 'uid=0'].sort
  image = work + '/' + label + '.ffs'
  run.call(label + '-makefs', tools + '/nbmakefs', '-t', 'ffs', '-B', 'little', '-Z', '-s', '2m', '-o', 'version=2',
    '-F', work + '/' + label + '.mtree', '-N', etc, image, work + '/root')
  # Finite single-file image check, using ufs2_dinode fields from sys/ufs/ufs/dinode.h:
  # mode/nlink/uid/gid at 0/2/4/8; size at 16; each inode occupies 256 bytes.
  prefix = [0100000 | 02555, 1, 0, gid].pack('vvVV')
  abort 'Ambiguous fixture payload.' if File.binread(input).include?(prefix)
  data = File.binread(image)
  matches = []
  offset = 0
  while (found = data.index(prefix, offset))
    matches << found if found % 256 == 0 && data.byteslice(found + 16, 8).unpack1('Q<') == before[:bytes]
    offset = found + 1
  end
  abort 'Written FFS2 metadata does not match.' unless matches.size == 1
  results[label] = {uid: 0, gid: gid, mode: '02555', inode_offset: matches.first,
                    image_sha256: Digest::SHA256.file(image).hexdigest}
end
abort 'Inode placement changed.' unless results['before'][:inode_offset] == results['fixed'][:inode_offset]
abort 'Hardlinked base input changed.' unless before == snapshot.call
File.write(work + '/result.json', JSON.pretty_generate(source: before, images: results,
  scope: 'Actual makefs/mtree and two 2 MiB images; base bytes/ownership/mode unchanged; no guest execution.') + "\n")
puts 'PASS: baseline gid0, fixed root:kmem/02555 in actual FFS2; immutable base unchanged.'
