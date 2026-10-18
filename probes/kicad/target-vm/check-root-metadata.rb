#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Actual fork tools and finite FFS2 root metadata regression.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
require_relative 'root-metadata'

abort 'Usage: check-root-metadata.rb BASE OS_REPOSITORY REVISION NETBSD_TOOLS NEW_WORK' unless ARGV.size == 5
base, source, revision, tools, work = ARGV
base, source, tools = [base, source, tools].map { |p| File.realpath(p) }
work = File.expand_path(work)
abort 'Use a full source commit.' unless revision.match?(/\A[0-9a-f]{40}\z/)
abort 'Output exists.' if File.exist?(work) || File.symlink?(work)
input = base + '/usr/bin/tee'
snapshot = lambda do
  s = File.stat(input)
  {sha256: Digest::SHA256.file(input).hexdigest, mode: s.mode, uid: s.uid,
   gid: s.gid, device: s.dev, inode: s.ino, bytes: s.size, mtime: s.mtime.to_r.to_s}
end
before = snapshot.call
header = File.binread(input, 20)
abort 'Use the genuine AArch64 base executable.' unless header.start_with?("\x7fELF".b) &&
  header.getbyte(4) == 2 && header.getbyte(5) == 1 && header.byteslice(18, 2).unpack1('v') == 183 &&
  (before[:mode] & 07777) == 0555
builder = File.read(__dir__ + '/build.rb')
abort 'Builder must select tee from the base.' unless builder.match?(/\busr\/bin\/tee\b/)
abort 'Builder must retain the canonical source pin.' unless builder.include?('etc/mtree/NetBSD.dist.base')
abort 'Builder must use this metadata helper.' unless builder.include?("mtree << QueryVmRootMetadata.image_root(work + '/source/etc', tools, &run)")
FileUtils.mkdir_p(work, mode: 0700)
FileUtils.mkdir_p(work + '/root', mode: 0700)
FileUtils.mkdir_p(work + '/source/etc/mtree', mode: 0700)
# The work directory must share BASE's filesystem, as with the actual builder.
File.link(input, work + '/root/tee')
commands = []
run = lambda do |name, *argv|
  out, err, status = Open3.capture3(*argv)
  File.write(work + '/' + name + '.stdout', out)
  File.write(work + '/' + name + '.stderr', err)
  commands << {name: name, argv: argv, status: status.exitstatus}
  File.write(work + '/commands.json', JSON.pretty_generate(commands) + "\n")
  abort "Command failed: #{name}" unless status.success?
  out
end
pins = {}
%w[etc/group etc/master.passwd etc/mtree/NetBSD.dist.base sys/ufs/ufs/dinode.h].each do |relative|
  content = run.call('source-' + relative.tr('/', '-'), 'git', '-C', source, 'show', revision + ':' + relative)
  path = work + '/source/' + relative
  FileUtils.mkdir_p(File.dirname(path))
  File.write(path, content)
  pins[relative] = Digest::SHA256.hexdigest(content)
end
etc = work + '/source/etc'
override = QueryVmRootMetadata.image_root(etc, tools, &run)
generated = "/set uid=0 gid=0\n" + run.call('mtree', tools + '/nbmtree', '-c', '-k', 'type,mode,link', '-p', work + '/root')
images = {}
{'before'=>[generated,0700], 'fixed'=>[generated+override,0755]}.each do |name, (spec, mode)|
  file = work + '/' + name + '.mtree'
  File.write(file, spec)
  flat = run.call(name + '-flat', tools + '/nbmtree', '-C', '-N', etc, '-f', file)
  records = flat.lines.select { |line| line.split.first == '.' }
  expected = ['type=dir', 'uid=0', 'gid=0', 'mode='+format('%04o',mode)].sort
  abort 'Wrong resolved image root.' unless records.size == 1 && records.first.split.drop(1).sort == expected
  image = work + '/' + name + '.ffs'
  run.call(name + '-makefs', tools + '/nbmakefs', '-t', 'ffs', '-B', 'little', '-Z', '-s', '2m',
    '-o', 'version=2', '-F', file, '-N', etc, image, work + '/root')
  # Finite one-file image: the root is the only directory. The pinned ufs2_dinode
  # uses mode/nlink/uid/gid at 0/2/4/8, size at 16, and a 256-byte inode.
  prefix = [0040000 | mode, 2, 0, 0].pack('vvVV')
  abort 'Ambiguous fixture payload.' if File.binread(input).include?(prefix)
  data = File.binread(image); matches = []; offset = 0
  while (found = data.index(prefix, offset))
    matches << found if found % 256 == 0 && data.byteslice(found + 16, 8).unpack1('Q<') == 512
    offset = found + 1
  end
  abort 'Written FFS2 root metadata does not match.' unless matches.size == 1
  images[name] = {uid: 0, gid: 0, mode: format('%04o',mode), inode_offset: matches.first,
    sha256: Digest::SHA256.file(image).hexdigest, allocated_bytes: File.stat(image).blocks * 512}
end
abort 'Root inode placement changed.' unless images['before'][:inode_offset] == images['fixed'][:inode_offset]
inode_offset = images['before'][:inode_offset]
before_inode = File.binread(work + '/before.ffs', 256, inode_offset)
fixed_inode = File.binread(work + '/fixed.ffs', 256, inode_offset)
abort 'Other root inode fields changed.' unless before_inode.byteslice(2, 254) == fixed_inode.byteslice(2, 254)
canonical = File.read(etc + '/mtree/NetBSD.dist.base')
negatives = {
  'private-root' => canonical.sub('mode=0755','mode=0700'),
  'wrong-owner' => canonical.sub('uname=root','uid=1'),
  'missing-root' => canonical.lines.reject { |line| line.split.first == '.' }.join,
  'duplicate-root' => canonical + "\n.\n"
}
negative_results = {}
negatives.each do |name, text|
  variant = work + '/' + name
  FileUtils.mkdir_p(variant + '/mtree')
  %w[group master.passwd].each { |file| FileUtils.cp(etc + '/' + file, variant + '/' + file) }
  File.write(variant + '/mtree/NetBSD.dist.base', text)
  begin
    QueryVmRootMetadata.image_root(variant, tools) { |label,*argv| run.call(name + '-' + label,*argv) }
  rescue ArgumentError => error
    negative_results[name] = error.message
    next
  end
  abort 'Invalid canonical root accepted: ' + name
end
abort 'Host staging permissions changed.' unless File.stat(work + '/root').mode & 07777 == 0700
abort 'Hardlinked base input changed.' unless snapshot.call == before
File.write(work + '/result.json', JSON.pretty_generate(result: 'PASS', source_revision: revision,
  source: before, pinned_source_sha256: pins, images: images, other_root_inode_fields_unchanged: true,
  negative_controls: negative_results,
  tool_sha256: %w[nbmtree nbmakefs].to_h { |name| [name, Digest::SHA256.file(tools + '/' + name).hexdigest] },
  helper_sha256: %w[build.rb root-metadata.rb check-root-metadata.rb].to_h { |name| [name, Digest::SHA256.file(__dir__ + '/' + name).hexdigest] },
  scope: 'Actual shared builder helper and two small FFS2 images; private staging and immutable base unchanged. No guest execution.') + "\n")
puts 'PASS: actual FFS2 root 0700 -> canonical 0755, four source guards, unchanged base and host staging.'
