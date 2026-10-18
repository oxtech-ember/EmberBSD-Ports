#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Prepare a private coherent target execution guest.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
require 'shellwords'
require 'zlib'
require_relative 'resources'
abort 'usage: build.rb BASE KERNEL_GZ OS_REPOSITORY NETBSD_TOOLS NEW_WORK' unless ARGV.size == 5
abort 'simple absolute paths required' unless ARGV.all? { |p| p.match?(%r{\A/[A-Za-z0-9_./+-]+\z}) }
base, kernel, source, tools, work = ARGV.map { |p| File.expand_path(p) }
abort 'work exists' if File.exist?(work) || File.symlink?(work)
revision = ENV.fetch('EMBERBSD_BASE_REVISION')
kernel_hash = ENV.fetch('EMBERBSD_KERNEL_SHA256')
abort 'invalid source revision' unless revision.match?(/\A[0-9a-f]{40}\z/)
abort 'kernel hash mismatch' unless kernel_hash.match?(/\A[0-9a-f]{64}\z/) && Digest::SHA256.file(kernel).hexdigest == kernel_hash
port = Integer(ENV.fetch('EMBERBSD_QUERY_PORT', '22614'), 10)
disk_mib = Integer(ENV.fetch('EMBERBSD_QUERY_DISK_MIB', '384'), 10)
free_inodes = Integer(ENV.fetch('EMBERBSD_QUERY_FREE_INODES', '16000'), 10)
begin
  ram_mib = QueryVmResources.ram_mib(ENV.fetch('EMBERBSD_QUERY_RAM_MIB', QueryVmResources::DEFAULT_RAM_MIB))
rescue ArgumentError => error
  abort error.message
end
abort 'invalid unprivileged SSH port' unless (1024..65535).cover?(port)
abort 'disk must be 384..16384 MiB' unless (384..16384).cover?(disk_mib)
abort 'inode reserve must be 16000..1000000' unless (16000..1000000).cover?(free_inodes)
FileUtils.mkdir_p(work, mode: 0700)
%w[root keys logs artifacts bin cache probes source].each { |d| FileUtils.mkdir_p(work + '/' + d, mode: 0700) }
root = work + '/root'
run = lambda do |name, *command, **options|
  stdout, stderr, status = Open3.capture3(*command, **options)
  File.write(work + '/logs/' + name + '.log', stdout + stderr)
  abort "#{name} failed: #{status.exitstatus}" unless status.success?
  stdout
end
# Read configuration and device definitions from the accepted fork revision.
source_files = %w[etc/group etc/master.passwd etc/services etc/protocols etc/MAKEDEV.awk etc/MAKEDEV.tmpl
  etc/etc.aarch64/MAKEDEV.conf sys/conf/majors sys/arch/aarch64/conf/majors.aarch64
  sys/arch/aarch64/include/disklabel.h sys/arch/arm/include/disklabel.h sys/arch/evbarm/conf/mk.generic64]
source_hashes = {}
source_files.each do |relative|
  content = run.call('source-' + relative.tr('/', '-'), 'git', '-C', source, 'show', revision + ':' + relative)
  path = work + '/source/' + relative
  FileUtils.mkdir_p(File.dirname(path))
  File.write(path, content)
  source_hashes[relative] = Digest::SHA256.hexdigest(content)
end
make_env = {'MACHINE'=>'aarch64', 'MACHINE_ARCH'=>'aarch64', 'NETBSDSRCDIR'=>work + '/source'}
makedev = run.call('makedev-generate', make_env, 'awk', '-f', work + '/source/etc/MAKEDEV.awk', work + '/source/etc/MAKEDEV.tmpl')
File.write(work + '/artifacts/MAKEDEV', makedev)
devices = run.call('makedev-spec', 'sh', work + '/artifacts/MAKEDEV', '-s', 'std', 'fd', 'ptm', 'ld4', 'plcom0', chdir: work + '/artifacts')
abort 'canonical ptmx major/minor absent' unless devices.match?(/ptmx.*device=netbsd,165,0/)
File.write(work + '/artifacts/devices.mtree', devices)
origins = {kernel=>kernel_hash}
copy_base = lambda do |relative|
  input = base + '/' + relative
  output = root + '/' + relative
  FileUtils.mkdir_p(File.dirname(output), mode: 0755)
  if File.symlink?(input)
    File.symlink(File.readlink(input), output)
    origins[input] = {symlink: File.readlink(input)}
  elsif File.file?(input)
    File.link(input, output)
    origins[input] = Digest::SHA256.file(input).hexdigest
  else
    abort "missing base file: #{input}"
  end
end
%w[lib libexec usr/lib/i18n usr/share/i18n usr/share/locale].each do |directory|
  abort "missing base runtime directory: #{directory}" unless File.directory?(base + '/' + directory)
  Dir.glob(base + '/' + directory + '/**/*').sort.each do |path|
    next if File.directory?(path) && !File.symlink?(path)
    next if path.end_with?('.a')
    copy_base.call(path.delete_prefix(base + '/'))
  end
end
Dir.glob(base + '/usr/lib/*.so*').sort.each { |p| copy_base.call(p.delete_prefix(base + '/')) }
Dir.glob(base + '/usr/lib/private/*.so*').sort.each { |p| copy_base.call(p.delete_prefix(base + '/')) }
%w[
  bin/sh bin/sync bin/cat bin/chmod bin/cp bin/ls bin/mkdir bin/rm bin/test
  bin/date bin/tar bin/sleep bin/stty bin/hostname bin/kill bin/df bin/pwd bin/ps
  sbin/init sbin/mount sbin/mount_ffs sbin/mount_ptyfs sbin/halt sbin/reboot
  sbin/sysctl sbin/ifconfig sbin/route sbin/nologin
  usr/bin/uname usr/bin/grep usr/bin/sha256 usr/bin/ldd usr/bin/sed usr/bin/awk
  usr/bin/env usr/bin/printf usr/bin/timeout usr/bin/mktemp usr/bin/id usr/bin/tty
  usr/bin/getent usr/bin/true usr/bin/false usr/bin/du usr/bin/locale
  usr/bin/sort usr/bin/realpath usr/bin/wc usr/bin/tr usr/bin/dirname usr/bin/basename
  usr/bin/ktrace usr/bin/kdump usr/bin/fstat
  usr/sbin/pkg_add usr/sbin/pkg_delete usr/sbin/pkg_info usr/sbin/pkg_admin
  usr/sbin/sshd usr/libexec/sshd-session usr/libexec/sshd-auth usr/libexec/sftp-server
  usr/libexec/ld.elf_so
].each { |path| copy_base.call(path) }
%w[etc etc/ssh dev dev/pts tmp var/run var/log var/chroot/sshd var/empty root root/.ssh usr/pkg/lib].each do |directory|
  FileUtils.mkdir_p(root + '/' + directory, mode: 0755)
end
File.chmod(01777, root + '/tmp')
File.chmod(0700, root + '/root/.ssh')
%w[group master.passwd services protocols].each { |name| FileUtils.cp(work + '/source/etc/' + name, root + '/etc/' + name) }
run.call('password-database', tools + '/nbpwd_mkdb', '-d', root, '-p', root + '/etc/master.passwd')
%w[client host].each do |name|
  run.call('keygen-' + name, 'ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'emberbsd-query-' + name, '-f', work + '/keys/' + name)
end
FileUtils.cp(work + '/keys/host', root + '/etc/ssh/ssh_host_ed25519_key')
FileUtils.cp(work + '/keys/host.pub', root + '/etc/ssh/ssh_host_ed25519_key.pub')
FileUtils.cp(work + '/keys/client.pub', root + '/root/.ssh/authorized_keys')
File.chmod(0600, root + '/etc/ssh/ssh_host_ed25519_key', root + '/root/.ssh/authorized_keys')
key_type, key_data = File.read(work + '/keys/host.pub').split[0,2]
File.write(work + '/keys/known_hosts', "ember-e14-query #{key_type} #{key_data}\n", mode: 'w', perm: 0600)
File.write(work + '/ssh.conf', <<~CONFIG, mode: 'w', perm: 0600)
  Host ember-e14-query
    HostName 127.0.0.1
    Port #{port}
    User root
    IdentityFile #{work}/keys/client
    IdentitiesOnly yes
    UserKnownHostsFile #{work}/keys/known_hosts
    GlobalKnownHostsFile /dev/null
    HostKeyAlias ember-e14-query
    StrictHostKeyChecking yes
    BatchMode yes
    ConnectTimeout 5
    ServerAliveInterval 10
    ServerAliveCountMax 3
CONFIG
File.write(work + '/bin/ssh', "#!/bin/sh\nexec /usr/bin/ssh -F #{(work + '/ssh.conf').shellescape} \"$@\"\n", mode: 'w', perm: 0755)
File.write(root + '/etc/ssh/sshd_config', <<~CONFIG)
  Port 22
  ListenAddress 10.0.2.15
  HostKey /etc/ssh/ssh_host_ed25519_key
  PidFile /var/run/sshd.pid
  AuthorizedKeysFile .ssh/authorized_keys
  PermitRootLogin prohibit-password
  PasswordAuthentication no
  PermitEmptyPasswords no
  KbdInteractiveAuthentication no
  PubkeyAuthentication yes
  UsePAM no
  UseDNS no
  PrintMotd no
  Subsystem sftp /usr/libexec/sftp-server
CONFIG
File.write(root + '/etc/fstab', "/dev/ld4a / ffs rw 1 1\n")
File.write(root + '/etc/ttys', "console \"/bin/sh\" vt100 off secure\n")
File.write(root + '/etc/hosts', "127.0.0.1 localhost\n10.0.2.15 ember-query\n")
File.write(root + '/etc/resolv.conf', "nameserver 10.0.2.3\n")
File.write(root + '/etc/nsswitch.conf', "group: files\npasswd: files\nhosts: files dns\n")
FileUtils.cp(File.join(__dir__, 'guest-rc.sh'), root + '/etc/rc')
File.chmod(0755, root + '/etc/rc')
mtree = "/set uid=0 gid=0\n" + run.call('mtree', tools + '/nbmtree', '-c', '-k', 'type,mode,link', '-p', root)
mtree << devices.lines.reject { |line| line.start_with?('. type=dir') }.map { |line| line.sub(%r{\A\./}, './dev/') }.join
File.write(work + '/artifacts/guest.mtree', mtree)
run.call('makefs', tools + '/nbmakefs', '-t', 'ffs', '-B', 'little', '-Z', '-s', "#{disk_mib}m",
         '-o', 'version=2,label=emberquery', '-f', free_inodes.to_s, '-F', work + '/artifacts/guest.mtree',
         '-N', work + '/source/etc', work + '/query.ffs', root)
Zlib::GzipReader.open(kernel) { |input| File.open(work + '/artifacts/kernel.elf', 'wb') { |output| IO.copy_stream(input, output) } }
run.call('kernel-binary', tools + '/aarch64--netbsd-objcopy', '-S', '-O', 'binary', work + '/artifacts/kernel.elf', work + '/artifacts/kernel.bin')
run.call('kernel-arm64-image', tools + '/nbmkubootimage', '-f', 'arm64', '-u', '-a', '0x200000', work + '/artifacts/kernel.bin', work + '/artifacts/kernel.img')
abort 'base input changed during build' unless origins.all? do |path, value|
  value.is_a?(Hash) ? File.symlink?(path) && File.readlink(path) == value.fetch(:symlink) : Digest::SHA256.file(path).hexdigest == value
end
manifest = {base_revision: revision, base: base, port: port, ram_mib: ram_mib, disk_bytes: File.size(work + '/query.ffs'),
            sparse_disk: true, allocated_disk_bytes: File.stat(work + '/query.ffs').blocks * 512,
            extra_free_inodes: free_inodes, initial_disk_sha256: Digest::SHA256.file(work + '/query.ffs').hexdigest,
            kernel_image_sha256: Digest::SHA256.file(work + '/artifacts/kernel.img').hexdigest,
            sources_sha256: origins, configuration_sources_sha256: source_hashes}
File.write(work + '/artifacts/input.json', JSON.pretty_generate(manifest) + "\n")
puts "Prepared private #{disk_mib} MiB sparse target guest: #{work}"
