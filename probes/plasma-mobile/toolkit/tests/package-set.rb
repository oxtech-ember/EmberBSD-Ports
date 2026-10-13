#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Exercise the package-set auditor with pkgtools.
require 'digest'
require 'fileutils'
require 'open3'
require 'rbconfig'

abort 'Usage: package-set.rb NEW_OUTPUT' unless ARGV.length == 1
work = File.expand_path(ARGV.first)
Dir.mkdir(work)
create = ENV.fetch('PKG_CREATE', 'pkg_create')
info = ENV.fetch('PKG_INFO', 'pkg_info')
tar = ENV.fetch('BSDTAR', 'bsdtar')
auditor = File.expand_path('../cross/prepare-package-set.rb', __dir__)

def run!(*command)
  output, error, status = Open3.capture3(*command)
  raise "Command failed: #{command.inspect}\n#{output}#{error}" unless status.success?
  output
end

def pack(tar, tree, destination)
  names = Dir.chdir(tree) do
    Dir.glob('**/*', File::FNM_DOTMATCH).reject { |name| File.directory?(name) }.sort
  end
  names.delete('+CONTENTS')
  run!(tar, '-czf', destination, '--format=pax', '-C', tree, '+CONTENTS', *names)
end

payload = File.join(work, 'payload')
long_name = "share/pkgset/#{'a' * 90}/#{'b' * 90}/#{'c' * 90}/data"
long_link = "../../#{long_name}"
FileUtils.mkdir_p(File.dirname(File.join(payload, long_name)))
File.write(File.join(payload, long_name), "Pkgtools payload fixture\n")
File.link(File.join(payload, long_name), File.join(payload, 'share/pkgset/hardlink'))
File.symlink(long_link, File.join(payload, 'share/pkgset/symlink'))
File.write(File.join(payload, 'share/pkgset/root'), "Package root fixture\n")
File.write(File.join(work, 'comment'), "Package-set regression\n")
File.write(File.join(work, 'description'), "Package-set regression fixture. It is not a runtime acceptance package.\n")
File.write(File.join(work, 'build-info'), "OPSYS=NetBSD\nOS_VERSION=11.0\nMACHINE_ARCH=aarch64\nOBJECT_FMT=ELF\n")
cache = File.join(work, 'cache')
Dir.mkdir(cache)
{ 'pkgset-leaf-1.0' => [long_name, 'share/pkgset/hardlink', 'share/pkgset/symlink'],
  'pkgset-root-1.0' => ['share/pkgset/root'] }.each do |name, files|
  plist = File.join(work, "#{name}.plist")
  File.write(plist, files.join("\n") + "\n")
  command = [create, '-p', payload, '-I', '/usr/pkg', '-f', plist,
             '-c', File.join(work, 'comment'), '-d', File.join(work, 'description'),
             '-B', File.join(work, 'build-info')]
  command += ['-P', 'pkgset-leaf>=1.0'] if name == 'pkgset-root-1.0'
  run!(*command, File.join(cache, "#{name}.tgz"))
end
# Use pkg_create's actual metadata as an isolated installed database.
pkgdb = File.join(work, 'pkgdb')
Dir.mkdir(pkgdb)
Dir[File.join(cache, '*.tgz')].each do |archive|
  name = File.basename(archive, '.tgz')
  directory = File.join(pkgdb, name)
  Dir.mkdir(directory)
  run!(tar, '-tf', archive).lines.map(&:chomp).grep(/^\+/).each do |entry|
    File.binwrite(File.join(directory, entry), run!(tar, '-xOf', archive, entry))
  end
end
raise 'pkg_info did not resolve the real database' unless
  run!(info, '-K', pkgdb, '-e', 'pkgset-leaf>=1.0') == "pkgset-leaf-1.0\n"
leaf = File.join(cache, 'pkgset-leaf-1.0.tgz')
root = File.join(cache, 'pkgset-root-1.0.tgz')
index = File.join(work, 'archives.txt')
count = 0
check_case = lambda do |name, database, leaf_archive, expected|
  File.write(index, (Array(leaf_archive) + [root]).join("\n") + "\n")
  destination = File.join(work, "set-#{name}")
  output, error, status = Open3.capture3({ 'PKG_INFO' => info, 'BSDTAR' => tar },
                                      RbConfig.ruby, auditor, database, index, destination, 'pkgset-root-1.0')
  File.write(File.join(work, "#{name}.log"), output + error)
  if expected.nil?
    raise "#{name} failed: #{output}#{error}" unless status.success?
    raise 'Wrong dependency installation order' unless
      File.read(File.join(destination, 'install-order.txt')) == "pkgset-leaf-1.0.tgz\npkgset-root-1.0.tgz\n"
    File.readlines(File.join(destination, 'packages.sha256')).each do |line|
      sha, file = line.split
      raise "Bad copied SHA256 #{file}" unless Digest::SHA256.file(File.join(destination, file)).hexdigest == sha
    end
    [leaf, root].each do |original|
      copy = File.join(destination, 'packages', File.basename(original))
      raise 'Copied archive differs' unless FileUtils.compare_file(original, copy)
    end
  else
    raise "#{name} did not reject the cause: #{output}#{error}" if status.success? || !(output + error).include?(expected)
    raise "Failed audit left an accepted output: #{destination}" if File.exist?(destination)
  end
  raise 'Failed audit left staging files' unless Dir[File.join(work, ".set-#{name}-*")].empty?
  count += 1
  puts "PASS: #{name}"
end
check_case.call('valid-pax-hardlink-symlink', pkgdb, leaf, nil)
mutate = lambda do |name, expected, &block|
  directory = File.join(work, name)
  tree = File.join(directory, 'tree')
  FileUtils.mkdir_p(tree)
  run!(tar, '-xf', leaf, '-C', tree)
  block.call(tree)
  archive = File.join(directory, 'pkgset-leaf-1.0.tgz')
  pack(tar, tree, archive)
  check_case.call(name, pkgdb, archive, expected)
end
mutate.call('stale-manifest', 'No archive with the installed manifest') do |tree|
  File.open(File.join(tree, '+CONTENTS'), 'a') { |file| file.puts('@comment stale-recipe') }
end
mutate.call('wrong-architecture', 'Wrong target MACHINE_ARCH') do |tree|
  path = File.join(tree, '+BUILD_INFO')
  File.write(path, File.read(path).sub('MACHINE_ARCH=aarch64', 'MACHINE_ARCH=x86_64'))
end
mutate.call('wrong-os-abi', 'Wrong target OS_VERSION') do |tree|
  path = File.join(tree, '+BUILD_INFO')
  File.write(path, File.read(path).sub('OS_VERSION=11.0', 'OS_VERSION=10.0'))
end
mutate.call('corrupt-payload', 'Archive payload mismatch') do |tree|
  File.write(File.join(tree, long_name), "Changed bytes with unchanged manifest\n")
end
mutate.call('changed-symlink', 'Archive payload mismatch') do |tree|
  path = File.join(tree, 'share/pkgset/symlink')
  File.unlink(path)
  File.symlink('wrong-target', path)
end
mutate.call('missing-payload', 'Missing archive member') do |tree|
  File.unlink(File.join(tree, long_name))
end
mutate.call('unlisted-payload', 'Unlisted archive member') do |tree|
  File.write(File.join(tree, 'share/pkgset/unlisted'), "not in manifest\n")
end
mutate.call('changed-metadata', 'Archive metadata mismatch +DESC') do |tree|
  File.chmod(0644, File.join(tree, '+DESC'))
  File.write(File.join(tree, '+DESC'), "Different description\n")
end
# A stale copy must not hide a later cache archive that passes the full audit.
check_case.call('valid-after-stale-cache-copy', pkgdb,
                [File.join(work, 'wrong-architecture/pkgset-leaf-1.0.tgz'), leaf], nil)
missing_db = File.join(work, 'missing-dependency-db')
FileUtils.cp_r(pkgdb, missing_db)
FileUtils.rm_r(File.join(missing_db, 'pkgset-leaf-1.0'))
check_case.call('missing-dependency', missing_db, leaf, 'Unresolved or ambiguous dependency')
truncated = File.join(work, 'truncated')
Dir.mkdir(truncated)
truncated_leaf = File.join(truncated, 'pkgset-leaf-1.0.tgz')
File.binwrite(truncated_leaf, File.binread(leaf)[0, File.size(leaf) / 2])
check_case.call('truncated-archive', pkgdb, truncated_leaf, 'No archive with the installed manifest')
# An existing accepted output is never replaced.
File.write(index, [leaf, root].join("\n") + "\n")
accepted = File.join(work, 'set-valid-pax-hardlink-symlink')
before = File.read(File.join(accepted, 'packages.sha256'))
output, error, status = Open3.capture3({ 'PKG_INFO' => info, 'BSDTAR' => tar }, RbConfig.ruby,
                                    auditor, pkgdb, index, accepted, 'pkgset-root-1.0')
raise 'Existing output was not rejected' if status.success? || !(output + error).include?('Output already exists')
raise 'Existing output changed' unless before == File.read(File.join(accepted, 'packages.sha256'))
count += 1
puts 'PASS: preserve-existing-output'
puts "PASS: #{count} package-set cases with actual pkg_create/pkg_info and archive payloads"
