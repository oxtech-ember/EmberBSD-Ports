#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), acceptance of the installed common Mesa package.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
require 'rubygems/package'
require 'shellwords'
require 'zlib'

abort 'usage: prepare-mesa-package-tests.rb CROSS_TOOLS SYSROOT MESA_SOURCE MESA_BUILD MESA_PACKAGE NEW_WORK' unless ARGV.length == 6
tools, sysroot, source, build, package = ARGV.first(5).map { |p| File.realpath(p) }
work = File.expand_path(ARGV.last)
abort 'NEW_WORK must be a new absolute path' unless ARGV.last.start_with?('/') && !File.exist?(work)
owner = File.dirname(File.realpath(__FILE__))
prefix = "#{sysroot}/usr/pkg"
cc, readelf = %w[gcc readelf].map { |name| "#{tools}/bin/aarch64--netbsd-#{name}" }
abort 'missing cross compiler or ELF inspector' unless [cc, readelf].all? { |p| File.executable?(p) }

def query(*command)
  out, err, status = Open3.capture3(*command)
  abort "failed: #{Shellwords.join(command)}\n#{err}" unless status.success?
  out.strip
end

def elf?(path)
  File.file?(path) && File.binread(path, 4) == "\x7fELF"
end

def target_elf!(path)
  header = File.binread(path, 20)
  abort "not an AArch64 ELF64 executable/library: #{path}" unless header.byteslice(0, 6) == "\x7fELF\x02\x01" &&
    [2, 3].include?(header.byteslice(16, 2).unpack1('v')) && header.byteslice(18, 2).unpack1('v') == 183
end

abort 'unexpected cross compiler target' unless query(cc, '-dumpmachine') == 'aarch64--netbsd'
info = "#{build}/meson-info"
project = JSON.parse(File.read("#{info}/intro-projectinfo.json"))
abort 'require Mesa 26.2.4 build metadata' unless project.fetch('version') == '26.2.4' && File.read("#{source}/VERSION").strip == '26.2.4'
options = JSON.parse(File.read("#{info}/intro-buildoptions.json")).to_h { |o| [o.fetch('name'), o.fetch('value')] }
{'prefix' => '/usr/pkg', 'llvm' => 'enabled', 'shared-llvm' => 'enabled', 'build-tests' => true,
 'egl' => 'enabled', 'gles2' => 'enabled', 'glx' => 'dri'}.each do |name, value|
  abort "unexpected Mesa option #{name}" unless options.fetch(name) == value
end
abort 'require complete common drivers/platforms' unless options.fetch('gallium-drivers').sort == %w[llvmpipe softpipe v3d virgl] && options.fetch('platforms').sort == %w[wayland x11]
ninja = File.read("#{build}/build.ninja")
abort 'require the actual shared LLVM23 ORC build' unless ninja.include?('-DGALLIVM_USE_ORCJIT=1') && ninja.include?('-DLLVM_IS_SHARED=1') && ninja.include?('23.1.2')
inputs = [__FILE__, "#{owner}/mesa-render.c", "#{owner}/run-mesa-package-tests.sh", cc, readelf, package,
          "#{source}/VERSION", "#{build}/build.ninja", "#{build}/compile_commands.json"] +
         %w[intro-projectinfo.json intro-buildoptions.json intro-tests.json].map { |name| "#{info}/#{name}" }
initial = inputs.to_h { |p| [p, Digest::SHA256.file(p).hexdigest] }
bundle = "#{work}/bundle"
FileUtils.mkdir_p(["#{bundle}/bin", "#{bundle}/source", "#{bundle}/fixtures", "#{work}/elf"])
FileUtils.cp("#{owner}/mesa-render.c", "#{bundle}/source")
FileUtils.cp("#{owner}/run-mesa-package-tests.sh", bundle)
File.chmod(0755, "#{bundle}/run-mesa-package-tests.sh")

# Compare every installed Mesa file and symlink with the actual normal package.
# Read the archive in memory; no second installed prefix or payload copy is made.
payload = {}
links = {}
mesa_elfs = []
Zlib::GzipReader.open(package) do |gzip|
  Gem::Package::TarReader.new(gzip) do |tar|
    tar.each do |entry|
      # pkgsrc records PAX timestamps separately; payload names remain short.
      next if entry.header.typeflag == 'x'
      name = entry.full_name.sub(%r{\A\./}, '')
      if name.start_with?('+')
        File.write("#{bundle}/source/MesaLib.CONTENTS", entry.read) if name == '+CONTENTS'
        next
      end
      next if entry.directory?
      abort "unsafe package path #{name}" if name.start_with?('/') || name.split('/').include?('..')
      installed = "#{prefix}/#{name}"
      if entry.header.typeflag == '2'
        abort "installed package symlink mismatch: #{name}" unless File.symlink?(installed) && File.readlink(installed) == entry.header.linkname
        links["/usr/pkg/#{name}"] = entry.header.linkname
      elsif entry.file?
        expected = Digest::SHA256.hexdigest(entry.read)
        abort "installed package file mismatch: #{name}" unless File.file?(installed) && Digest::SHA256.file(installed).hexdigest == expected
      else
        abort "unsupported package entry: #{name}"
      end
      payload["/usr/pkg/#{name}"] = Digest::SHA256.file(installed).hexdigest
      mesa_elfs << installed if elf?(installed)
    end
  end
end
contents = File.read("#{bundle}/source/MesaLib.CONTENTS")
abort 'unexpected package identity/prefix' unless contents.include?("@name MesaLib-26.2.4nb3\n") && contents.include?("@cwd /usr/pkg\n")
abort 'package has no Mesa shared libraries' if mesa_elfs.empty?
File.write("#{bundle}/mesa-package-files.sha256", payload.sort.map { |path, sha| "#{sha}  #{path}\n" }.join)
File.write("#{bundle}/mesa-package-links.tsv", links.sort.map { |path, target| "#{path}\t#{target}\n" }.join)

command = [cc, "--sysroot=#{sysroot}", '-O2', '-std=c11', '-D_NETBSD_SOURCE', '-Wall', '-Wextra', '-Werror',
           "-I#{prefix}/include", "#{bundle}/source/mesa-render.c", "-L#{prefix}/lib", '-lEGL', '-lGLESv2', '-lgbm',
           "-Wl,-rpath-link,#{prefix}/lib", "-Wl,-rpath-link,#{prefix}/gcc16/lib",
           '-Wl,-rpath,/usr/pkg/lib', '-Wl,-rpath,/usr/pkg/gcc16/lib', '-o', "#{bundle}/bin/mesa-render"]
File.write("#{work}/render-build.command", Shellwords.join(command) + "\n")
out, err, status = Open3.capture3(*command)
File.write("#{work}/render-build.log", out + err)
abort 'render consumer compile/link failed' unless status.success?

tests = []
JSON.parse(File.read("#{info}/intro-tests.json")).each do |test|
  cmd = test.fetch('cmd')
  next unless cmd.length == 1 && cmd[0].start_with?(build + '/') && elf?(cmd[0])
  name, executable = test.fetch('name'), File.basename(cmd[0])
  abort 'unsafe test name' unless [name, executable].all? { |s| s.match?(/\A[A-Za-z0-9_-]+\z/) }
  abort "unsupported working directory/protocol: #{name}" unless test['workdir'].nil? && %w[exitcode gtest].include?(test.fetch('protocol'))
  expected_env = case name
                 when 'xmlconfig' then {'HOME' => "#{source}/src/util/tests/drirc_home", 'DRIRC_CONFIGDIR' => "#{source}/src/util/tests/drirc_configdir"}
                 when 'process' then {'BUILD_FULL_PATH' => cmd[0]}
                 when 'process_with_overrides' then {'BUILD_FULL_PATH' => cmd[0], 'MESA_PROCESS_NAME' => 'hello'}
                 else {}
                 end
  abort "unhandled upstream test environment: #{name}" unless test.fetch('env') == expected_env
  limit = test.fetch('timeout')
  abort "unbounded test: #{name}" unless limit.is_a?(Integer) && limit.between?(1, 600)
  destination = "#{bundle}/bin/#{executable}"
  sha = Digest::SHA256.file(cmd[0]).hexdigest
  abort "test basename collision: #{executable}" if File.exist?(destination) && Digest::SHA256.file(destination).hexdigest != sha
  initial[cmd[0]] = sha
  FileUtils.cp(cmd[0], destination)
  tests << [name, executable, limit]
end
abort 'missing expected full-Mesa upstream tests' unless tests.length == 38 && tests.any? { |t| t[0] == 'qpu_disasm' } && tests.count { |t| t[0].start_with?('lp_test_') } == 7 && tests.any? { |t| t[0] == 'xmlconfig' }
File.write("#{bundle}/upstream-tests.tsv", tests.map { |row| row.join("\t") + "\n" }.join)
%w[drirc_home drirc_configdir].each { |name| FileUtils.cp_r("#{source}/src/util/tests/#{name}", "#{bundle}/fixtures") }

# Resolve DT_NEEDED from target files only, retaining all SONAME/real-file names
# that the target loader can report. This is an input closure, not a fake ldd.
runtime = {}
seen = {}
queue = mesa_elfs + Dir.glob("#{bundle}/bin/*")
until queue.empty?
  path = queue.shift
  real = File.realpath(path)
  abort 'ELF input escapes sysroot/bundle' unless real.start_with?(sysroot + '/') || real.start_with?(bundle + '/')
  if path.start_with?(prefix + '/')
    abort 'library symlink escapes target sysroot' unless real.start_with?(prefix + '/')
    [path, real].each { |p| runtime[p.delete_prefix(sysroot)] = Digest::SHA256.file(p).hexdigest }
  end
  next if seen[real]
  seen[real] = true
  target_elf!(real)
  dynamic = query(readelf, '-d', real)
  File.write("#{work}/elf/#{Digest::SHA256.hexdigest(real)[0, 16]}.txt", "#{real}\n#{dynamic}\n")
  rpaths = dynamic.scan(/\((?:RUNPATH|RPATH)\).*\[([^\]]+)\]/).flatten.flat_map { |p| p.split(':') }
  abort "relative ELF runtime path: #{real}" unless rpaths.all? { |p| p.start_with?('/') }
  rpaths.map! { |p| File.expand_path(p) }
  allowed = %w[/usr/pkg/lib /usr/pkg/gcc16/lib /usr/pkg/gcc16/aarch64--netbsd/lib /usr/pkg/lib/python3.14/config-3.14 /usr/lib /lib]
  abort "foreign ELF runtime path: #{real}" unless rpaths.all? { |p| allowed.include?(p) }
  dynamic.scan(/\(NEEDED\).*\[([^\]]+)\]/).flatten.each do |name|
    abort "absolute/non-library NEEDED: #{name}" unless name.match?(/\Alib[A-Za-z0-9_.+-]+\z/)
    directories = (rpaths + %w[/usr/pkg/gcc16/lib /usr/pkg/lib /usr/lib /lib]).uniq
    dependency = directories.map { |dir| "#{sysroot}#{dir}/#{name}" }.find { |p| File.file?(p) }
    abort "unresolved target dependency #{name} from #{real}" unless dependency
    queue << dependency
  end
end
abort 'missing shared LLVM23 runtime closure' unless runtime.key?('/usr/pkg/lib/libLLVM.so.23.1')
File.write("#{bundle}/runtime-libraries.sha256", runtime.sort.map { |path, sha| "#{sha}  #{path}\n" }.join)
initial.merge!(runtime.to_h { |path, sha| [sysroot + path, sha] })
initial.each { |path, sha| abort "input changed during preparation: #{path}" unless Digest::SHA256.file(path).hexdigest == sha }
File.write("#{work}/inputs.sha256", initial.sort.map { |path, sha| "#{sha}  #{path}\n" }.join)
File.write("#{bundle}/source/receipt.json", JSON.pretty_generate({package_sha256: initial.fetch(package), compiler: cc,
  compiler_version: query(cc, '--version'), source: source, build: build, sysroot: sysroot,
  options: options, input_sha256: initial, target_invocations: tests.length}) + "\n")
artifacts = Dir.glob("#{bundle}/**/*", File::FNM_DOTMATCH).select { |p| File.file?(p) }.sort
File.write("#{bundle}/artifacts.sha256", artifacts.map { |p| "#{Digest::SHA256.file(p).hexdigest}  #{p.delete_prefix(bundle + '/')}\n" }.join)
archive = "#{work}/mesa-package-tests.tar.gz"
abort 'archive creation failed' unless system({'COPYFILE_DISABLE' => '1'}, 'tar', '--no-xattrs', '--exclude', '._*', '-czf', archive, '-C', bundle, '.')
puts "#{Digest::SHA256.file(archive).hexdigest}  #{archive}"
puts "#{tests.length} upstream invocations; #{runtime.length} installed library paths; no runtime libraries bundled"
