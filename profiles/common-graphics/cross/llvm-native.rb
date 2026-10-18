# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Inspect and retain real native ELF runtimes.
require 'digest'
require 'fileutils'
require 'open3'
require 'shellwords'

module EmberGraphicsLLVMNative
  module_function

  CLEAN_ENV = {'LD_PRELOAD' => nil, 'LD_AUDIT' => nil}.freeze

  def platform(triple)
    return 'darwin' if triple.include?('darwin')
    return 'linux-gnu' if triple.match?(/\A(x86_64|aarch64)-(?:unknown-)?linux-gnu\z/)
    raise ArgumentError, "unsupported native LLVM triple: #{triple}"
  end

  def machine(triple)
    raise ArgumentError, 'expected native Linux GNU triple' unless platform(triple) == 'linux-gnu'
    triple.start_with?('aarch64-') ? 183 : 62
  end

  def capture(*command, env: {})
    out, err, status = Open3.capture3(CLEAN_ENV.merge(env), *command)
    raise ArgumentError, "native command failed: #{Shellwords.join(command)}: #{err.strip}" unless status.success?
    out
  end

  def executable(name)
    path = name.start_with?('/') ? name : ENV.fetch('PATH').split(':').map { |dir| File.join(dir, name) }.find { |p| File.executable?(p) && File.file?(p) }
    raise ArgumentError, "missing native tool: #{name}" unless path && File.executable?(path)
    File.realpath(path)
  end

  def safe_absolute?(path)
    path.is_a?(String) && path.start_with?('/') && !path.match?(/[\s\x00-\x1f]/) && !path.split('/').include?('..')
  end

  def elf(path, expected_machine)
    bytes = File.binread(path, 20)
    valid = bytes.bytesize == 20 && bytes.byteslice(0, 7) == "\x7fELF\x02\x01\x01".b &&
      [2, 3].include?(bytes.byteslice(16, 2).unpack1('v')) && bytes.byteslice(18, 2).unpack1('v') == expected_machine
    raise ArgumentError, "wrong native ELF architecture: #{path}" unless valid
  end

  def dynamic(path, readelf)
    text = capture(readelf, '-dW', path)
    needed = text.scan(/\(NEEDED\).*\[([^\]]+)\]/).flatten
    sonames = text.scan(/\(SONAME\).*\[([^\]]+)\]/).flatten
    raise ArgumentError, 'duplicate native SONAME' if sonames.length > 1
    (needed + sonames).each do |name|
      raise ArgumentError, "unsafe native dependency name: #{name}" unless name.match?(/\A[A-Za-z0-9_+.-]+\z/) && !name.include?('..')
      raise ArgumentError, 'native shared LLVM dependency is unsupported' if name.start_with?('libLLVM')
    end
    {needed: needed, soname: sonames.first}
  end

  def compiler(cxx, triple, flags)
    raise ArgumentError, 'Linux helper requires GCC16' unless capture(cxx, '-dumpfullversion').strip.match?(/\A16\./)
    macros = capture(cxx, '-dM', '-E', '-x', 'c++', '/dev/null')
    raise ArgumentError, 'Linux helper requires genuine GCC16' unless macros.match?(/^#define __GNUC__ 16$/) && !macros.match?(/^#define __clang__ /)
    raise ArgumentError, 'native compiler and LLVM architectures differ' unless machine(capture(cxx, '-dumpmachine').strip) == machine(triple)
    out, err, status = Open3.capture3(CLEAN_ENV, cxx, *flags, '-E', '-v', '-x', 'c++', '/dev/null', '-o', '/dev/null')
    raise ArgumentError, "native include search failed: #{out}#{err}" unless status.success?
    search = err[/#include <\.\.\.> search starts here:\n(.*?)End of search list\./m, 1]
    raise ArgumentError, 'native compiler did not report include search roots' unless search
    roots = search.lines.map(&:strip).map { |p| File.realpath(p) }.uniq
    raise ArgumentError, 'unsafe native include root' unless !roots.empty? && roots.all? { |p| safe_absolute?(p) && p != '/' }
    libraries = %w[libstdc++.so libgcc_s.so.1].map do |name|
      path = capture(cxx, "-print-file-name=#{name}").strip
      raise ArgumentError, "native compiler runtime missing: #{name}" unless path.start_with?('/') && File.file?(path)
      File.realpath(path)
    end
    {header_roots: roots, compiler_libraries: libraries}
  end

  # The glibc loader's virtual vDSO has no file. Every other line must resolve
  # to a real path. An unresolved or unfamiliar line cannot enter the closure.
  def loaded(text)
    result = {}
    text.lines.each do |line|
      next if line.match?(/\A\s*linux-vdso(?:64)?\.so\.1 \(0x[0-9a-f]+\)\s*\z/)
      match = line.match(/\A\s*(\S+) => (\/\S+) \(0x[0-9a-f]+\)\s*\z/) ||
        line.match(/\A\s*(\/\S+) \(0x[0-9a-f]+\)\s*\z/)
      raise ArgumentError, "unresolved native loader entry: #{line.strip}" unless match
      name = match[1].start_with?('/') ? File.basename(match[1]) : match[1]
      path = match[2] || match[1]
      raise ArgumentError, "duplicate or unsafe native loader entry: #{name}" if result.key?(name) || !safe_absolute?(path)
      result[name] = File.realpath(path)
    end
    result
  end

  def retain(binary, work, triple, compiler_libraries, forbidden: [])
    readelf = executable(ENV.fetch('NATIVE_READELF', 'readelf'))
    ldd = executable('ldd')
    elf(binary, machine(triple))
    interpreters = capture(readelf, '-lW', binary).scan(/\[Requesting program interpreter: ([^\]]+)\]/).flatten
    raise ArgumentError, 'expected one native ELF interpreter' unless interpreters.length == 1 && safe_absolute?(interpreters[0])
    interpreter = File.realpath(interpreters[0])
    search = (compiler_libraries.map { |p| File.dirname(p) } + ENV.fetch('LD_LIBRARY_PATH', '').split(':')).reject(&:empty?).uniq
    trace = capture(ldd, binary, env: {'LD_LIBRARY_PATH' => search.join(':')})
    paths = loaded(trace)
    loader_name = File.basename(interpreters[0])
    raise ArgumentError, 'native loader differs from ELF interpreter' unless paths[loader_name] == interpreter
    raise ArgumentError, 'loaded runtime is not the selected GCC16 runtime' unless (compiler_libraries - paths.values).empty?
    files = paths.map do |name, path|
      raise ArgumentError, 'native runtime resolves inside a target tree' if forbidden.any? { |root| path == root || path.start_with?(root + '/') }
      elf(path, machine(triple))
      info = dynamic(path, readelf)
      raise ArgumentError, 'native runtime filename differs from its SONAME' unless info[:soname] == name
      { 'name' => name, 'source' => path, 'path' => "native/lib/#{name}",
        'sha256' => Digest::SHA256.file(path).hexdigest, 'needed' => info[:needed] }
    end
    needed = dynamic(binary, readelf).fetch(:needed) + files.flat_map { |file| file.fetch('needed') }
    raise ArgumentError, 'native runtime closure is incomplete' unless (needed - paths.keys).empty?
    reachable = [loader_name, *dynamic(binary, readelf).fetch(:needed)]
    loop do
      more = files.select { |file| reachable.include?(file['name']) }.flat_map { |file| file['needed'] }
      break if (more - reachable).empty?
      reachable |= more
    end
    raise ArgumentError, 'native loader reports an unexplained library' unless paths.keys.sort == reachable.sort
    FileUtils.mkdir_p("#{work}/native/lib")
    files.each do |file|
      FileUtils.cp(file.fetch('source'), "#{work}/#{file.fetch('path')}")
      File.chmod(0755, "#{work}/#{file.fetch('path')}")
      raise ArgumentError, 'native runtime changed while copying' unless Digest::SHA256.file(file.fetch('source')).hexdigest == file.fetch('sha256')
    end
    receipt = {'format' => 'ember-llvm-native-runtime-v1', 'triple' => triple, 'loader' => "native/lib/#{loader_name}",
      'files' => files, 'tools' => [readelf, ldd].to_h { |p| [p, Digest::SHA256.file(p).hexdigest] }, 'original_loader_output' => trace}
    verify(binary, work, receipt)
    receipt
  end

  def verify(binary, work, receipt)
    raise ArgumentError, 'unsupported native runtime receipt' unless receipt.fetch('format') == 'ember-llvm-native-runtime-v1'
    expected_machine = machine(receipt.fetch('triple'))
    elf(binary, expected_machine)
    files = receipt.fetch('files')
    raise ArgumentError, 'duplicate native runtime payload' unless files.map { |f| f.fetch('name') }.uniq.length == files.length
    expected = files.to_h do |file|
      name = file.fetch('name')
      relative = file.fetch('path')
      raise ArgumentError, 'unsafe retained native runtime path' unless name.match?(/\A[A-Za-z0-9_+.-]+\z/) && !name.include?('..') && relative == "native/lib/#{name}"
      path = "#{File.realpath(work)}/#{relative}"
      raise ArgumentError, 'retained native runtime changed' unless File.file?(path) && !File.symlink?(path) && Digest::SHA256.file(path).hexdigest == file.fetch('sha256')
      raise ArgumentError, 'retained native runtime escapes the payload' unless File.realpath(path) == path
      elf(path, expected_machine)
      [name, File.realpath(path)]
    end
    loader = receipt.fetch('loader')
    raise ArgumentError, 'retained native loader is not in the payload' unless files.any? { |f| f['path'] == loader }
    text = capture("#{work}/#{loader}", '--inhibit-cache', '--library-path', "#{work}/native/lib", '--list', binary, env: {'LD_LIBRARY_PATH' => nil})
    raise ArgumentError, 'retained loader resolves outside the copied native closure' unless loaded(text) == expected
    text
  end

  def copy(binary, old, work, receipt, copied_binary:)
    verify(binary, old, receipt)
    receipt.fetch('files').each do |file|
      destination = "#{work}/#{file.fetch('path')}"
      raise ArgumentError, 'native runtime destination exists' if File.exist?(destination) || File.symlink?(destination)
      FileUtils.mkdir_p(File.dirname(destination))
      FileUtils.cp("#{old}/#{file.fetch('path')}", destination)
      File.chmod(0755, destination)
    end
    verify(copied_binary, work, receipt)
  end

  def launcher(receipt)
    return 'exec "$base/bin/llvm-config.real" "$@"' unless receipt
    loader = receipt.fetch('loader')
    raise ArgumentError, 'unsafe native launcher loader' unless loader.match?(%r{\Anative/lib/[A-Za-z0-9_+.-]+\z}) && !loader.include?('..')
    "unset LD_PRELOAD LD_AUDIT LD_LIBRARY_PATH\nexec \"$base/#{loader}\" --inhibit-cache --library-path \"$base/native/lib\" \"$base/bin/llvm-config.real\" \"$@\""
  end
end
