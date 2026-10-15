# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted runtime packaging regression.
require 'minitest/autorun'
require 'tmpdir'
require 'fileutils'
require 'digest'
require 'json'
require_relative '../recipe/files/runtime'

class RuntimePackageTest < Minitest::Test
  def elf(soname, machine = 62, needed = ['libc.so.12'])
    names = [soname, *needed, '/usr/pkg/gcc16/lib']
    strings = "\0".b
    indexes = names.map { |s| n = strings.bytesize; strings << s << "\0"; n }
    dynamic = [[5, 0x400200], [10, strings.bytesize], [14, indexes[0]], [29, indexes[-1]]]
    needed.each_index { |i| dynamic << [1, indexes[i + 1]] }
    dynamic << [0, 0]
    data = "\0".b * 512
    data[0, 16] = "\x7fELF\x02\x01\x01".b.ljust(16, "\0")
    data[16, 48] = [3, machine, 1, 0, 64, 0, 0, 64, 56, 2, 0, 0, 0].pack('vvVQ<Q<Q<Vvvvvvv')
    bytes = dynamic.map { |tag, value| [tag, value].pack('Q<Q<') }.join
    total = 512 + strings.bytesize
    data[64, 56] = [1, 4, 0, 0x400000, 0x400000, total, total, 4096].pack('VVQ<Q<Q<Q<Q<Q<')
    data[120, 56] = [2, 4, 256, 0x400100, 0x400100, bytes.bytesize, bytes.bytesize, 8].pack('VVQ<Q<Q<Q<Q<Q<')
    data[256, bytes.bytesize] = bytes
    data + strings
  end

  def with_fixture
    Dir.mktmpdir('gcc-runtime-test-') do |d|
      @work = d + '/work'; @pkgsrc = d + '/pkgsrc'; @stage = @work + '/stage'
      @source = d + '/gcc.tar.xz'
      FileUtils.mkdir_p(@stage + '/usr/pkg/gcc16/lib')
      FileUtils.mkdir_p(@pkgsrc + '/lang/gcc16/patches')
      FileUtils.mkdir_p(d + '/gcc-16.2.0')
      %w[COPYING3 COPYING.RUNTIME].each { |f| File.write(d + '/gcc-16.2.0/' + f, 'License fixture: ' + f) }
      raise 'tar fixture failed' unless system('tar', '-cJf', @source, '-C', d, 'gcc-16.2.0')
      @archive_sha = Digest::SHA256.file(@source).hexdigest
      %w[distinfo Makefile Makefile.common].each { |n| File.write(@pkgsrc + '/lang/gcc16/' + n, n) }
      File.write(@work + '/build-success', "runtime-only-bootstrap\n")
      File.write(@stage + '/usr/pkg/gcc16/lib/libgcc_s.so.1', elf('libgcc_s.so.1'))
      File.write(@stage + '/usr/pkg/gcc16/lib/libstdc++.so.7.36', elf('libstdc++.so.7', 62, %w[libc.so.12 libgcc_s.so.1]))
      File.symlink('libstdc++.so.7.36', @stage + '/usr/pkg/gcc16/lib/libstdc++.so.7')
      FileUtils.mkdir_p(@stage + '/usr/pkg/gcc16/include/c++')
      File.write(@stage + '/usr/pkg/gcc16/include/c++/vector', 'build-only header')
      write_receipts
      yield d
    end
  end

  def write_receipts
    inputs = "scope=runtime-only-bootstrap\ntarget=amd64\ntriplet=x86_64--netbsd\nseed_source=#{'b' * 40}\n"
    inputs << "#{@archive_sha}  #{@source}\n"
    %w[distinfo Makefile Makefile.common].each do |n|
      path = @pkgsrc + '/lang/gcc16/' + n
      inputs << "#{Digest::SHA256.file(path).hexdigest}  #{path}\n"
    end
    File.write(@work + '/inputs.txt', inputs)
    regular = []; links = []
    Dir.glob(@stage + '/**/*').sort.each do |path|
      rel = './' + path.delete_prefix(@stage + '/')
      if File.symlink?(path)
        links << "#{rel}\t#{File.readlink(path)}\n"
      elsif File.file?(path)
        regular << "#{Digest::SHA256.file(path).hexdigest}  #{rel}\n"
      end
    end
    File.write(@work + '/stage.sha256', regular.join)
    File.write(@work + '/stage.symlinks', links.join)
  end

  def stage
    GCC16Runtime::Stage.new(@work, @pkgsrc, @source, expected_source: @archive_sha)
  end

  def test_select_only_target_runtime
    with_fixture do
      result = stage.verify
      assert_equal %w[gcc16/lib/libgcc_s.so.1 gcc16/lib/libstdc++.so.7 gcc16/lib/libstdc++.so.7.36], result.fetch(:files)
      assert_equal 'x86_64', result.fetch(:metadata).fetch('MACHINE_ARCH')
      assert_equal 'NetBSD', result.fetch(:metadata).fetch('OPSYS')
      assert_equal '11.0', result.fetch(:metadata).fetch('OS_VERSION')
    end
  end

  def test_fail_closed
    changes = {
      'target' => -> { File.write(@work + '/inputs.txt', File.read(@work + '/inputs.txt').sub('target=amd64', 'target=aarch64')) },
      'conflicting-target' => -> { File.write(@work + '/inputs.txt', File.read(@work + '/inputs.txt') + "target=aarch64\n") },
      'source' => -> { File.write(@work + '/inputs.txt', File.read(@work + '/inputs.txt').sub(@archive_sha, 'c' * 64)) },
      'recipe' => -> { File.write(@pkgsrc + '/lang/gcc16/distinfo', 'modified') },
      'mutation' => -> { File.write(@stage + '/usr/pkg/gcc16/lib/libgcc_s.so.1', 'modified') },
      'unrecorded' => -> { File.write(@stage + '/unexpected', 'unrecorded') },
      'truncated-elf' => -> { File.write(@stage + '/usr/pkg/gcc16/lib/libgcc_s.so.1', "\x7fELF"); write_receipts },
      'rpath' => -> { p = @stage + '/usr/pkg/gcc16/lib/libgcc_s.so.1'; File.binwrite(p, File.binread(p).sub('/usr/pkg/gcc16/lib', '/tmp/bad'.ljust('/usr/pkg/gcc16/lib'.bytesize, 'x'))); write_receipts },
      'arch' => -> { File.write(@stage + '/usr/pkg/gcc16/lib/libgcc_s.so.1', elf('libgcc_s.so.1', 183)); write_receipts },
      'soname' => -> { File.write(@stage + '/usr/pkg/gcc16/lib/libstdc++.so.7.36', elf('libstdc++.so.9')); write_receipts },
      'dependency' => -> { File.write(@stage + '/usr/pkg/gcc16/lib/libgcc_s.so.1', elf('libgcc_s.so.1', 62, ['libstdc++.so.9'])); write_receipts },
      'escape' => -> { File.unlink(@stage + '/usr/pkg/gcc16/lib/libstdc++.so.7'); File.symlink('/usr/lib/libstdc++.so.9', @stage + '/usr/pkg/gcc16/lib/libstdc++.so.7'); write_receipts },
      'indirect-unshipped-link' => -> { File.unlink(@stage + '/usr/pkg/gcc16/lib/libstdc++.so.7'); File.symlink('alias', @stage + '/usr/pkg/gcc16/lib/libstdc++.so.7'); File.symlink('libstdc++.so.7.36', @stage + '/usr/pkg/gcc16/lib/alias'); write_receipts },
      'unrecorded-link' => -> { File.write(@work + '/stage.symlinks', '') }
    }
    changes.each do |name, change|
      with_fixture { change.call; assert_raises(GCC16Runtime::Invalid, name) { stage.verify } }
    end
  end
  def test_real_native_package
    pkg_create = ENV['PKG_CREATE']
    skip 'Set PKG_CREATE to a native host tool' unless pkg_create
    with_fixture do |d|
      output = d + '/package'
      GCC16Runtime.create(stage, pkg_create, output)
      package = output + '/' + GCC16Runtime::NAME + '.tgz'
      list, status = Open3.capture2('tar', '-tf', package)
      assert status.success?
      assert_includes list, 'gcc16/lib/libstdc++.so.7'
      refute_match(%r{include|crtbegin|bin/gcc|[.]a$}, list)
      contents, status = Open3.capture2('tar', '-xOf', package, '+CONTENTS')
      assert status.success?
      assert_includes contents, '@pkgcfl gcc16-[0-9]*'
      assert_includes contents, '@pkgcfl gcc16-libs-[0-9]*'
      metadata, status = Open3.capture2('tar', '-xOf', package, '+BUILD_INFO')
      assert status.success?
      %w[OPSYS=NetBSD OS_VERSION=11.0 MACHINE_ARCH=x86_64].each { |line| assert_includes metadata, line }
      assert File.file?(output + '/package.sha256')
      assert File.file?(output + '/provenance.json')
      assert_raises(GCC16Runtime::Invalid) { GCC16Runtime.create(stage, pkg_create, output) }
    end
  end

  def test_source_pin_matches_owner
    pin = File.read(File.expand_path('../../sources.tsv', __dir__)).lines.find { |l| l.start_with?("gcc\t16.2.0\t") }.split("\t").last.strip
    assert_equal pin, GCC16Runtime::SOURCE_SHA256
  end

  def test_recipe_with_real_pkgsrc
    bmake = ENV['BMAKE']; pkgsrc = ENV['PKGSRC']
    skip 'Set BMAKE and PKGSRC for native recipe parsing' unless bmake && pkgsrc
    Dir.mktmpdir('gcc-runtime-recipe-', '/tmp') do |d|
      Dir.children(pkgsrc).each { |name| File.symlink(pkgsrc + '/' + name, d + '/' + name) unless name == 'lang' }
      FileUtils.mkdir_p(d + '/lang')
      Dir.children(pkgsrc + '/lang').each { |name| File.symlink(pkgsrc + '/lang/' + name, d + '/lang/' + name) unless name == 'gcc16-runtime' }
      FileUtils.cp_r(File.expand_path('../recipe', __dir__), d + '/lang/gcc16-runtime')
      out, err, status = Open3.capture3(bmake, '-C', d + '/lang/gcc16-runtime', '-v', 'PKGNAME', '-v', 'CONFLICTS', '-v', 'PKG_FAIL_REASON')
      assert status.success?, out + err
      assert_includes out, GCC16Runtime::NAME
      GCC16Runtime::CONFLICTS.each { |pattern| assert_includes out, pattern }
      %w[RUBY WORK ARCHIVE].each { |name| assert_includes out, "Set GCC16_RUNTIME_#{name}" }
      with_fixture do
        out, err, status = Open3.capture3(bmake, '-C', d + '/lang/gcc16-runtime', "GCC16_RUNTIME_RUBY=#{RbConfig.ruby}", "GCC16_RUNTIME_WORK=#{@work}", "GCC16_RUNTIME_ARCHIVE=#{@source}", "GCC16_RUNTIME_PKGSRC=#{@pkgsrc}", '-v', 'PKG_FAIL_REASON')
        assert status.success?, out + err
        assert_includes out, 'audited runtime provenance'
        assert_includes err, 'GCC source archive mismatch'
      end

    end
  end

end
