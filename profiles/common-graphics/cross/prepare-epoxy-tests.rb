#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), installed libepoxy consumer acceptance.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
require 'rubygems/package'
require 'zlib'

abort 'usage: prepare-epoxy-tests.rb CROSS_TOOLS SYSROOT EPOXY_BUILD EPOXY_PACKAGE MESA_METADATA_BUNDLE EPOXY_CONSUMER_WORK NEW_WORK' unless ARGV.length == 7
tools, sysroot, build, package, mesa, consumer = ARGV.first(6).map { |p| File.realpath(p) }
work = File.expand_path(ARGV.last)
abort 'NEW_WORK must be new and absolute' unless ARGV.last.start_with?('/') && !File.exist?(work)
owner = File.dirname(File.realpath(__FILE__))
readelf = "#{tools}/bin/aarch64--netbsd-readelf"
prefix = "#{sysroot}/usr/pkg"

def hash_file(path)
  Digest::SHA256.file(path).hexdigest
end

def verify_manifest(base, manifest)
  File.readlines(manifest).each do |line|
    hash, path = line.chomp.split(/  /, 2)
    abort 'invalid input manifest' unless hash&.match?(/\A[0-9a-f]{64}\z/) && path && !path.split('/').include?('..')
    actual = path.start_with?('/') ? path : "#{base}/#{path}"
    abort "input drift: #{actual}" unless File.file?(actual) && hash_file(actual) == hash
  end
end

verify_manifest(mesa, "#{mesa}/artifacts.sha256")
verify_manifest(consumer, "#{consumer}/inputs.sha256")
abort 'Mesa metadata verification failed' unless system('sh', "#{mesa}/run-mesa-package-tests.sh", '--verify-sysroot', mesa, sysroot)
mesa_contents = ["#{mesa}/source/MesaLib.CONTENTS", "#{mesa}/MesaLib.CONTENTS"].find { |p| File.file?(p) }
abort 'require the metadata-corrected Mesa package' unless mesa_contents && File.read(mesa_contents).include?("@name MesaLib-26.2.4nb3\n")
project = JSON.parse(File.read("#{build}/meson-info/intro-projectinfo.json"))
abort 'require actual libepoxy 1.5.10 build' unless project['version'] == '1.5.10'
consumer_binary = "#{consumer}/epoxy-pkgconfig-render"
abort 'consumer executable is not in its input receipt' unless File.read("#{consumer}/inputs.sha256").include?("#{hash_file(consumer_binary)}  #{consumer_binary}\n")
bundle = "#{work}/bundle"
FileUtils.mkdir_p(["#{bundle}/bin", "#{bundle}/source"])
FileUtils.cp(consumer_binary, "#{bundle}/bin/epoxy-render")
FileUtils.cp("#{owner}/run-epoxy-tests.sh", bundle)
FileUtils.cp("#{owner}/mesa-render.c", "#{bundle}/source")
%w[inputs.sha256 consumer-build.log.command consumer-elf.log].each { |p| FileUtils.cp("#{consumer}/#{p}", "#{bundle}/source") }
files = File.readlines("#{mesa}/mesa-package-files.sha256").to_h { |l| h,p=l.chomp.split(/  /,2); [p,h] }
links = File.readlines("#{mesa}/mesa-package-links.tsv").to_h { |l| l.chomp.split("\t",2) }
runtime = File.readlines("#{mesa}/runtime-libraries.sha256").to_h { |l| h,p=l.chomp.split(/  /,2); [p,h] }
Zlib::GzipReader.open(package) do |gzip|
  Gem::Package::TarReader.new(gzip) do |tar|
    tar.each do |entry|
      next if entry.directory? || entry.header.typeflag == 'x'
      name = entry.full_name
      if name.start_with?('+')
        File.write("#{bundle}/source/libepoxy.CONTENTS", entry.read) if name == '+CONTENTS'
        next
      end
      abort 'unsafe package path' if name.start_with?('/') || name.split('/').include?('..')
      target = "/usr/pkg/#{name}"
      path = sysroot + target
      if entry.file?
        abort "installed libepoxy drift: #{name}" unless File.file?(path) && Digest::SHA256.hexdigest(entry.read) == hash_file(path)
      elsif entry.header.typeflag == '2'
        abort "installed link drift: #{name}" unless File.symlink?(path) && File.readlink(path) == entry.header.linkname
        links[target] = entry.header.linkname
      else
        abort 'unsupported package entry'
      end
      files[target] = hash_file(path)
      runtime[target] = files[target] if File.binread(path,4) == "\x7fELF"
    end
  end
end
contents = File.read("#{bundle}/source/libepoxy.CONTENTS")
abort 'wrong package identity/dependency' unless contents.include?("@name libepoxy-1.5.10nb2\n") && contents.include?("@pkgdep MesaLib>=26.2.4nb2\n")
selected = %w[header_guards misc_defines khronos_typedefs gl_version]
tests = JSON.parse(File.read("#{build}/meson-info/intro-tests.json")).select { |t| selected.include?(t['name']) }
abort 'missing/duplicate upstream tests' unless tests.map { |t| t['name'] }.sort == selected.sort
inputs = {package => hash_file(package), "#{consumer}/inputs.sha256" => hash_file("#{consumer}/inputs.sha256")}
rows = tests.map do |t|
  cmd = t.fetch('cmd')
  # Meson adds the build libepoxy directory. This installed-library acceptance
  # deliberately removes that one exact override; other test inputs must match.
  # A relocated build can retain a still-valid symlink spelling in Meson JSON.
  # Resolve both paths; do not allow another directory or extra environment.
  executable = File.realpath(cmd[0]) if cmd.length == 1 && cmd[0].start_with?('/')
  library_path = t.fetch('env').fetch('LD_LIBRARY_PATH', '')
  library_path = File.realpath(library_path) if library_path.start_with?('/') && File.directory?(library_path)
  abort 'unexpected pure test prerequisites' unless executable&.start_with?(build + '/') &&
    t['env'].keys == ['LD_LIBRARY_PATH'] && library_path == "#{build}/src" &&
    t['workdir'].nil? && t['protocol'] == 'exitcode'
  limit = t.fetch('timeout')
  abort 'unbounded upstream test' unless limit.is_a?(Integer) && limit.between?(1, 120)
  inputs[cmd[0]] = hash_file(cmd[0])
  FileUtils.cp(cmd[0], "#{bundle}/bin/#{t['name']}")
  [t['name'], limit]
end
Dir.glob("#{bundle}/bin/*").each do |path|
  header = File.binread(path,20)
  abort 'not AArch64 ELF' unless header.byteslice(0,6) == "\x7fELF\x02\x01" && header.byteslice(18,2).unpack1('v') == 183
  dynamic, error, status = Open3.capture3(readelf, '-d', path)
  abort error unless status.success?
  File.write("#{bundle}/source/#{File.basename(path)}.dynamic", dynamic)
  paths = dynamic.scan(/\((?:RPATH|RUNPATH)\).*\[([^\]]+)\]/).flatten.flat_map { |p| p.split(':') }
  abort 'foreign test runtime path' unless paths.all? { |p| %w[/usr/pkg/lib /usr/pkg/gcc16/lib].include?(File.expand_path(p)) }
  dynamic.scan(/\(NEEDED\).*\[([^\]]+)\]/).flatten.each do |name|
    abort "unrecorded package test dependency: #{name}" unless runtime.keys.any? { |p| File.basename(p) == name } || File.file?("#{sysroot}/usr/lib/#{name}") || File.file?("#{sysroot}/lib/#{name}")
  end
end
File.write("#{bundle}/installed-files.sha256", files.sort.map { |p,h| "#{h}  #{p}\n" }.join)
File.write("#{bundle}/installed-links.tsv", links.sort.map { |p,t| "#{p}\t#{t}\n" }.join)
File.write("#{bundle}/runtime-libraries.sha256", runtime.sort.map { |p,h| "#{h}  #{p}\n" }.join)
File.write("#{bundle}/tests.tsv", rows.map { |row| row.join("\t")+"\n" }.join)
File.write("#{bundle}/source/upstream-tests.json", JSON.pretty_generate(tests)+"\n")
File.write("#{bundle}/source/receipt.json", JSON.pretty_generate({package: package, input_sha256: inputs,
  scope: 'Four unconditional upstream pure tests plus actual epoxy-dispatched surfaceless rendering. Display-dependent EGL/GLX tests are not included.'})+"\n")
inputs.each { |p,h| abort 'input changed during preparation' unless hash_file(p) == h }
paths = Dir.glob("#{bundle}/**/*").select { |p| File.file?(p) }.sort
File.write("#{bundle}/artifacts.sha256", paths.map { |p| "#{hash_file(p)}  #{p.delete_prefix(bundle+'/')}\n" }.join)
archive = "#{work}/epoxy-tests.tar.gz"
abort 'tar failed' unless system({'COPYFILE_DISABLE'=>'1'}, 'tar', '--no-xattrs', '-czf', archive, '-C', bundle, '.')
puts "#{hash_file(archive)}  #{archive}"
