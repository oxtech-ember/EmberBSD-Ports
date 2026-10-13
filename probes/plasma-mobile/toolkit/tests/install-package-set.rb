#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Check the installer with real pkgtools archives.
require 'digest'
require 'fileutils'
require 'open3'

abort 'Usage: install-package-set.rb NEW_OUTPUT' unless ARGV.length == 1
work = File.expand_path(ARGV[0])
Dir.mkdir(work)
create = ENV.fetch('PKG_CREATE', 'pkg_create')
info = ENV.fetch('PKG_INFO', 'pkg_info')
admin = ENV.fetch('PKG_ADMIN', 'pkg_admin')
add = ENV.fetch('PKG_ADD', 'pkg_add')
installer = File.expand_path('../cross/install-package-set.sh', __dir__)
def run!(*command)
  out, err, status = Open3.capture3(*command)
  raise "Command failed: #{command.inspect}\n#{out}#{err}" unless status.success?
  out
end
payload = File.join(work, 'payload')
FileUtils.mkdir_p(File.join(payload, 'share', 'installer-test'))
File.write(File.join(work, 'comment'), "Installer regression\n")
File.write(File.join(work, 'description'), "Data-only pkgtools fixture. Not a desktop runtime test.\n")
File.write(File.join(work, 'build-info'), "OPSYS=NetBSD\nOS_VERSION=11.0\nMACHINE_ARCH=aarch64\nOBJECT_FMT=ELF\n")
valid = File.join(work, 'valid')
FileUtils.mkdir_p(File.join(valid, 'packages'))
names = %w[installer-leaf-1.0 installer-root-1.0]
names.each do |name|
  file = "share/installer-test/#{name}"
  File.write(File.join(payload, file), "#{name}\n")
  plist = File.join(work, "#{name}.plist")
  File.write(plist, "#{file}\n")
  command = [create, '-p', payload, '-I', '/usr/pkg', '-f', plist,
             '-c', File.join(work, 'comment'), '-d', File.join(work, 'description'),
             '-B', File.join(work, 'build-info')]
  command += ['-P', 'installer-leaf>=1.0'] if name == names.last
  run!(*command, File.join(valid, 'packages', "#{name}.tgz"))
end
File.write(File.join(valid, 'install-order.txt'), names.map { |name| "#{name}.tgz\n" }.join)
File.write(File.join(valid, 'roots.txt'), "#{names.last}\n")
File.write(File.join(valid, 'packages.sha256'), names.map do |name|
  "#{Digest::SHA256.file(File.join(valid, 'packages', "#{name}.tgz")).hexdigest}  packages/#{name}.tgz\n"
end.join)
env = { 'PKG_INFO' => info, 'PKG_ADMIN' => admin, 'PKG_ADD' => add }
count = 0
check = lambda do |name, directory, expected = nil, install = false|
  log = File.join(work, "#{name}-install.log")
  command = ['sh', installer]
  command += install ? ['--install', directory, log] : [directory]
  out, err, status = Open3.capture3(env, *command)
  File.write(File.join(work, "#{name}.log"), out + err)
  if expected
    raise "#{name} did not reject the cause: #{out}#{err}" if status.success? || !(out + err).include?(expected)
  else
    raise "#{name} failed: #{out}#{err}" unless status.success?
    raise 'Verification did not check dependency order' unless out.include?('2 archives, SHA256, target metadata, roots and dependency order verified')
  end
  raise "#{name} reached the installation mutation" if File.exist?(log)
  count += 1
  puts "PASS: #{name}"
end
check.call('default-verify', valid)
mutate = lambda do |name, error, &block|
  directory = File.join(work, name)
  FileUtils.cp_r(valid, directory)
  block.call(directory)
  check.call(name, directory, error)
  check.call("#{name}-before-install", directory, error, true) if RUBY_PLATFORM.include?('darwin')
end
mutate.call('corrupt-hash', 'SHA256 mismatch') do |directory|
  File.open(File.join(directory, 'packages', "#{names.first}.tgz"), 'ab') { |file| file.write('changed') }
end
mutate.call('missing-archive', 'Package directory and installation manifest differ') do |directory|
  File.unlink(File.join(directory, 'packages', "#{names.first}.tgz"))
end
mutate.call('reversed-order', 'Invalid dependency order') do |directory|
  File.write(File.join(directory, 'install-order.txt'), names.reverse.map { |name| "#{name}.tgz\n" }.join)
end
mutate.call('duplicate-order', 'Invalid or duplicate install-order') do |directory|
  File.open(File.join(directory, 'install-order.txt'), 'a') { |file| file.puts("#{names.first}.tgz") }
end
mutate.call('extra-archive', 'Package directory and installation manifest differ') do |directory|
  FileUtils.cp(File.join(directory, 'packages', "#{names.first}.tgz"), File.join(directory, 'packages', 'unlisted-1.0.tgz'))
end
mutate.call('missing-root', 'Invalid, missing or duplicate root') do |directory|
  File.write(File.join(directory, 'roots.txt'), "missing-root-1.0\n")
end
mutate.call('unfinished-manifest', 'Manifest needs a final newline') do |directory|
  path = File.join(directory, 'packages.sha256')
  File.write(path, File.read(path).chomp)
end
mutate.call('archive-symlink', 'Not a regular package archive') do |directory|
  path = File.join(directory, 'packages', "#{names.first}.tgz")
  File.unlink(path)
  File.symlink(File.join(valid, 'packages', "#{names.first}.tgz"), path)
end
if RUBY_PLATFORM.include?('darwin')
  check.call('host-install-rejected', valid, 'Installation requires an EmberBSD target', true)
end
# Exercise the exact production helper with native, data-only packages in
# private prefixes. The control proves that the parent's 077 mask is harmful.
helper = File.read(installer)[/^install_archive\(\) \{\n.*?^\}/m]
raise 'Missing production install helper' unless helper
raise 'Install loop does not call the umask helper' unless File.read(installer).include?('install_archive "$bundle/packages/$archive"')
host_metadata = run!(info, '-q', '-B', ENV.fetch('PKG_HOST_SAMPLE', 'digest')).lines.grep(/^(OPSYS|OS_VERSION|MACHINE_ARCH|OBJECT_FMT)=/).join
raise 'Incomplete native package metadata' unless host_metadata.lines.length == 4
native_info = File.join(work, 'native-build-info')
File.write(native_info, host_metadata)
native_name = 'installer-mask-1.0'
native_file = 'share/installer-mask/nested/data'
FileUtils.mkdir_p(File.dirname(File.join(payload, native_file)))
File.write(File.join(payload, native_file), "umask acceptance\n")
native_plist = File.join(work, 'native.plist')
File.write(native_plist, "#{native_file}\n")
native_archive = File.join(work, "#{native_name}.tgz")
native_script = File.join(work, 'native-install.sh')
File.write(native_script, "#!/bin/sh\nset -eu\ncase $2 in POST-INSTALL) printf 'install script ran\n' > \"$PKG_PREFIX/share/installer-mask/script-ran\" ;; esac\n")
run!(create, '-p', payload, '-I', '/usr/pkg', '-f', native_plist,
     '-c', File.join(work, 'comment'), '-d', File.join(work, 'description'),
     '-B', native_info, '-i', native_script, native_archive)
%w[control fixed].each do |label|
  area = File.join(work, "umask-#{label}")
  prefix = File.join(area, 'prefix')
  database = File.join(area, 'pkgdb')
  FileUtils.mkdir_p([prefix, database])
  config = File.join(area, 'pkg_install.conf')
  File.write(config, "PKG_DBDIR=#{database}\nPKG_REFCOUNT_DBDIR=#{area}/refcount\n")
  script = File.join(area, 'run.sh')
  body = "#!/bin/sh\nset -eu\numask 077\nadd=$1\nshift\n"
  body += label == 'fixed' ? "#{helper}\ninstall_archive \"$@\"\n" : "\"$add\" -U \"$@\"\n"
  File.write(script, body)
  out, err, status = Open3.capture3('sh', script, add, '-C', config, '-K', database, '-p', prefix, native_archive)
  File.write(File.join(area, 'install.log'), out + err)
  raise "Private native installation failed: #{out}#{err}" unless status.success?
  directory = File.join(prefix, 'share', 'installer-mask', 'nested')
  mode = File.stat(directory).mode & 0777
  raise "Negative umask control did not create 0700: #{mode.to_s(8)}" if label == 'control' && mode != 0700
  raise "Production helper did not create 0755: #{mode.to_s(8)}" if label == 'fixed' && mode != 0755
  raise 'Installed private payload differs' unless File.binread(File.join(prefix, native_file)) == "umask acceptance\n"
  raise 'Package install script was skipped' unless File.read(File.join(prefix, 'share/installer-mask/script-ran')) == "install script ran\n"
  run!(admin, '-C', config, '-K', database, 'check', native_name)
  count += 1
  puts "PASS: native-umask-#{label} (#{mode.to_s(8)})"
end
puts "PASS: #{count} installer checks with native pkg_create/pkg_info/pkg_admin and real package archives; no target installation (native umask fixtures use private prefixes)"
