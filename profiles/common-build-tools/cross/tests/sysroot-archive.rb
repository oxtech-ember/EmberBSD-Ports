# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted), 2026-10-16.
# Exercise extraction with real xz streams. All hostile paths stay in one fixture.
require 'digest'
require 'fileutils'
require 'open3'
require 'rbconfig'
require 'rubygems/package'
require 'timeout'
require 'tmpdir'
require_relative '../sysroot-archive'

def check(condition, message)
  abort 'FAIL: ' + message unless condition
end

def tar_bytes(entries, trailing = ''.b)
  result = ''.b
  entries.each do |entry|
    data = entry.fetch(:data, ''.b).b
    header = Gem::Package::TarHeader.new(name: entry.fetch(:name), mode: entry.fetch(:mode, 0644),
      uid: 0, gid: 0, size: data.bytesize, mtime: 0, typeflag: entry.fetch(:type, '0'),
      linkname: entry.fetch(:link, ''), magic: 'ustar', version: '00', uname: 'root',
      gname: 'wheel', devmajor: 0, devminor: 0, prefix: '')
    result << header.to_s << data
    result << "\0" * ((512 - data.bytesize % 512) % 512)
  end
  result << "\0" * 1024 << trailing
end

def write_xz(path, bytes)
  output, error, status = Open3.capture3('xz', '-c', stdin_data: bytes, binmode: true)
  check(status.success?, 'fixture xz failed: ' + error)
  File.binwrite(path, output)
  path
end

def mode(path)
  File.stat(path).mode & 07777
end

Dir.mktmpdir('ember-sysroot-archive') do |dir|
  sentinel = File.join(dir, 'outside-sentinel')
  File.binwrite(sentinel, "Outside destination. Do not change.\0\xff".b)
  File.chmod(0640, sentinel)
  baseline = [File.binread(sentinel), File.stat(sentinel).ino, File.stat(sentinel).nlink, mode(sentinel)]
  unchanged = lambda do
    check([File.binread(sentinel), File.stat(sentinel).ino, File.stat(sentinel).nlink, mode(sentinel)] == baseline,
      'extraction changed the sentinel outside its destination')
  end
  loader = "loader\0binary\xff\x80\n".b
  library = "libc\0binary\x81\xfe\n".b
  startup = (0..255).to_a.pack('C*') * 4099 # Cross the extractor's 1 MiB read boundary.
  header = "/* fixture C header */\n"
  base_entries = [
    {name: '.', type: '5', mode: 0755},
    {name: 'lib', type: '5', mode: 0755},
    {name: 'libexec', type: '5', mode: 0755},
    {name: 'usr', type: '5', mode: 0755},
    {name: 'usr/lib', type: '5', mode: 0755},
    {name: 'usr/include', type: '5', mode: 0755},
    {name: 'libexec/ld.elf_so', data: loader, mode: 0555},
    {name: 'lib/libc.so.12.229', data: library, mode: 0555},
    {name: 'lib/libc.so.12', type: '2', link: 'libc.so.12.229', mode: 0777},
    {name: 'usr/lib/libc.so.12', type: '2', link: '/lib/libc.so.12', mode: 0777},
    {name: 'usr/lib/libc.so', type: '2', link: 'libc.so.12', mode: 0777},
    # The OS base/comp lists intentionally share selected library aliases.
    {name: 'usr/lib/libproc.so', type: '2', link: 'libproc.so.1.0', mode: 0755},
    {name: 'usr/lib/libproc.so.1.0', data: library, mode: 0555},
    # Both links precede their provider, which arrives in the other set.
    {name: 'usr/lib/crt-chain.o', type: '1', link: 'usr/lib/crt-forward.o'},
    {name: 'usr/lib/crt-forward.o', type: '1', link: './usr/lib/crt0.o'}
  ]
  comp_entries = [
    # Real base and comp sets share their directory entries.
    {name: './usr/', type: '5', mode: 0755},
    {name: './usr/lib/', type: '5', mode: 0755},
    {name: './usr/include/', type: '5', mode: 0755},
    {name: 'usr/lib/libproc.so', type: '2', link: 'libproc.so.1.0', mode: 0755},
    {name: 'usr/include/stdio.h', data: header, mode: 0444},
    {name: 'usr/include/stdio-alias.h', type: '2', link: 'stdio.h', mode: 0777},
    {name: 'usr/lib/crt0.o', data: startup, mode: 0644},
    {name: 'usr/lib/crt-backward.o', type: '1', link: 'usr/lib/crt0.o'}
  ]
  base = write_xz(File.join(dir, 'base.tar.xz'), tar_bytes(base_entries, "\0" * 8192))
  comp = write_xz(File.join(dir, 'comp.tar.xz'), tar_bytes(comp_entries))
  check(File.size(base) < 16_384 && File.size(comp) < 16_384, 'fixture archives are unexpectedly large')
  root = File.join(dir, 'sysroot')
  previous_umask = File.umask(0077)
  begin
    inventory = EmberSysrootArchive.extract([base, comp], root)
  ensure
    File.umask(previous_umask)
  end
  {'libexec/ld.elf_so' => [loader, 0555], 'lib/libc.so.12.229' => [library, 0555],
   'usr/include/stdio.h' => [header, 0444], 'usr/lib/crt0.o' => [startup, 0644]}.each do |name, (bytes, permissions)|
    path = File.join(root, name)
    check(File.binread(path) == bytes.b, 'changed file bytes: ' + name)
    check(mode(path) == permissions, 'changed file mode: ' + name)
    check(inventory.fetch(name).values_at('type', 'mode', 'sha256') ==
      ['file', permissions, Digest::SHA256.hexdigest(bytes)], 'incorrect file inventory: ' + name)
  end
  %w[usr usr/lib usr/include].each do |name|
    check(File.directory?(File.join(root, name)) && mode(File.join(root, name)) == 0755,
      'shared directory was lost or retained the host umask: ' + name)
    check(inventory.fetch(name).fetch('type') == 'directory', 'incorrect shared directory inventory')
  end
  {'lib/libc.so.12' => 'libc.so.12.229', 'usr/lib/libc.so.12' => '../../lib/libc.so.12',
   'usr/lib/libc.so' => 'libc.so.12', 'usr/lib/libproc.so' => 'libproc.so.1.0',
   'usr/include/stdio-alias.h' => 'stdio.h'}.each do |name, link|
    path = File.join(root, name)
    check(File.symlink?(path) && File.readlink(path) == link, 'incorrect normalized alias: ' + name)
    check(File.realpath(path).start_with?(root + '/'), 'alias resolves outside the target: ' + name)
    check(inventory.fetch(name).values_at('type', 'link') == ['symlink', link], 'incorrect alias inventory')
  end
  check(File.binread(File.join(root, 'usr/lib/libc.so')) == library, 'absolute target link used host files')
  %w[crt-chain.o crt-forward.o crt-backward.o].each do |name|
    path = File.join(root, 'usr/lib', name)
    check(File.identical?(path, File.join(root, 'usr/lib/crt0.o')), 'forward hardlink lost inode identity: ' + name)
    check(File.binread(path) == startup && mode(path) == 0644, 'hardlink changed provider bytes or permissions')
    check(inventory.fetch('usr/lib/' + name).fetch('type') == 'hardlink', 'incorrect hardlink inventory')
  end
  unchanged.call
  check(inventory.fetch('usr/lib/libproc.so').fetch('mode') == 0755, 'shared symlink mode was changed')
  puts 'PASS: split sets preserve bytes, modes, directories, identical shared symlinks, aliases and forward hardlink chains'

  # Run hostile cases in their own process group. A regression must fail within
  # eight seconds and must not leave a blocked decompressor behind.
  library_path = File.expand_path('../sysroot-archive.rb', __dir__)
  child = <<~'RUBY'
    begin
      EmberSysrootArchive.extract(ARGV.drop(1), ARGV.fetch(0))
      warn 'Accepted invalid archive'
      exit 2
    rescue EmberSysrootArchive::Error => error
      warn error.message
      exit 0
    end
  RUBY
  refuse = lambda do |label, archives, expected, destination = File.join(dir, 'rejected-' + label)|
    Open3.popen3(RbConfig.ruby, '-r', library_path, '-e', child, '--', destination, *archives, pgroup: true) do |input, output, error, waiter|
      input.close
      begin
        stdout, stderr, status = Timeout.timeout(8) { [output.read, error.read, waiter.value] }
      rescue Timeout::Error
        begin
          Process.kill('KILL', -waiter.pid)
        rescue Errno::ESRCH
          # The process group already exited.
        end
        abort 'FAIL: extraction hung for ' + label
      ensure
        unchanged.call
      end
      check(status.success? && expected.match?(stderr), "#{label}: #{stdout}#{stderr}")
    end
    puts 'PASS: refuses ' + label
  end
  invalid = lambda do |label, entries, expected|
    path = write_xz(File.join(dir, label + '.tar.xz'), tar_bytes(entries))
    refuse.call(label, [path], expected)
  end
  invalid.call('traversal-member', [{name: '../outside-sentinel', data: 'changed'}], /Unsafe archive member/)
  invalid.call('absolute-member', [{name: sentinel, data: 'changed'}], /Unsafe archive member/)
  invalid.call('root-regular-file', [{name: '.', data: 'ignored bytes'}], /root must be a directory/)
  invalid.call('root-symlink', [{name: '.', type: '2', link: sentinel}], /root must be a directory/)
  invalid.call('root-device', [{name: '.', type: '3'}], /root must be a directory/)
  invalid.call('escaping-relative-symlink', [{name: 'usr/lib/escape', type: '2', link: '../../../outside-sentinel'}], /link escapes/)
  invalid.call('escaping-absolute-symlink', [{name: 'lib/escape', type: '2', link: '/../../outside-sentinel'}], /link escapes/)
  invalid.call('escaping-relative-hardlink', [{name: 'escape', type: '1', link: '../outside-sentinel'}], /Unsafe archive member/)
  invalid.call('escaping-absolute-hardlink', [{name: 'escape', type: '1', link: sentinel}], /Unsafe archive member/)
  # Lexically, alias/outside-link -> ../outside-sentinel stays in the target.
  # After alias -> '.', that same relative link would reach the outside file.
  invalid.call('symlink-below-directory-alias', [{name: 'alias', type: '2', link: '.'},
    {name: 'alias/outside-link', type: '2', link: '../outside-sentinel'}], /symlink parent/)
  rejected_root = File.join(dir, 'rejected-symlink-below-directory-alias')
  check(!File.symlink?(File.join(rejected_root, 'alias/outside-link')) &&
    !File.symlink?(File.join(rejected_root, 'outside-link')), 'refusal left an effective outside link')
  partial_alias = File.join(rejected_root, 'alias')
  check(!File.symlink?(partial_alias) || File.realpath(partial_alias) == rejected_root, 'partial alias points outside the target')
  invalid.call('duplicate-file', [{name: 'same', data: 'one'}, {name: 'same', data: 'two'}], /Duplicate non-directory/)
  invalid.call('duplicate-link', [{name: 'same', type: '2', link: 'target'}, {name: 'same', type: '2', link: 'other'}], /Duplicate non-directory/)
  invalid.call('identical-link-twice-in-one-archive', [{name: 'same', type: '2', link: 'target'},
    {name: 'same', type: '2', link: 'target'}], /Duplicate non-directory/)
  duplicate = write_xz(File.join(dir, 'duplicate-set.tar.xz'), tar_bytes([{name: 'lib/libc.so.12.229', data: 'other'}]))
  refuse.call('duplicate-between-sets', [base, duplicate], /Duplicate non-directory/)
  identical_file = write_xz(File.join(dir, 'identical-file.tar.xz'), tar_bytes([{name: 'lib/libc.so.12.229', data: library, mode: 0555}]))
  refuse.call('identical-file-between-sets', [base, identical_file], /Duplicate non-directory/)
  wrong_target = write_xz(File.join(dir, 'wrong-link-target.tar.xz'),
    tar_bytes([{name: 'usr/lib/libproc.so', type: '2', link: 'libproc.so.2.0', mode: 0755}]))
  refuse.call('shared-link-with-another-target', [base, wrong_target], /Duplicate non-directory/)
  wrong_mode = write_xz(File.join(dir, 'wrong-link-mode.tar.xz'),
    tar_bytes([{name: 'usr/lib/libproc.so', type: '2', link: 'libproc.so.1.0', mode: 0777}]))
  refuse.call('shared-link-with-another-mode', [base, wrong_mode], /Duplicate non-directory/)
  repeated_alias = write_xz(File.join(dir, 'repeated-shared-alias.tar.xz'), tar_bytes([
    {name: 'usr/lib/libproc.so', type: '2', link: 'libproc.so.1.0', mode: 0755},
    {name: 'usr/lib/libproc.so', type: '2', link: 'libproc.so.1.0', mode: 0755}]))
  refuse.call('shared-link-repeated-in-second-archive', [base, repeated_alias], /Duplicate non-directory/)
  identical_hardlink = write_xz(File.join(dir, 'identical-hardlink.tar.xz'),
    tar_bytes([{name: 'usr/lib/crt-forward.o', type: '1', link: './usr/lib/crt0.o'}]))
  refuse.call('identical-hardlink-between-sets', [base, identical_hardlink], /Duplicate non-directory/)
  invalid.call('unresolved-hardlink', [{name: 'alias', type: '1', link: 'missing'}], /Unresolved or cyclic/)
  invalid.call('cyclic-hardlinks', [{name: 'one', type: '1', link: 'two'}, {name: 'two', type: '1', link: 'one'}], /Unresolved or cyclic/)
  {'character-device' => '3', 'block-device' => '4', 'fifo' => '6', 'pax-extension' => 'x'}.each do |label, type|
    invalid.call('unsupported-' + label, [{name: 'unsupported', type: type}], /Unsupported archive entry/)
  end
  corrupt = File.join(dir, 'corrupt.tar.xz')
  bytes = File.binread(comp)
  bytes.setbyte(-1, bytes.getbyte(-1) ^ 0xff)
  File.binwrite(corrupt, bytes)
  refuse.call('corrupt-xz-trailer', [corrupt], /xz failed/)
  trailing = write_xz(File.join(dir, 'trailing-nonzero.tar.xz'), tar_bytes([], 'x' * 262_144))
  refuse.call('nonzero-trailing-data-without-hang', [trailing], /Nonzero data after tar end marker/)
  excessive = write_xz(File.join(dir, 'excessive-padding.tar.xz'), tar_bytes([], "\0" * (2 * 1024 * 1024)))
  refuse.call('excessive-zero-padding-without-hang', [excessive], /Excessive trailing tar padding/)
  refuse.call('existing-destination', [base], /fresh extraction directory/, root)
  unchanged.call
end
puts 'PASS: bounded archive extraction refusals preserve the outside sentinel'
