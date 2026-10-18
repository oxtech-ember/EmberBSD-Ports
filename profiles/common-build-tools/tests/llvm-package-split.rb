#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Real pkgsrc PLIST contracts, without an LLVM build.
require 'fileutils'
require 'digest'
require 'find'
require 'open3'
require 'shellwords'
require 'timeout'

abort 'Usage: llvm-package-split.rb PKGSRC HOST_PREFIX CROSS_TOOLS SYSROOT NEW_WORK' unless ARGV.length == 5
source, host, tools, sysroot = ARGV.first(4).map { |path| File.realpath(path) }
work = File.expand_path(ARGV.last)
abort 'new absolute work directory required' unless ARGV.last.start_with?('/') && !File.exist?(work)
FileUtils.mkdir_p(work)
tree = work + '/pkgsrc'
Dir.mkdir(tree)
profile = File.expand_path('..', __dir__)
# Other recipes and the actual pkgsrc framework remain read-only. Only these
# two recipes can write local files; WRKDIR and the package database are private.
Dir.children(source).reject { |name| name.start_with?('.') }.each do |name|
  if %w[lang devel].include?(name)
    Dir.mkdir(tree + '/' + name)
    Dir.children(source + '/' + name).each do |package|
      next if name == 'lang' && %w[llvm llvm-devel].include?(package)
      File.symlink(source + '/' + name + '/' + package, tree + '/' + name + '/' + package)
    end
  else
    File.symlink(source + '/' + name, tree + '/' + name)
  end
end
%w[llvm llvm-devel].each do |name|
  recipe = profile + '/recipes/lang/' + name
  FileUtils.cp_r(recipe, tree + '/lang/' + name) if File.directory?(recipe)
end
File.write(work + '/mk.conf', <<~MAKE)
  .include "#{host}/etc/mk.conf"
  WRKOBJDIR= #{work}/objects
  PACKAGES= #{work}/packages
  PKG_DBDIR= #{work}/pkgdb
  CXXFLAGS= -O2
MAKE
bmake = ENV.fetch('BMAKE', host + '/bin/bmake')
common = [bmake, 'MAKECONF=' + work + '/mk.conf', 'AWK=' + host + '/bin/nawk',
  'CAT=/bin/cat', 'SED=/usr/bin/sed', 'TEST=/bin/test', 'MKDIR=/bin/mkdir -p',
  'PERL5=' + host + '/bin/perl', 'FIND=/usr/bin/find', 'LN=/bin/ln',
  'INSTALL_DATA_DIR=/usr/bin/install -d',
  'X11_TYPE=modular']
# Cache actual SDK lookup results rather than repeating xcrun --no-cache for
# every make parse. Missing SDK tools retain the framework's empty result.
%w[m4 yacc].each do |tool|
  path, error, status = Open3.capture3('/usr/bin/xcrun', '--find', tool)
  File.write(work + '/xcrun-' + tool + '.log', path + error)
  common << 'OSX_PATH_TO_' + tool.upcase + '=' + (status.success? ? path.strip : '')
end
# Reuse genuine native provider option metadata for native-only manifest parsing.
# An empty private database otherwise recursively queries libxml2 -> GCC ->
# libxml2. This is a source contract, not an installed target dependency claim.
xml_options, xml_error, xml_status = Open3.capture3(host + '/sbin/pkg_info',
  '-K', host + '/pkgdb', '-Q', 'PKG_OPTIONS', 'libxml2')
abort 'installed native libxml2 option receipt required: ' + xml_error unless xml_status.success?
File.write(work + '/native-libxml2-options.txt', xml_options)
common << 'PKG_BUILD_OPTIONS.libxml2=' + xml_options.strip
cross = ['USE_CROSS_COMPILE=yes', 'CROSS_OPSYS=NetBSD', 'CROSS_OS_VERSION=11.0',
  'CROSS_OPSYS_VERSION=110000', 'CROSS_MACHINE_ARCH=x86_64', 'CROSS_LOWER_OPSYS=netbsd',
  'CROSS_LOWER_OPSYS_VERSUFFIX=', 'CROSS_LOWER_OS_VARIANT=', 'CROSS_LOWER_VARIANT_VERSION=',
  'CROSS_LOWER_VENDOR=', 'CROSS_OBJECT_FMT=ELF', 'CROSS_LOCALBASE=/usr/pkg',
  'CROSS_DESTDIR=' + sysroot, 'TOOLDIR=' + tools, 'CROSS_PKG_TOOLS_BIN=' + host + '/sbin']
cross << 'USE_PKGSRC_GCC_RUNTIME=no'
run = lambda do |label, package, *arguments|
  command = [*common, '-C', tree + '/lang/' + package, *arguments]
  output = ''
  status = nil
  Open3.popen2e(*command, pgroup: true) do |input, stream, process|
    input.close
    reader = Thread.new { stream.read }
    begin
      status = Timeout.timeout(30) { process.value }
    rescue Timeout::Error
      Process.kill('KILL', -process.pid) rescue Errno::ESRCH
      process.value
    ensure
      output = reader.value
    end
  end
  File.write(work + '/' + label + '.log', output)
  abort label + ': bounded source query exceeded 30 seconds' unless status
  abort label + ': ' + output unless status.success?
  output
end
plist = lambda do |label, package, *mode|
  directory = work + '/' + label
  run.call(label, package, *mode, 'WRKDIR=' + directory, 'plist')
  File.readlines(directory + '/.PLIST_nokeywords', chomp: true).reject(&:empty?)
end
runtime = plist.call('runtime', 'llvm', *cross)
abort 'runtime PLIST contains SDK files' unless runtime.sort == %w[include/llvm/Support/LICENSE.TXT lib/libLLVM.so.23.1 lib/libLLVM-23.so lib/libLLVM.so lib/libLTO.so.23.1 lib/libLTO.so lib/libRemarks.so.23.1 lib/libRemarks.so].sort
abort 'runtime package identity was not revised' unless run.call('runtime-name', 'llvm', *cross, '-V', '${PKGNAME}').strip == 'llvm-23.1.3nb1'
abort 'SDK recipe missing' unless File.directory?(tree + '/lang/llvm-devel')
sdk = plist.call('devel', 'llvm-devel', *cross)
abort 'SDK PLIST lost the CMake/generator contract' unless %w[bin/llvm-config bin/llvm-tblgen include/llvm/IR/Module.h lib/cmake/llvm/LLVMConfig.cmake lib/libLLVMCore.a].all? { |path| sdk.include?(path) }
abort 'partition overlaps' unless (runtime & sdk).empty?
owner = tree + '/lang/llvm'
full_dir = work + '/full'
run.call('full', 'llvm', *cross, 'WRKDIR=' + full_dir, 'PLIST=' + full_dir + '/.PLIST',
  'PLIST_SRC=' + owner + '/PLIST', 'plist')
full = File.readlines(full_dir + '/.PLIST_nokeywords', chomp: true).reject(&:empty?)
abort 'expanded partition union differs from full pkgsrc PLIST' unless (runtime + sdk).sort == full.sort
helper = owner + '/files/select-package-stage.pl'
abort 'stage partition helper missing' unless File.file?(helper)
native = plist.call('native', 'llvm', 'USE_CROSS_COMPILE=no', 'PKGSRC_COMPILER=clang',
  'CC=/usr/bin/clang', 'CXX=/usr/bin/clang++', 'CLANGBASE=/usr', 'USE_NATIVE_GCC=no', 'USE_PKGSRC_GCC=no')
abort 'native full SDK behavior changed' unless native.include?('bin/llvm-config') && native.include?('include/llvm/IR/Module.h')
reasons = run.call('devel-metadata', 'llvm-devel', *cross, '-V', '${PKG_FAIL_REASON}', '-V', '${DEPENDS}', '-V', '${DISTINFO_FILE}', '-V', '${PATCHDIR}')
abort 'SDK source owner, exact runtime or platform contract differs' unless reasons.lines.first.strip.empty? && reasons.include?('llvm-23.1.3nb1:') && reasons.include?(owner + '/distinfo') && reasons.include?(owner + '/patches')
FileUtils.mkdir_p(tree + '/devel/llvm-split-consumer')
File.write(tree + '/devel/llvm-split-consumer/Makefile', <<~MAKE)
  DISTNAME= llvm-split-contract-1
  CATEGORIES= devel
  COMMENT= LLVM buildlink source contract fixture
  LICENSE= 2-clause-bsd
  META_PACKAGE= yes
  .include "../../mk/bsd.prefs.mk"
  .include "../../lang/llvm/buildlink3.mk"
  .include "../../mk/bsd.pkg.mk"
MAKE
out = run.call('buildlink', '../devel/llvm-split-consumer', *cross,
  '-V', '${BUILD_DEPENDS}', '-V', '${DEPENDS}')
abort 'SDK was not a separate target build-only dependency' unless out.lines[0].include?('llvm-devel>=23.1.3nb2:') && !out.lines[1].include?('llvm-devel') && out.lines[1].include?('llvm>=23.1.3nb1:')

fields = run.call('runtime-dependencies', 'llvm', *cross,
  '-V', '${DEPENDS}', '-V', '${BUILD_DEPENDS}', '-V', '${TOOL_DEPENDS}',
  '-V', '${CMAKE_CONFIGURE_ARGS}', '-V', '${PKG_FAIL_REASON}', '-V', '${USE_BUILTIN.zlib}').lines.map(&:strip)
abort 'runtime retained SDK or Python/lit runtime dependencies' if fields[0].match?(/llvm-devel|llvm-lit|python[0-9]/)
abort 'runtime lost shared-library dependencies' unless %w[zstd libxml2].all? { |name| fields[0].include?(name + '>=') }
abort 'zlib provider missing' unless fields[0].include?('zlib>=') || fields[5] == 'yes'
abort 'lit is not a build dependency or Python is not a native tool dependency' unless fields[1].include?('llvm-lit>=23.1.3nb1:') && fields[2].match?(/python[0-9]+>=/)
abort 'cross native-tool fallback depends on a target SDK/revision' unless fields[2].include?('llvm-23.1.3{,nb*}:../../lang/llvm') && !fields[2].include?('llvm-devel')
flags = fields[3]
%w[LLVM_BUILD_LLVM_DYLIB=ON LLVM_LINK_LLVM_DYLIB=ON LLVM_ENABLE_RTTI=ON BUILD_SHARED_LIBS=OFF LLVM_INSTALL_TOOLCHAIN_ONLY=OFF LLVM_INCLUDE_TESTS=ON LLVM_INSTALL_GTEST=ON].each do |flag|
  abort 'full LLVM build feature changed: ' + flag unless flags.include?(flag)
end
backends = %w[AArch64 AMDGPU ARM AVR BPF Hexagon Lanai LoongArch Mips MSP430 NVPTX PowerPC RISCV Sparc SPIRV SystemZ VE WebAssembly X86 XCore ARC CSKY DirectX M68k Xtensa]
abort 'full backend policy changed' unless backends.all? { |name| flags.match?(/(?:[=;\"]|\A)#{name}(?:[;\"]|\z)/) }
abort 'runtime has package failure reasons: ' + fields[4].to_s unless fields[4].to_s.empty?
sdk_metadata = run.call('sdk-dependencies', 'llvm-devel', *cross,
  '-V', '${DEPENDS}', '-V', '${WRKSRC}', '-V', '${EXTRACT_ELEMENTS}', '-V', '${TOOL_DEPENDS}').lines.map(&:strip)
abort 'SDK lost installed Python/lit tools' unless sdk_metadata[0].include?('llvm-lit-23.1.3') && sdk_metadata[3].match?(/python[0-9]+>=/)
abort 'SDK extracts a different source component' unless sdk_metadata[1].end_with?('/llvm') && sdk_metadata[2].include?('/llvm ') && !sdk_metadata[2].include?('/llvm-devel')
abort 'SDK native-tool fallback is not LLVM core' unless sdk_metadata[3].include?('llvm-23.1.3{,nb*}:../../lang/llvm')
# The AArch64 query expands manifests only. Use the real host Clang for
# compiler capability probing; no AArch64 target compiler is installed here.
arm = cross.reject { |arg| arg.start_with?('CROSS_MACHINE_ARCH=') } + ['CROSS_MACHINE_ARCH=aarch64', 'PKGSRC_COMPILER=clang', 'CLANGBASE=/usr', 'CC=/usr/bin/clang', 'CXX=/usr/bin/clang++']
abort 'AArch64 runtime partition differs' unless plist.call('runtime-arm', 'llvm', *arm).sort == runtime.sort
%w[LLVM_PACKAGE_PART=devel PKGREVISION=2 CROSS_MACHINE_ARCH=i386].each_with_index do |bad, index|
  reasons = run.call('bad-contract-' + index.to_s, 'llvm', *cross.reject { |arg| arg.start_with?(bad.split('=').first + '=') }, bad, *(['PKGSRC_COMPILER=clang', 'CLANGBASE=/usr', 'CC=/usr/bin/clang', 'CXX=/usr/bin/clang++'] if bad.start_with?('CROSS_MACHINE_ARCH=')), '-V', '${PKG_FAIL_REASON}')
  abort 'invalid package contract accepted: ' + bad if reasons.strip.empty?
end
native_args = ['USE_CROSS_COMPILE=no', 'PKGSRC_COMPILER=clang', 'CC=/usr/bin/clang', 'CXX=/usr/bin/clang++', 'CLANGBASE=/usr', 'USE_NATIVE_GCC=no', 'USE_PKGSRC_GCC=no']
abort 'native identity changed' unless run.call('native-name', 'llvm', *native_args, '-V', '${PKGNAME}').strip == 'llvm-23.1.3'
abort 'native SDK recipe accepted' if run.call('native-sdk-refused', 'llvm-devel', *native_args, '-V', '${PKG_FAIL_REASON}').strip.empty?

# These payload bytes are labelled source-contract fixtures, not compiled LLVM.
# Exercise the actual selection target and preserve every byte
# and symlink that belongs to the selected real pkgsrc manifest.
original = work + '/full-stage'
prefix = original + '/usr/pkg'
full.each do |path|
  FileUtils.mkdir_p(File.dirname(prefix + '/' + path))
  File.write(prefix + '/' + path, "source-contract fixture: #{path}\n")
end
fingerprint = lambda do |directory|
  files = {}
  Find.find(directory) do |path|
    next if File.directory?(path) && !File.symlink?(path)
    relative = path.delete_prefix(directory + '/')
    files[relative] = File.symlink?(path) ? ['symlink', File.readlink(path)] : ['file', Digest::SHA256.file(path).hexdigest, File.stat(path).mode & 07777]
  end
  files
end
# Model the real DSO alias topology. These are still labelled text files.
{'lib/libLLVM-23.so' => 'libLLVM.so.23.1', 'lib/libLLVM.so' => 'libLLVM-23.so',
 'lib/libLTO.so' => 'libLTO.so.23.1', 'lib/libRemarks.so' => 'libRemarks.so.23.1'}.each do |name, target|
  File.unlink(prefix + '/' + name)
  File.symlink(target, prefix + '/' + name)
end
File.chmod(0555, prefix + '/lib/libLLVM.so.23.1')
before = fingerprint.call(prefix)
abort 'full fixture differs from the pkgsrc manifest' unless before.keys.sort == full.sort
%w[runtime devel].each do |part|
  destination = work + '/' + part + '-stage'
  FileUtils.cp_r(original, destination, preserve: true)
  package = part == 'runtime' ? 'llvm' : 'llvm-devel'
  run.call(part + '-select-stage', package, *cross, 'WRKDIR=' + work + '/' + part + '-select',
    'DESTDIR=' + destination, 'llvm-select-stage')
  selected = part == 'runtime' ? runtime : sdk
  abort 'selected stage bytes, modes or symlinks changed' unless fingerprint.call(destination + '/usr/pkg') == before.select { |path, _| selected.include?(path) }
end
%w[missing unknown overlap union selected symlink-parent part].each do |case_name|
  destination = work + '/reject-' + case_name
  FileUtils.cp_r(original, destination, preserve: true)
  stage = destination + '/usr/pkg'
  lists = [full_dir + '/.PLIST', work + '/runtime/.PLIST', work + '/devel/.PLIST', work + '/runtime/.PLIST']
  part = 'runtime'
  case case_name
  when 'missing' then File.unlink(stage + '/' + sdk.first)
  when 'unknown' then File.write(stage + '/bin/unlisted-generator', 'unlisted fixture')
  when 'overlap'
    lists[2] = destination + '/overlap.plist'
    File.write(lists[2], File.read(work + '/devel/.PLIST') + runtime.first + "\n")
  when 'union'
    lists[2] = destination + '/incomplete.plist'
    File.write(lists[2], (sdk.drop(1)).join("\n") + "\n")
  when 'selected' then lists[3] = lists[2]
  when 'symlink-parent'
    outside = destination + '/outside'
    Dir.mkdir(outside)
    File.write(outside + '/preserved', 'outside fixture')
    FileUtils.rm_r(stage + '/include')
    File.symlink(outside, stage + '/include')
  when 'part' then part = 'unsupported'
  end
  unchanged = fingerprint.call(stage)
  output, status = Open3.capture2e(host + '/bin/perl', helper, part, stage, *lists)
  File.write(work + '/reject-' + case_name + '.log', output)
  abort 'invalid partition was accepted: ' + case_name if status.success?
  abort 'invalid partition changed staging: ' + case_name unless fingerprint.call(stage) == unchanged
end
puts 'PASS: real pkgsrc produces distinct runtime/SDK manifests and a revised runtime identity'
puts 'PASS: both target manifests, native full manifest/identity, full backends/features, source identity and runtime/build/tool dependency roles'
puts 'PASS: package part, revision, unsupported architecture and native SDK guards reject invalid contracts'
puts 'PASS: actual full-stage partition preserve selected bytes; seven invalid inputs fail before pruning'
puts 'SCOPE: source packaging contract only; no LLVM compilation, target file execution or installed LLVM acceptance'
