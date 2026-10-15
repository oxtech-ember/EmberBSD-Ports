#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Audit package scripts without executing them.
require 'digest'
require 'fileutils'
require 'open3'
require 'rbconfig'

abort 'Usage: package-install-scripts.rb NEW_OUTPUT [AUDITOR]' unless (1..2).cover?(ARGV.length)
work = File.expand_path(ARGV[0])
auditor = File.expand_path(ARGV[1] || '../cross/prepare-package-set.rb', __dir__)
Dir.mkdir(work)
create = ENV.fetch('PKG_CREATE', 'pkg_create')
info = ENV.fetch('PKG_INFO', 'pkg_info')
tar = ENV.fetch('BSDTAR', 'bsdtar')
payload = File.join(work, 'payload')
FileUtils.mkdir_p(payload)
File.write(File.join(payload, 'data'), "Target package payload\n")
File.write(File.join(work, 'plist'), "data\n")
File.write(File.join(work, 'comment'), "Serialized package script test\n")
File.write(File.join(work, 'description'), "This fixture never runs a package script.\n")
File.write(File.join(work, 'build-info'), <<~INFO)
  OPSYS=NetBSD
  OS_VERSION=11.0
  MACHINE_ARCH=aarch64
  OBJECT_FMT=ELF
  BUILD_HOST=/private/tmp/build-host
  CC=/Volumes/build/compiler/bin/cc
INFO

def run!(*command)
  out, err, status = Open3.capture3(*command)
  raise "Failed #{command.inspect}\n#{out}#{err}" unless status.success?
  out
end

# Observe the real auditor's copy call. A rejected archive must not reach it.
copy_observer = File.join(work, 'copy-observer.rb')
File.write(copy_observer, <<~'RUBY')
  require 'fileutils'
  module FileUtils
    class << self
      alias_method :observed_original_cp, :cp
      def cp(source, destination, *args)
        File.open(ENV.fetch('PKGSET_COPY_LOG'), 'a') { |log| log.puts(source) }
        observed_original_cp(source, destination, *args)
      end
    end
  end
RUBY
script_ran = File.join(work, 'script-was-executed')
# These literal assignments follow pkgsrc mk/pkginstall/header 1.3, as
# serialized in the Python 3.15 package. The paths below are target examples.
target_header = <<~'SCRIPT'
  #!/bin/sh
  SELF="$0"
  PKGNAME="$1"
  STAGE="$2"
  shift 2
  AWK="/usr/bin/awk"
  SED="/usr/bin/sed"
  SH="/bin/sh"
  SORT="/usr/bin/sort"
  LINKFARM="/usr/sbin/linkfarm"
  PKG_ADMIN="/usr/sbin/pkg_admin"
  PKG_INFO="/usr/pkg/sbin/pkg_info"
  MKDIR="/bin/mkdir -p"
  ECHO_N="echo -n"
  TRUE="true"
  GTAR=""
  PREFIX="/usr/pkg"
  PKG_SYSCONFDIR="/etc/example"
SCRIPT
target_header += "printf unexpected > #{script_ran}\n"
count = 0
check_case = lambda do |name, scripts, expected, prefix = '/usr/pkg', archive_only = nil|
  directory = File.join(work, name)
  FileUtils.mkdir_p(directory)
  command = [create, '-p', payload, '-I', prefix, '-f', File.join(work, 'plist'),
             '-c', File.join(work, 'comment'), '-d', File.join(work, 'description'),
             '-B', File.join(work, 'build-info')]
  flags = { '+INSTALL' => '-i', '+DEINSTALL' => '-k' }
  scripts.each do |entry, source|
    path = File.join(directory, entry)
    File.write(path, source)
    command += [flags.fetch(entry), path] if flags.key?(entry)
  end
  archive = File.join(directory, 'pkgset-scripts-1.0.tgz')
  run!(*command, archive)
  # Current pkg_create advertises -r but has no switch case for it. Exercise
  # the retained +REQUIRE metadata form without executing or inventing a tool.
  if scripts.key?('+REQUIRE')
    tree = File.join(directory, 'require-tree')
    Dir.mkdir(tree)
    run!(tar, '-xf', archive, '-C', tree)
    contents = File.join(tree, '+CONTENTS')
    File.chmod(0644, contents)
    File.open(contents, 'a') { |file| file.write("@ignore\n+REQUIRE\n") }
    File.write(File.join(tree, '+REQUIRE'), scripts.fetch('+REQUIRE'))
    names = Dir.children(tree).sort - ['+CONTENTS']
    run!({ 'COPYFILE_DISABLE' => '1' }, tar, '-czf', archive, '-C', tree, '+CONTENTS', *names)
  end
  metadata = File.join(directory, 'pkgdb/pkgset-scripts-1.0')
  FileUtils.mkdir_p(metadata)
  names = run!(tar, '-tf', archive).lines.map(&:chomp).grep(/^\+/)
  names.each do |entry|
    File.binwrite(File.join(metadata, entry), run!(tar, '-xOf', archive, entry))
  end
  if archive_only
    tree = File.join(directory, 'archive-tree')
    Dir.mkdir(tree)
    run!(tar, '-xf', archive, '-C', tree)
    path = File.join(tree, '+INSTALL')
    File.chmod(0644, path)
    File.write(path, archive_only)
    run!({ 'COPYFILE_DISABLE' => '1' }, tar, '-czf', archive, '-C', tree, '+CONTENTS',
         *(names - ['+CONTENTS']), 'data')
  end
  index = File.join(directory, 'archives.txt')
  File.write(index, archive + "\n")
  destination = File.join(directory, 'set')
  copy_log = File.join(directory, 'copies.log')
  output, error, status = Open3.capture3(
    { 'PKG_INFO' => info, 'BSDTAR' => tar, 'PKGSET_COPY_LOG' => copy_log },
    RbConfig.ruby, '-r', copy_observer, auditor, File.dirname(metadata), index,
    destination, 'pkgset-scripts-1.0')
  File.write(File.join(directory, 'audit.log'), output + error)
  if expected
    raise "#{name}: cause not rejected: #{output}#{error}" if status.success? || !(output + error).include?(expected)
    raise "#{name}: rejected archive was copied" if File.exist?(copy_log)
    raise "#{name}: rejected output exists" if File.exist?(destination)
  else
    raise "#{name}: valid script rejected: #{output}#{error}" unless status.success?
    raise "#{name}: no archive was copied" unless File.readlines(copy_log).length == 1
    copy = File.join(destination, 'packages/pkgset-scripts-1.0.tgz')
    raise "#{name}: archive differs" unless Digest::SHA256.file(copy).hexdigest == Digest::SHA256.file(archive).hexdigest
  end
  raise 'A package script was executed' if File.exist?(script_ran)
  raise "#{name}: staging remained" unless Dir[File.join(directory, '.set-*')].empty?
  count += 1
  puts "PASS: #{name}"
end

check_case.call('valid-target-scripts-and-build-history',
                %w[+INSTALL +DEINSTALL +REQUIRE].to_h { |name| [name, target_header] }, nil)
check_case.call('valid-nondefault-prefix',
                { '+INSTALL' => target_header + "PERL5='/opt/device/bin/perl -w'\n" }, nil, '/opt/device')
check_case.call('valid-local-and-x11-prefixes',
                { '+INSTALL' => target_header + "PERL5=/usr/local/bin/perl\nMKFONTDIR=/usr/X11R7/bin/mkfontdir\n" }, nil)
%w[+INSTALL +DEINSTALL +REQUIRE].each do |name|
  check_case.call("host-shebang-#{name.delete_prefix('+').downcase}",
                  { name => target_header.sub('#!/bin/sh', '#!/private/tmp/native/bin/mksh') },
                  'Host path in package script')
end
{
  'AWK' => '/private/tmp/native/bin/nawk', 'SED' => '/Volumes/build/native/bin/nbsed',
  'PKG_ADMIN' => '/Users/builder/native/sbin/pkg_admin',
  'LINKFARM' => '/opt/homebrew/sbin/linkfarm', 'SORT' => '/var/folders/build/native/bin/sort'
}.each do |helper, path|
  check_case.call("host-helper-#{helper.downcase}", { '+INSTALL' => target_header + "#{helper}=\"#{path}\"\n" },
                  'Host path in package script')
end
check_case.call('unquoted-host-helper', { '+DEINSTALL' => target_header + "SED=/tmp/native/bin/sed\n" },
                'Host path in package script')
check_case.call('single-quoted-host-helper', { '+REQUIRE' => target_header + "AWK='/private/tmp/native/bin/awk -F :'\n" },
                'Host path in package script')
check_case.call('dot-component-host-helper', { '+INSTALL' => target_header + "SH=/usr/bin/../../private/tmp/native/bin/sh\n" },
                'Host path in package script')
check_case.call('non-target-helper-prefix', { '+INSTALL' => target_header + "PKG_INFO=/build/native/sbin/pkg_info\n" },
                'Non-target executable in package script')
check_case.call('embedded-helper-shebang',
                { '+INSTALL' => target_header + "cat <<'HELPER'\n#!/private/tmp/native/bin/mksh\nHELPER\n" },
                'Host path in package script')
check_case.call('embedded-helper-assignment',
                { '+INSTALL' => target_header + "cat <<'HELPER'\n#!/bin/sh\nAWK=/Volumes/build/native/bin/awk\nHELPER\n" },
                'Host path in package script')
check_case.call('env-wrapped-host-helper',
                { '+INSTALL' => target_header + "SH='/usr/bin/env /private/tmp/native/bin/sh'\n" },
                'Host path in package script')
check_case.call('target-prefix-boundary', { '+INSTALL' => target_header + "SH=/usr/pkg-host/bin/sh\n" },
                'Non-target executable in package script')
check_case.call('archive-metadata-change-before-copy', { '+INSTALL' => target_header },
                'Archive metadata mismatch +INSTALL', '/usr/pkg',
                target_header.sub('#!/bin/sh', '#!/private/tmp/native/bin/mksh'))

if ENV['PYTHON_PACKAGE_SCRIPT']
  original = File.binread(ENV.fetch('PYTHON_PACKAGE_SCRIPT'))
  File.write(File.join(work, 'python-script.sha256'), Digest::SHA256.hexdigest(original) + "\n")
  check_case.call('actual-python315-serialized-script', { '+INSTALL' => original }, 'Host path in package script')
end
if ENV['TARGET_PACKAGE_SCRIPT']
  original = File.binread(ENV.fetch('TARGET_PACKAGE_SCRIPT'))
  File.write(File.join(work, 'target-script.sha256'), Digest::SHA256.hexdigest(original) + "\n")
  check_case.call('actual-repaired-serialized-script', { '+INSTALL' => original }, nil)
end
puts "PASS: #{count} actual package-script audit cases; no scripts executed"
