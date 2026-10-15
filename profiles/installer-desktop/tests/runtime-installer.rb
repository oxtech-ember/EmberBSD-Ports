#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Real native package and cross-linked ELF fixtures.
require 'minitest/autorun'
require 'tmpdir'
require 'fileutils'
require 'json'
require 'digest'
require 'open3'
require 'rbconfig'
require_relative '../../development-toolchain/runtime/recipe/files/runtime'

class RuntimeInstallerTest < Minitest::Test
  TOOLS = ENV.fetch('CROSS_BIN')
  ROOTS = %w[/bin/sh /bin/tar /usr/bin/tar /usr/bin/sha512 /usr/bin/cmp /usr/bin/id /usr/sbin/pkg_add /usr/sbin/pkg_info].freeze
  def run!(*args)
    out, err, status = Open3.capture3({ 'COPYFILE_DISABLE' => '1', 'XZ_OPT' => '-0' }, *args)
    assert status.success?, "#{args.inspect}\n#{out}#{err}"
    out
  end

  def setup
    @tmp = Dir.mktmpdir('ikar-runtime-installer-')
    @builder = File.expand_path('../bundle-gcc16.rb', __dir__)
    @auditor = File.expand_path('../audit-bootstrap.rb', __dir__)
    @object = @tmp + '/empty.o'
    File.write(@tmp + '/empty.s', ".text\n.global _start\n_start:\n ret\n.section .note.GNU-stack,\"\",@progbits\n")
    run!(TOOLS + 'as', '-o', @object, @tmp + '/empty.s')
  end

  def teardown
    FileUtils.remove_entry(@tmp)
  end

  def elf(path, soname: nil, needed: [], library: nil, rpath: nil, executable: false)
    FileUtils.mkdir_p(File.dirname(path))
    args = [TOOLS + 'ld', '-o', path, @object]
    args += executable ? ['-e', '_start', '--dynamic-linker', '/libexec/ld.elf_so'] : ['-shared']
    args += ['-soname', soname] if soname
    args += ['-rpath', rpath] if rpath
    args += ['-L', library, '--no-as-needed', *needed.map { |n| '-l:' + n }] unless needed.empty?
    run!(*args)
    File.chmod(0755, path)
  end

  class FixtureStage
    attr_reader :result
    def initialize(payload, result)
      @payload = payload; @result = result
    end
    def verify = @result
    def install(dest)
      FileUtils.mkdir_p(dest + '/usr/pkg')
      FileUtils.cp_r(Dir.children(@payload).map { |n| @payload + '/' + n }, dest + '/usr/pkg', preserve: true)
      @result
    end
  end

  def package
    payload = @tmp + '/payload'
    lib = payload + '/gcc16/lib'
    elf(lib + '/libgcc_s.so.1', soname: 'libgcc_s.so.1', rpath: '/usr/pkg/gcc16/lib')
    elf(lib + '/libstdc++.so.7.36', soname: 'libstdc++.so.7', needed: ['libgcc_s.so.1'], library: lib, rpath: '/usr/pkg/gcc16/lib')
    File.symlink('libstdc++.so.7.36', lib + '/libstdc++.so.7')
    GCC16Runtime::LICENSES.each do |name|
      FileUtils.mkdir_p(payload + '/share/licenses/gcc16-runtime')
      File.write(payload + '/share/licenses/gcc16-runtime/' + name, 'License fixture ' + name)
    end
    files = %w[gcc16/lib/libgcc_s.so.1 gcc16/lib/libstdc++.so.7 gcc16/lib/libstdc++.so.7.36]
    metadata = { 'OPSYS' => 'NetBSD', 'OS_VERSION' => '11.0', 'MACHINE_ARCH' => 'x86_64', 'PKGPATH' => 'lang/gcc16-runtime',
      'PKGNAME' => 'gcc16-runtime-16.2.0nb1', 'LICENSE' => 'gnu-gpl-v3', 'GCC_VERSION' => '16.2.0', 'GCC_RUNTIME_SONAME' => 'libstdc++.so.7',
      'GCC_SOURCE_SHA256' => GCC16Runtime::SOURCE_SHA256, 'EMBERBSD_SEED_SOURCE' => 'b' * 40 }
    %w[GCC_RECIPE_SHA256 GCC_RECIPE_DISTINFO_SHA256 GCC_RUNTIME_INPUTS_SHA256 GCC_RUNTIME_STAGE_SHA256 GCC_RUNTIME_LINKS_SHA256].each { |key| metadata[key] = 'a' * 64 }
    result = { files: files, metadata: metadata, elf: files.to_h { |p| [p, GCC16Runtime::ELF.new(payload + '/' + p).verify(p.include?('stdc++') ? 'libstdc++.so.7' : 'libgcc_s.so.1')] } }
    @source = @tmp + '/created'
    GCC16Runtime.create(FixtureStage.new(payload, result), ENV.fetch('PKG_CREATE'), @source)
    @pkg = @source + '/gcc16-runtime-16.2.0nb1.tgz'
    @output = @tmp + '/bundle'
  end

  def bundle
    Open3.capture3({ 'BSDTAR' => ENV.fetch('BSDTAR', 'bsdtar'), 'COPYFILE_DISABLE' => '1', 'XZ_OPT' => '-0' }, RbConfig.ruby, @builder, @source, @output)
  end

  def change_package
    d = @tmp + '/unpacked'; Dir.mkdir(d)
    run!('tar', '-xf', @pkg, '-C', d)
    yield d
    members = Dir.glob(d + '/**/*', File::FNM_DOTMATCH).select { |p| File.file?(p) || File.symlink?(p) }.map { |p| p.delete_prefix(d + '/') }
    run!('tar', '--no-xattrs', '--no-acls', '--no-fflags', '-czf', @pkg, '-C', d, *members)
    File.write(@source + '/package.sha256', "#{Digest::SHA256.file(@pkg).hexdigest}  gcc16-runtime-16.2.0nb1.tgz\n")
  end

  def test_bundle_preserves_create_package_and_installer_contract
    package
    before = Dir.children(@source).to_h { |n| [n, Digest::SHA256.file(@source + '/' + n).hexdigest] }
    out, err, status = bundle
    assert status.success?, out + err
    d = @tmp + '/bundle-inner'; Dir.mkdir(d)
    archive = @output + '/runtime-gcc16.tar.xz'
    run!('tar', '-xf', archive, '-C', d)
    assert_equal "gcc16\n", File.read(d + '/PROFILE')
    assert_equal "gcc16-runtime-16.2.0nb1\n", File.read(d + '/ROOTS')
    assert_equal File.binread(@pkg), File.binread(d + '/All/gcc16-runtime-16.2.0nb1.tgz')
    assert_equal "SHA512 (gcc16-runtime-16.2.0nb1.tgz) = #{Digest::SHA512.file(@pkg).hexdigest}\n", File.read(d + '/SHA512')
    assert_equal "SHA512 (runtime-gcc16.tar.xz) = #{Digest::SHA512.file(archive).hexdigest}\n", File.read(@output + '/SHA512')
    assert_operator File.size(archive), :<=, 64 * 1024 * 1024
    listing = run!('tar', '-tvf', archive)
    assert_match(/root\s+wheel/, listing)
    refute_match(/AppleDouble|SCHILY.xattr|\.DS_Store/, listing)
    assert_equal before, Dir.children(@source).to_h { |n| [n, Digest::SHA256.file(@source + '/' + n).hexdigest] }
    receipt = JSON.parse(File.read(@output + '/PROVENANCE.json'))
    assert_equal Digest::SHA256.file(@pkg).hexdigest, receipt.fetch('package').fetch('sha256')
  end

  def test_bundle_rejects_changed_digest
    package
    File.open(@pkg, 'ab') { |f| f.write('changed') }
    _out, _err, status = bundle
    refute status.success?
    refute File.exist?(@output)
  end

  def test_bundle_rejects_missing_invalid_or_unrecognized_pkgtools_receipts
    package
    receipt = @source + '/provenance.json'
    original = File.read(receipt)
    changes = [
      ->(m) { m.delete('PKGTOOLS_VERSION') },
      ->(m) { m['PKGTOOLS_VERSION'] = '20260230' },
      ->(m) { m['PKGTOOLS_VERSION'] = '20260227nb1' },
      ->(m) { m['EMBERBSD_PKG_CREATE_SHA256'] = 'invalid' },
      ->(m) { m['UNREVIEWED_METADATA'] = 'extra' }
    ]
    changes.each do |change|
      value = JSON.parse(original); change.call(value.fetch('metadata'))
      File.write(receipt, JSON.generate(value))
      _out, _err, status = bundle
      refute status.success?
      refute File.exist?(@output)
    end
  end

  def test_bundle_rejects_duplicate_pkgtools_version_in_package
    package
    change_package { |d| File.open(d + '/+BUILD_INFO', 'a') { |io| io.puts 'PKGTOOLS_VERSION=20260227' } }
    _out, _err, status = bundle
    refute status.success?
    refute File.exist?(@output)
  end

  def test_bundle_rejects_changed_pkg_create_hash_in_package
    package
    change_package { |d| p = d + '/+BUILD_INFO'; File.write(p, File.read(p).sub(/^EMBERBSD_PKG_CREATE_SHA256=.*$/, 'EMBERBSD_PKG_CREATE_SHA256=' + 'a' * 64)) }
    _out, _err, status = bundle
    refute status.success?
    refute File.exist?(@output)
  end

  def test_bundle_reaudits_architecture_even_with_updated_digest
    package
    change_package { |d| p = d + '/gcc16/lib/libgcc_s.so.1'; bytes = File.binread(p); bytes[18, 2] = [183].pack('v'); File.binwrite(p, bytes) }
    _out, _err, status = bundle
    refute status.success?
    refute File.exist?(@output)
  end

  def test_bundle_rejects_development_payload
    package
    change_package { |d| File.write(d + '/gcc16/lib/crtbegin.o', 'unshipped development object') }
    _out, _err, status = bundle
    refute status.success?
  end

  def test_bundle_rejects_missing_conflicts
    package
    change_package { |d| File.write(d + '/+CONTENTS', File.read(d + '/+CONTENTS').lines.reject { |l| l.start_with?('@pkgcfl ') }.join) }
    _out, _err, status = bundle
    refute status.success?
  end

  def test_bundle_rejects_wrong_receipt_and_preserves_existing_destination
    package
    receipt = @source + '/provenance.json'
    File.write(receipt, File.read(receipt).sub('x86_64', 'aarch64'))
    _out, _err, status = bundle
    refute status.success?
    Dir.mkdir(@output); File.write(@output + '/keep', 'keep')
    _out, _err, status = bundle
    refute status.success?
    assert_equal 'keep', File.read(@output + '/keep')
  end

  def bootstrap
    @dest = @tmp + '/dest'
    elf(@dest + '/usr/lib/libc.so.12', soname: 'libc.so.12')
    elf(@dest + '/usr/lib/libutil.so.7', soname: 'libutil.so.7', needed: ['libc.so.12'], library: @dest + '/usr/lib')
    elf(@dest + '/libexec/ld.elf_so')
    ROOTS.each { |p| elf(@dest + p, executable: true, needed: ['libutil.so.7'], library: @dest + '/usr/lib') }
    File.rename(@dest + '/usr/bin/sha512', @dest + '/usr/bin/cksum')
    File.symlink('/usr/bin/cksum', @dest + '/usr/bin/sha512')
    File.unlink(@dest + '/bin/tar'); File.symlink('../usr/bin/tar', @dest + '/bin/tar')
  end

  def audit
    Open3.capture3(RbConfig.ruby, @auditor, @dest, TOOLS + 'readelf')
  end

  def test_bootstrap_follows_target_symlinks_interpreter_and_recursive_needed
    bootstrap
    before = Dir.glob(@dest + '/**/*').select { |p| File.file?(p) && !File.symlink?(p) }.to_h { |p| [p, Digest::SHA256.file(p).hexdigest] }
    out, err, status = audit
    assert status.success?, out + err
    report = JSON.parse(out)
    assert_equal ROOTS, report.fetch('roots')
    assert_includes report.fetch('files').keys, '/usr/lib/libc.so.12'
    assert_includes report.fetch('files').keys, '/libexec/ld.elf_so'
    assert_equal before, before.keys.to_h { |p| [p, Digest::SHA256.file(p).hexdigest] }
  end

  def test_bootstrap_rejects_missing_transitive_library
    bootstrap
    File.unlink(@dest + '/usr/lib/libc.so.12')
    _out, _err, status = audit
    refute status.success?
  end

  def test_bootstrap_rejects_foreign_elf
    bootstrap
    p = @dest + '/usr/lib/libc.so.12'; bytes = File.binread(p); bytes[18, 2] = [183].pack('v'); File.binwrite(p, bytes)
    _out, _err, status = audit
    refute status.success?
  end

  def test_bootstrap_rejects_symlink_escape
    bootstrap
    File.unlink(@dest + '/usr/lib/libc.so.12'); File.symlink('../../../../outside', @dest + '/usr/lib/libc.so.12')
    _out, _err, status = audit
    refute status.success?
  end

  def test_bootstrap_rejects_shared_stdcpp
    bootstrap
    elf(@dest + '/usr/lib/libstdc++.so.7', soname: 'libstdc++.so.7')
    elf(@dest + '/usr/sbin/pkg_add', executable: true, needed: ['libstdc++.so.7'], library: @dest + '/usr/lib')
    _out, _err, status = audit
    refute status.success?
  end

  def test_bootstrap_rejects_pkg_runtime_search_path
    bootstrap
    elf(@dest + '/usr/sbin/pkg_add', executable: true, needed: ['libutil.so.7'], library: @dest + '/usr/lib', rpath: '/usr/pkg/gcc16/lib')
    _out, _err, status = audit
    refute status.success?
  end

  def test_bootstrap_rejects_source_text_instead_of_elf
    bootstrap
    File.write(@dest + '/usr/sbin/pkg_info', 'int main(void) { return 0; }')
    _out, _err, status = audit
    refute status.success?
  end
  def test_bundle_rejects_missing_license
    package
    change_package { |d| File.unlink(d + '/share/licenses/gcc16-runtime/COPYING.RUNTIME') }
    _out, err, status = bundle
    refute status.success?
    assert_match(/payload|license/, err)
  end

  def test_bundle_rejects_payload_digest_changes
    package
    change_package { |d| File.open(d + '/gcc16/lib/libgcc_s.so.1', 'ab') { |f| f.write('changed payload') } }
    _out, err, status = bundle
    refute status.success?
    assert_match(/payload digest mismatch/, err)
  end

  def test_bundle_rejects_install_commands
    package
    change_package { |d| File.open(d + '/+CONTENTS', 'a') { |f| f.write("@exec touch /tmp/unsafe\n") } }
    _out, err, status = bundle
    refute status.success?
    assert_match(/packing-list/, err)
  end

  def test_bundle_rejects_symlink_escape
    package
    change_package do |d|
      File.unlink(d + '/gcc16/lib/libstdc++.so.7')
      File.symlink('/usr/pkg/gcc16/lib/libstdc++.so.7.36', d + '/gcc16/lib/libstdc++.so.7')
    end
    _out, err, status = bundle
    refute status.success?
    assert_match(/alias/, err)
  end

  def test_bundle_rejects_wrong_package_target
    package
    change_package { |d| p = d + '/+BUILD_INFO'; File.write(p, File.read(p).sub('MACHINE_ARCH=x86_64', 'MACHINE_ARCH=aarch64')) }
    _out, err, status = bundle
    refute status.success?
    assert_match(/metadata/, err)
  end

  def test_bundle_has_a_hard_capacity_gate
    require 'securerandom'
    package
    change_package do |d|
      file = d + '/gcc16/lib/libgcc_s.so.1'
      old = Digest::MD5.file(file).hexdigest
      File.open(file, 'ab') { |f| 65.times { f.write(SecureRandom.random_bytes(1024 * 1024)) } }
      plist = d + '/+CONTENTS'
      File.write(plist, File.read(plist).sub(old, Digest::MD5.file(file).hexdigest))
    end
    _out, err, status = bundle
    refute status.success?
    assert_match(/64 MiB/, err)
    refute File.exist?(@output)
  end

  def test_bundle_preserves_dangling_output_link
    package
    File.symlink('missing', @output)
    _out, err, status = bundle
    refute status.success?
    assert_match(/already exists/, err)
    assert_equal 'missing', File.readlink(@output)
  end

  def test_bundle_rejects_output_inside_source
    package
    @output = @source + '/nested'
    _out, err, status = bundle
    refute status.success?
    assert_match(/outside/, err)
    refute File.exist?(@output)
  end

  def test_bundle_publication_never_overwrites_a_competing_output
    package
    jobs = 2.times.map { Thread.new { bundle } }
    results = jobs.map(&:value)
    assert_equal [false, true], results.map { |r| r.last.success? }.sort_by { |v| v ? 1 : 0 }
    archive = @output + '/runtime-gcc16.tar.xz'
    assert_equal "SHA512 (runtime-gcc16.tar.xz) = #{Digest::SHA512.file(archive).hexdigest}\n", File.read(@output + '/SHA512')
  end

  def test_bootstrap_rejects_missing_loader
    bootstrap
    File.unlink(@dest + '/libexec/ld.elf_so')
    _out, err, status = audit
    refute status.success?
    assert_match(/Missing bootstrap dependency/, err)
  end

  def test_bootstrap_rejects_non_executable_program
    bootstrap
    File.chmod(0644, @dest + '/bin/sh')
    _out, err, status = audit
    refute status.success?
    assert_match(/not executable/, err)
  end

  def test_bootstrap_rejects_library_link_into_package_runtime
    bootstrap
    FileUtils.mkdir_p(@dest + '/usr/pkg/gcc16/lib')
    File.rename(@dest + '/usr/lib/libc.so.12', @dest + '/usr/pkg/gcc16/lib/libc.so.12')
    File.symlink('/usr/pkg/gcc16/lib/libc.so.12', @dest + '/usr/lib/libc.so.12')
    _out, err, status = audit
    refute status.success?
    assert_match(/Non-base dependency/, err)
  end

  def test_bootstrap_rejects_library_symlink_cycle
    bootstrap
    File.unlink(@dest + '/usr/lib/libc.so.12')
    File.symlink('cycle', @dest + '/usr/lib/libc.so.12')
    File.symlink('libc.so.12', @dest + '/usr/lib/cycle')
    _out, err, status = audit
    refute status.success?
    assert_match(/cycle/, err)
  end

  def test_bootstrap_rejects_stdcpp_under_a_different_library_name
    bootstrap
    elf(@dest + "/usr/lib/libhelper.so.1", soname: "libhelper.so.1")
    elf(@dest + "/usr/sbin/pkg_add", executable: true, needed: ["libhelper.so.1"], library: @dest + "/usr/lib")
    p = @dest + "/usr/lib/libhelper.so.1"
    File.binwrite(p, File.binread(p).sub("libhelper.so.1", "libstdc++.so.7"))
    _out, err, status = audit
    refute status.success?
    assert_match(/shared runtime/, err)
  end

  def test_bootstrap_rejects_nonbase_loader_hints
    bootstrap
    FileUtils.mkdir_p(@dest + "/etc")
    File.write(@dest + "/etc/ld.so.conf", "/usr/pkg/gcc16/lib\n")
    _out, err, status = audit
    refute status.success?
    assert_match(/Non-base dependency/, err)
  end

  def test_bootstrap_audits_base_loader_hints_before_default_directories
    bootstrap
    FileUtils.mkdir_p(@dest + "/etc")
    File.write(@dest + "/etc/ld.so.conf", "# fixture\n/usr/libexec/bootstrap\n")
    elf(@dest + "/usr/libexec/bootstrap/libc.so.12", soname: "libc.so.12")
    p = @dest + "/usr/libexec/bootstrap/libc.so.12"; bytes = File.binread(p); bytes[18, 2] = [183].pack("v"); File.binwrite(p, bytes)
    _out, err, status = audit
    refute status.success?
    assert_match(/Foreign/, err)
  end

  def test_bootstrap_accepts_static_base_executables
    bootstrap
    ROOTS.each do |p|
      File.unlink(@dest + p)
      run!(TOOLS + "ld", "-e", "_start", "-o", @dest + p, @object)
    end
    out, err, status = audit
    assert status.success?, out + err
    report = JSON.parse(out)
    assert report.fetch("files").values.all? { |v| v.fetch("needed").empty? }
    refute_includes report.fetch("files").keys, "/usr/lib/libc.so.12"
  end

  def test_bootstrap_rejects_header_only_elf
    bootstrap
    bytes = "\x7fELF\x02\x01\x01".b.ljust(64, "\0")
    bytes[16, 4] = [2, 62].pack("vv")
    bytes[20, 4] = [1].pack("V")
    bytes[52, 2] = [64].pack("v")
    File.binwrite(@dest + "/bin/sh", bytes)
    _out, err, status = audit
    refute status.success?
    assert_match(/non-loadable/, err)
  end

  def test_bootstrap_rejects_ambiguous_runtime_search_tags
    bootstrap
    elf(@dest + '/usr/libexec/alt/libutil.so.7', soname: 'libutil.so.7')
    p = @dest + '/usr/libexec/alt/libutil.so.7'
    bytes = File.binread(p); bytes[18, 2] = [183].pack('v'); File.binwrite(p, bytes)
    program = @dest + '/usr/sbin/pkg_add'
    elf(program, executable: true, soname: '/usr/lib', rpath: '/usr/libexec/alt', needed: ['libutil.so.7'], library: @dest + '/usr/lib')
    strings = run!(TOOLS + 'readelf', '-p', '.dynstr', program)
    index = strings[/\[\s*([0-9a-f]+)\]\s+\/usr\/lib\s*$/, 1].to_i(16)
    original = [14, index].pack('Q<Q<') # DT_SONAME, now converted into a second search tag.
    bytes = File.binread(program)
    assert_equal 1, bytes.split(original, -1).length - 1
    File.binwrite(program, bytes.sub(original) { [15, index].pack('Q<Q<') })
    _out, err, status = audit
    refute status.success?
    assert_match(/Ambiguous.*path/, err)
  end

end
