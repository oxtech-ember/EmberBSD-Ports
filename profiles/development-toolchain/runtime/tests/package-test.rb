# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted runtime packaging regression.
require 'minitest/autorun'
require 'tmpdir'
require 'fileutils'
require 'digest'
require 'json'
require_relative '../recipe/files/runtime'
require_relative '../recipe/files/inheritance'
require_relative '../recipe/files/relro'

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
    data[16, 48] = [3, machine, 1, 0, 64, 0, 0, 64, 56, 3, 0, 0, 0].pack('vvVQ<Q<Q<Vvvvvvv')
    bytes = dynamic.map { |tag, value| [tag, value].pack('Q<Q<') }.join
    total = 512 + strings.bytesize
    data[64, 56] = [1, 4, 0, 0x400000, 0x400000, total, total, 4096].pack('VVQ<Q<Q<Q<Q<Q<')
    data[120, 56] = [2, 4, 256, 0x400100, 0x400100, bytes.bytesize, bytes.bytesize, 8].pack('VVQ<Q<Q<Q<Q<Q<')
    data[176, 56] = [0x6474e552, 4, 256, 0x400100, 0x400100, bytes.bytesize, bytes.bytesize, 1].pack('VVQ<Q<Q<Q<Q<Q<')
    data[256, bytes.bytesize] = bytes
    data + strings
  end

  def with_fixture(target = 'amd64')
    Dir.mktmpdir('gcc-runtime-test-') do |d|
      @target = target
      @libraries = nil
      @triplet, @machine_arch, @elf_machine = case target
        when 'amd64' then ['x86_64--netbsd', 'x86_64', 62]
        when 'aarch64' then ['aarch64--netbsd', 'aarch64', 183]
        else raise 'Unsupported fixture target'
      end
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
      File.write(@stage + '/usr/pkg/gcc16/lib/libgcc_s.so.1', elf('libgcc_s.so.1', @elf_machine))
      File.write(@stage + '/usr/pkg/gcc16/lib/libstdc++.so.7.36', elf('libstdc++.so.7', @elf_machine, %w[libc.so.12 libgcc_s.so.1]))
      File.symlink('libstdc++.so.7.36', @stage + '/usr/pkg/gcc16/lib/libstdc++.so.7')
      FileUtils.mkdir_p(@stage + '/usr/pkg/gcc16/include/c++')
      File.write(@stage + '/usr/pkg/gcc16/include/c++/vector', 'build-only header')
      File.write(@stage + '/usr/pkg/gcc16/lib/libstdc++.so.7.36-gdb.py', 'build-only upstream debugger helper')
      write_receipts
      yield d
    end
  end

  def test_external_compiler_receipt_and_mutations
    %w[amd64 aarch64].each do |target|
      with_fixture(target) do
        File.write(@work + '/build-success', "runtime-only-external-compiler\n")
        prefix = '/fixture/compiler'
        receipt = "compiler_mode=external-posix\nversion=16.2.0\ntriplet=#{@triplet}\nthread_model=posix\nsupport_target=libgcc-support\ntarget_objects=external-compiler\ncompiler=#{prefix}\ncc1=#{prefix}/libexec/cc1\ncc1plus=#{prefix}/libexec/cc1plus\n"
        %W[#{prefix}/bin/#{@triplet}-gcc #{prefix}/bin/#{@triplet}-g++ #{prefix}/libexec/cc1 #{prefix}/libexec/cc1plus].each { |path| receipt << "#{'a' * 64}  #{path}\n" }
        plan = "support_target=libgcc-support\ntarget_objects=external-compiler\nCC=#{prefix}/bin/#{@triplet}-gcc --sysroot=/fixture/seed -B/fixture/work/build/gcc/\nCXX=#{prefix}/bin/#{@triplet}-gcc --sysroot=/fixture/seed -B/fixture/work/build/gcc/ -shared-libgcc -nostdinc++\n"
        compiler_path = @work + '/external-compiler.txt'
        plan_path = @work + '/external-runtime-plan.txt'
        File.write(compiler_path, receipt)
        File.write(plan_path, plan)
        inputs = File.read(@work + '/inputs.txt').sub('scope=runtime-only-bootstrap', 'scope=runtime-only-external-compiler') + "sysroot=/fixture/seed\n"
support = %w[libgcc.mvars specs tconfig.h version.h auto-host.h Makefile config.status].map { |name| @work + '/external-support/' + name }
        FileUtils.mkdir_p(@work + '/external-support')
        support.each { |path| File.write(path, 'generated support fixture') }
        [compiler_path, plan_path, *support].each { |path| inputs << "#{Digest::SHA256.file(path).hexdigest}  #{path}\n" }
        File.write(@work + '/inputs.txt', inputs)
        stage.verify
        File.write(compiler_path, receipt.sub('thread_model=posix', 'thread_model=single'))
        assert_raises(GCC16Runtime::Invalid) { stage.verify }
        File.write(compiler_path, receipt)
        changed = receipt.sub('thread_model=posix', 'thread_model=single')
        File.write(compiler_path, changed)
        File.write(@work + '/inputs.txt', inputs.sub(Digest::SHA256.hexdigest(receipt), Digest::SHA256.hexdigest(changed)))
        assert_raises(GCC16Runtime::Invalid) { stage.verify }
        File.write(compiler_path, receipt)
        File.write(@work + '/inputs.txt', inputs)
        File.write(plan_path, plan.sub('/fixture/seed', '/foreign/seed'))
        changed_inputs = inputs.sub(Digest::SHA256.hexdigest(plan), Digest::SHA256.file(plan_path).hexdigest)
        File.write(@work + '/inputs.txt', changed_inputs)
        assert_raises(GCC16Runtime::Invalid) { stage.verify }
        File.write(plan_path, plan)
        File.write(@work + '/inputs.txt', inputs)
        File.write(support.first, 'changed generated support')
        assert_raises(GCC16Runtime::Invalid) { stage.verify }
      end
    end
  end

  def write_receipts
    inputs = "scope=runtime-only-bootstrap\ntarget=#{@target}\ntriplet=#{@triplet}\nseed_source=#{'b' * 40}\n"
    inputs << "runtime_libraries=#{@libraries}\n" if @libraries
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

  def add_optional_libraries(selection)
    @libraries = selection
    selection.split(',').drop(2).each do |name|
      soname = GCC16Runtime::LIBRARIES.fetch(name)
      path = @stage + '/usr/pkg/gcc16/lib/' + soname
      File.binwrite(path + '.0', elf(soname, @elf_machine, %w[libpthread.so.1 libc.so.12]))
      File.symlink(soname + '.0', path)
      # Development files remain in the stage, never in the runtime package.
      File.symlink(soname, @stage + '/usr/pkg/gcc16/lib/' + name + '.so')
      File.write(@stage + '/usr/pkg/gcc16/lib/' + name + '.a', 'build-only archive')
    end
    write_receipts
  end

  def test_relro_is_mandatory_but_old_provenance_is_readable
    %w[amd64 aarch64].each do |target|
      with_fixture(target) do |dir|
        add_optional_libraries(GCC16Runtime::SELECTIONS.last)
        %w[libgcc_s.so.1 libstdc++.so.7.36 libgomp.so.1.0 libatomic.so.3.0].each do |name|
          path = @stage + '/usr/pkg/gcc16/lib/' + name
          original = File.binread(path)
          missing = original.dup
          missing[176, 4] = [0].pack('V')
          File.binwrite(path, missing); write_receipts
          error = assert_raises(GCC16Runtime::Invalid) { stage.verify }
          assert_match(/Missing GNU_RELRO/, error.message)
          historical = GCC16Runtime::Stage.new(@work, @pkgsrc, @source, expected_source: @archive_sha, historical: true)
          assert historical.verify
          error = assert_raises(GCC16Runtime::Invalid) { historical.install(dir + '/forbidden') }
          assert_match(/Historical provenance cannot be installed/, error.message)
          refute File.exist?(dir + '/forbidden')
          empty = original.dup
          empty[216, 8] = [0].pack('Q<')
          File.binwrite(path, empty); write_receipts
          error = assert_raises(GCC16Runtime::Invalid) { stage.verify }
          assert_match(/Invalid GNU_RELRO/, error.message)
          File.binwrite(path, original); write_receipts
        end
        assert stage.verify
      end
    end
  end

  # These are synthetic ELF/receipt refusal fixtures, never build evidence.
  def with_rebuild
    with_fixture('aarch64') do |dir|
      File.write(@pkgsrc + '/lang/gcc16/Makefile', "PKGREVISION=\t1\n")
      add_optional_libraries(GCC16Runtime::SELECTIONS.last)
      GCC16Runtime::Inheritance::CRT_FILES.each do |name|
        path = @stage + "/usr/pkg/gcc16/lib/gcc/#{@triplet}/16.2.0/#{name}"
        FileUtils.mkdir_p(File.dirname(path)); File.write(path, 'Receipt fixture, not real CRT: ' + name)
      end
      write_receipts
      parent = stage.verify
      work = dir + '/rebuild'; recipe = dir + '/new-recipe'
      FileUtils.mkdir_p(work)
      FileUtils.cp_r(@work, work + '/parent')
      FileUtils.cp_r(@pkgsrc, work + '/parent-recipe')
      FileUtils.cp_r(@pkgsrc, recipe)
      patch_name = GCC16Runtime::Inheritance::PATCH
      outer = File.read(File.expand_path('../../patches/gcc-netbsd-locale.patch', __dir__))
      patch = outer.split("+++ b/lang/gcc16/patches/#{patch_name}\n", 2).fetch(1).lines.drop(1).map do |line|
        raise 'Unexpected source patch format' unless line.start_with?('+')
        line.delete_prefix('+')
      end.join
      File.write(recipe + '/lang/gcc16/patches/' + patch_name, patch)
      File.write(recipe + '/lang/gcc16/Makefile', "PKGREVISION=\t2\n")
      sha1 = Digest::SHA1.hexdigest(patch.lines.reject { |l| l.match?(/[$]NetBSD.*/) }.join)
      File.write(recipe + '/lang/gcc16/distinfo', "SHA1 (#{patch_name}) = #{sha1}\n" + File.read(@pkgsrc + '/lang/gcc16/distinfo'))
      FileUtils.cp_r(@stage, work + '/stage')
      # Model a changed freshly installed DSO and all new C++ header ownership.
      File.open(work + '/stage/usr/pkg/gcc16/lib/libstdc++.so.7.36', 'ab') { |f| f.write('rebuilt ELF fixture') }
      locale = work + "/stage/usr/pkg/gcc16/include/c++/#{@triplet}/bits/c++locale.h"
      FileUtils.mkdir_p(File.dirname(locale)); File.write(locale, 'fresh header fixture')
      all = GCC16Runtime::Inheritance.inventory(work + '/stage')
      old = GCC16Runtime::Inheritance.inventory(work + '/parent/stage')
      inherited = GCC16Runtime::Inheritance.inherited_paths(parent).to_h { |p| [p, old.fetch(p)] }
      all.keys.grep(%r{/lib/(?:gcc/|libgcc|libgomp|libatomic)}).each do |path|
        next if inherited.key?(path)
        File.unlink(work + '/stage/' + path)
        all.delete(path)
      end
      fresh = all.reject { |p, _| inherited.key?(p) }
      logs = %w[configure.log runtime-build.log runtime-install.log].to_h do |name|
        File.write(work + '/' + name, 'Synthetic receipt fixture; no actual build')
        [name, Digest::SHA256.file(work + '/' + name).hexdigest]
      end
      configuration = GCC16Runtime::Inheritance::CONFIG_FILES.to_h do |name|
        path = work + '/' + name
        FileUtils.mkdir_p(File.dirname(path)); File.write(path, 'Synthetic configuration fixture; no actual build')
        [name, Digest::SHA256.file(path).hexdigest]
      end
      receipt = {format: 1, parent_paths: {archive: @source, pkgsrc: @pkgsrc},
        parent_receipts: GCC16Runtime::Inheritance::PARENT_FILES.to_h { |n| [n, Digest::SHA256.file(work + '/parent/' + n).hexdigest] },
        inherited: inherited, rebuilt: fresh, build_logs: logs, configuration: configuration}
      File.write(work + '/inheritance.json', JSON.pretty_generate(receipt) + "\n")
      inputs = "scope=runtime-libstdcxx-rebuild\ntarget=#{@target}\ntriplet=#{@triplet}\nseed_source=#{'b' * 40}\nruntime_libraries=#{@libraries}\n"
      ([ @source, work + '/inheritance.json' ] + configuration.keys.map { |n| work + '/' + n } + Dir.glob(recipe + '/lang/gcc16/{Makefile,Makefile.common,distinfo,patches/*}')).each do |path|
        inputs << "#{Digest::SHA256.file(path).hexdigest}  #{path}\n"
      end
      File.write(work + '/inputs.txt', inputs)
      File.write(work + '/build-success', "runtime-libstdcxx-rebuild\n")
      File.write(work + '/stage.sha256', all.sort.filter_map { |p, x| "#{x['sha256']}  ./#{p}\n" if x['sha256'] }.join)
      File.write(work + '/stage.symlinks', all.sort.filter_map { |p, x| "./#{p}\t#{x['link']}\n" if x['link'] }.join)
      yield GCC16Runtime::Stage.new(work, recipe, @source, expected_source: @archive_sha), work, recipe
    end
  end

  def test_rebuilt_components_and_historical_parent_paths
    with_rebuild do |rebuilt, work, _|
      result = rebuilt.verify
      assert_equal 'standalone-libstdcxx', result[:metadata]['GCC_RUNTIME_BUILD_MODE']
      assert_equal 7, result[:files].size
      # The copied original receipt still names the original recipe location.
      assert_equal File.read(@work + '/inputs.txt'), File.read(work + '/parent/inputs.txt')
      if GCC16Runtime::NAME == 'gcc16-runtime-16.2.0nb2'
        error = assert_raises(GCC16Runtime::Invalid) { rebuilt.install(work + '/package') }
        assert_match(/new package revision/, error.message)
      end
    end
  end

  def with_relink
    with_rebuild do |locale, parent, recipe|
      locale.verify
      work = File.dirname(parent) + '/relink'
      FileUtils.mkdir_p(work + '/proof')
      FileUtils.cp_r(parent + '/stage', work + '/stage')
      backup = work + '/backup-fixture'
      File.write(backup, 'Synthetic archived-input receipt, not a real compiler build')
      commands = []; components = {}
      GCC16Runtime::Relro::COMPONENTS.each do |library, name|
        path = 'usr/pkg/gcc16/lib/' + name
        before = work + '/proof/' + name + '.baseline'
        after = work + '/proof/' + name + '.relro'
        FileUtils.cp(parent + '/stage/' + path, before)
        File.binwrite(after, File.binread(before) + 'synthetic link-only receipt fixture')
        FileUtils.cp(after, work + '/stage/' + path)
        components[library] = {path: path, before: Digest::SHA256.file(before).hexdigest, after: Digest::SHA256.file(after).hexdigest}
        commands << {component: library, argv: ['/fixture/xgcc', '-shared', '-o', before], status: 0}
        commands << {component: library, argv: ['/fixture/xgcc', '-shared', '-o', after, '-Wl,-z,relro'], status: 0}
      end
      File.write(work + '/commands.json', JSON.pretty_generate(commands))
      receipt = {format: 1, parent_work: parent,
        parent_receipts: GCC16Runtime::Relro::PARENT.to_h { |n| [n, Digest::SHA256.file(parent + '/' + n).hexdigest] },
        backup: {path: backup, sha256: Digest::SHA256.file(backup).hexdigest},
        inputs: {work + '/commands.json' => Digest::SHA256.file(work + '/commands.json').hexdigest}, components: components}
      File.write(work + '/relink.json', JSON.pretty_generate(receipt))
      base_inputs = File.read(parent + '/inputs.txt').sub('scope=runtime-libstdcxx-rebuild', 'scope=runtime-relro-relink')
      repin = lambda do
        File.write(work + '/inputs.txt', base_inputs + "#{Digest::SHA256.file(work + '/relink.json').hexdigest}  #{work}/relink.json\n")
        all = GCC16Runtime::Inheritance.inventory(work + '/stage')
        File.write(work + '/stage.sha256', all.sort.filter_map { |p, x| "#{x['sha256']}  ./#{p}\n" if x['sha256'] }.join)
        File.write(work + '/stage.symlinks', all.sort.filter_map { |p, x| "./#{p}\t#{x['link']}\n" if x['link'] }.join)
      end
      repin.call
      File.write(work + '/build-success', "runtime-relro-relink\n")
      yield GCC16Runtime::Stage.new(work, recipe, @source, expected_source: @archive_sha), work, parent, repin
    end
  end

  def test_relink_receipt_preserves_distinct_component_ownership
    with_relink do |relinked, work, parent, _|
      result = relinked.verify
      assert_equal 'libstdcxx-and-runtime-relro-relink', result[:metadata]['GCC_RUNTIME_BUILD_MODE']
      assert_equal File.binread(parent + '/stage/usr/pkg/gcc16/lib/libstdc++.so.7.36'), File.binread(work + '/stage/usr/pkg/gcc16/lib/libstdc++.so.7.36')
    end
    %w[parent archive baseline output ownership command selection relative-input].each do |mutation|
      with_relink do |relinked, work, parent, repin|
        file = work + '/relink.json'
        receipt = JSON.parse(File.read(file))
        case mutation
        when 'parent' then File.write(parent + '/build-success', "runtime-relro-relink\n")
        when 'archive' then File.write(work + '/backup-fixture', 'changed')
        when 'baseline' then File.write(work + '/proof/libgcc_s.so.1.baseline', 'changed')
        when 'output' then File.write(work + '/proof/libgcc_s.so.1.relro', 'changed')
        when 'ownership' then File.write(work + '/stage/usr/pkg/gcc16/include/c++/vector', 'changed')
        when 'selection' then receipt['components'].delete('libatomic')
        when 'relative-input'
          receipt['inputs'] = {'commands.json' => receipt['inputs'].values.first}
        when 'command'
          path = work + '/commands.json'
          commands = JSON.parse(File.read(path)); commands[1]['argv'] << '-Wl,-z,now'
          File.write(path, JSON.pretty_generate(commands))
          receipt['inputs'][path] = Digest::SHA256.file(path).hexdigest
        end
        File.write(file, JSON.pretty_generate(receipt)); repin.call
        assert_raises(GCC16Runtime::Invalid, mutation) { relinked.verify }
      end
    end
  end

  def test_rebuild_refuses_component_and_provenance_drift
    %w[parent-receipt parent-payload parent-recipe new-patch new-recipe inherited rebuilt log configuration receipt scope nested-parent].each do |mutation|
      with_rebuild do |rebuilt, work, recipe|
        case mutation
        when 'parent-receipt' then File.write(work + '/parent/inputs.txt', 'changed')
        when 'parent-payload' then File.write(work + '/parent/stage/usr/pkg/gcc16/lib/libgcc_s.so.1', 'changed')
        when 'parent-recipe' then File.write(work + '/parent-recipe/lang/gcc16/Makefile.common', 'changed')
        when 'new-patch' then File.write(recipe + '/lang/gcc16/patches/' + GCC16Runtime::Inheritance::PATCH, 'changed')
        when 'new-recipe' then File.write(recipe + '/lang/gcc16/Makefile.common', 'changed')
        when 'inherited' then File.write(work + '/stage/usr/pkg/gcc16/lib/libgcc_s.so.1', 'changed')
        when 'rebuilt' then File.write(work + '/stage/usr/pkg/gcc16/include/c++/vector', 'changed')
        when 'log' then File.write(work + '/runtime-build.log', 'changed')
        when 'configuration' then File.write(work + '/configuration/config.h', 'changed')
        when 'receipt' then File.write(work + '/inheritance.json', '{}')
        when 'scope' then File.write(work + '/build-success', "runtime-only-bootstrap\n")
        when 'nested-parent'
          File.write(work + '/parent/build-success', "runtime-libstdcxx-rebuild\n")
        end
        assert_raises(GCC16Runtime::Invalid, mutation) { rebuilt.verify }
      end
    end
  end

  def test_rebuild_refuses_rehashed_false_ownership_and_old_dso
    %w[inherited-bytes missing-component old-dso].each do |mutation|
      with_rebuild do |rebuilt, work, _|
        receipt_path = work + '/inheritance.json'
        receipt = JSON.parse(File.read(receipt_path))
        if mutation == 'inherited-bytes'
          path = 'usr/pkg/gcc16/lib/libgcc_s.so.1'
          File.open(work + '/stage/' + path, 'ab') { |f| f.write('changed') }
        elsif mutation == 'missing-component'
          receipt.fetch('inherited').delete('usr/pkg/gcc16/lib/libgcc_s.so.1')
        else
          path = 'usr/pkg/gcc16/lib/libstdc++.so.7.36'
          FileUtils.cp(work + '/parent/stage/' + path, work + '/stage/' + path)
          receipt.fetch('rebuilt')[path] = GCC16Runtime::Inheritance.inventory(work + '/stage').fetch(path)
        end
        all = GCC16Runtime::Inheritance.inventory(work + '/stage')
        File.write(work + '/stage.sha256', all.sort.filter_map { |p, x| "#{x['sha256']}  ./#{p}\n" if x['sha256'] }.join)
        File.write(receipt_path, JSON.pretty_generate(receipt) + "\n")
        inputs = File.readlines(work + '/inputs.txt').reject { |l| l.end_with?('  ' + receipt_path + "\n") }.join
        File.write(work + '/inputs.txt', inputs + "#{Digest::SHA256.file(receipt_path).hexdigest}  #{receipt_path}\n")
        error = assert_raises(GCC16Runtime::Invalid, mutation) { rebuilt.verify }
        assert_match(/component|rebuilt libstdc/, error.message)
      end
    end
  end

  def test_optional_library_selection_and_abi
    %w[amd64 aarch64].each do |target|
      GCC16Runtime::SELECTIONS.each do |selection|
        with_fixture(target) do
          add_optional_libraries(selection)
          result = stage.verify
          sonames = selection.split(',').map { |name| GCC16Runtime::LIBRARIES.fetch(name) }
          assert_equal selection, result.fetch(:metadata).fetch('GCC_RUNTIME_LIBRARIES')
          assert_equal sonames.join(','), result.fetch(:metadata).fetch('GCC_RUNTIME_SONAMES')
          assert_equal sonames.sort, result.fetch(:elf).values.map { |row| row.fetch('soname') }.uniq.sort
          sonames.each { |name| assert_includes result.fetch(:files), 'gcc16/lib/' + name }
          refute result.fetch(:files).any? { |name| name.end_with?('.a', 'libgomp.so', 'libatomic.so') }
        end
      end
    end
  end

  def test_optional_library_refusals
    %w[amd64 aarch64].each do |target|
      %w[duplicate empty reordered unknown unterminated].each do |mutation|
        with_fixture(target) do
          add_optional_libraries(GCC16Runtime::SELECTIONS.last)
          path = @work + '/inputs.txt'
          text = File.read(path)
          text = case mutation
            when 'duplicate' then text + "runtime_libraries=#{@libraries}\n"
            when 'empty' then text.sub(@libraries, '')
            when 'reordered' then text.sub(@libraries, 'libgcc,libstdc++,libatomic,libgomp')
            when 'unknown' then text.sub(@libraries, 'libgcc,libstdc++,libquadmath')
            when 'unterminated' then text.lines.reject { |line| line.start_with?('runtime_libraries=') }.join + 'runtime_libraries=' + @libraries
          end
          File.write(path, text)
          assert_raises(GCC16Runtime::Invalid, mutation) { stage.verify }
        end
      end
      with_fixture(target) do
        add_optional_libraries(GCC16Runtime::SELECTIONS.last)
        @libraries = nil
        write_receipts
        error = assert_raises(GCC16Runtime::Invalid) { stage.verify }
        assert_match(/Unselected or foreign runtime ABI/, error.message)
      end
      %w[libgomp libatomic].each do |name|
        %w[missing soname architecture unshipped-link unselected-dependency second-abi].each do |mutation|
          with_fixture(target) do
            add_optional_libraries('libgcc,libstdc++,' + name)
            soname = GCC16Runtime::LIBRARIES.fetch(name)
            path = @stage + '/usr/pkg/gcc16/lib/' + soname
            case mutation
            when 'missing'
              File.unlink(path)
              File.unlink(@stage + '/usr/pkg/gcc16/lib/' + name + '.so')
            when 'soname' then File.binwrite(path + '.0', elf(name + '.so.2', @elf_machine))
            when 'architecture' then File.binwrite(path + '.0', elf(soname, @elf_machine == 62 ? 183 : 62))
            when 'unshipped-link'
              File.unlink(path)
              File.symlink('intermediate', path)
              File.symlink(soname + '.0', File.dirname(path) + '/intermediate')
            when 'unselected-dependency'
              other = name == 'libgomp' ? 'libatomic.so.3' : 'libgomp.so.1'
              File.binwrite(path + '.0', elf(soname, @elf_machine, [other]))
            when 'second-abi'
              File.binwrite(@stage + '/usr/pkg/gcc16/lib/' + name + '.so.2', elf(name + '.so.2', @elf_machine))
            end
            write_receipts
            assert_raises(GCC16Runtime::Invalid, "#{target}/#{name}/#{mutation}") { stage.verify }
          end
        end
      end
    end
  end

  def test_select_only_target_runtime
    with_fixture do
      result = stage.verify
      assert_equal %w[gcc16/lib/libgcc_s.so.1 gcc16/lib/libstdc++.so.7 gcc16/lib/libstdc++.so.7.36], result.fetch(:files)
      assert_equal 'x86_64', result.fetch(:metadata).fetch('MACHINE_ARCH')
      assert_equal 'NetBSD', result.fetch(:metadata).fetch('OPSYS')
      assert_equal '11.0', result.fetch(:metadata).fetch('OS_VERSION')
      assert_equal 'amd64', result.fetch(:metadata).fetch('GCC_RUNTIME_TARGET')
      assert_equal 'x86_64--netbsd', result.fetch(:metadata).fetch('GCC_RUNTIME_TRIPLET')
      assert_equal 'x86_64', result.fetch(:metadata).fetch('GCC_RUNTIME_MACHINE_ARCH')
      assert_equal ['x86_64'], result.fetch(:elf).values.map { |e| e.fetch('machine') }.uniq
    end
  end

  def test_select_aarch64_runtime
    with_fixture('aarch64') do
      result = stage.verify
      assert_equal %w[gcc16/lib/libgcc_s.so.1 gcc16/lib/libstdc++.so.7 gcc16/lib/libstdc++.so.7.36], result.fetch(:files)
      metadata = result.fetch(:metadata)
      assert_equal 'NetBSD', metadata.fetch('OPSYS')
      assert_equal '11.0', metadata.fetch('OS_VERSION')
      assert_equal 'aarch64', metadata.fetch('MACHINE_ARCH')
      assert_equal 'aarch64', metadata.fetch('GCC_RUNTIME_TARGET')
      assert_equal 'aarch64--netbsd', metadata.fetch('GCC_RUNTIME_TRIPLET')
      assert_equal 'aarch64', metadata.fetch('GCC_RUNTIME_MACHINE_ARCH')
      assert_equal ['aarch64'], result.fetch(:elf).values.map { |e| e.fetch('machine') }.uniq
    end
  end

  def test_target_claims_are_unique_and_consistent
    %w[amd64 aarch64].each do |target|
      changes = {
        'missing-target' => ->(s) { s.lines.reject { |l| l.start_with?('target=') }.join },
        'missing-triplet' => ->(s) { s.lines.reject { |l| l.start_with?('triplet=') }.join },
        'duplicate-target' => ->(s) { s + "target=#{@target}\n" },
        'duplicate-triplet' => ->(s) { s + "triplet=#{@triplet}\n" },
        'duplicate-scope' => ->(s) { s + "scope=runtime-only-bootstrap\n" },
        'wrong-triplet' => ->(s) { s.sub("triplet=#{@triplet}", "triplet=#{@target == 'amd64' ? 'aarch64' : 'x86_64'}--netbsd") },
        'noncanonical-triplet' => ->(s) { s.sub("triplet=#{@triplet}", "triplet=#{@machine_arch}-unknown-netbsd") },
        'unknown-target' => ->(s) { s.sub("target=#{@target}", 'target=arm64') }
      }
      changes.each do |name, change|
        with_fixture(target) do
          path = @work + '/inputs.txt'
          File.write(path, change.call(File.read(path)))
          assert_raises(GCC16Runtime::Invalid, "#{target}/#{name}") { stage.verify }
        end
      end
    end
  end

  def test_wrong_architecture_even_with_updated_receipts
    %w[amd64 aarch64].each do |target|
      %w[gcc-only cxx-only all].each do |selection|
        with_fixture(target) do
          wrong = @elf_machine == 62 ? 183 : 62
          if selection != 'cxx-only'
            File.binwrite(@stage + '/usr/pkg/gcc16/lib/libgcc_s.so.1', elf('libgcc_s.so.1', wrong))
          end
          if selection != 'gcc-only'
            File.binwrite(@stage + '/usr/pkg/gcc16/lib/libstdc++.so.7.36', elf('libstdc++.so.7', wrong))
          end
          write_receipts
          error = assert_raises(GCC16Runtime::Invalid, "#{target}/#{selection}") { stage.verify }
          assert_match(/Expected ELF64 little-endian #{@machine_arch} DSO/, error.message)
        end
      end
    end
  end

  def test_fail_closed
    changes = {
      'target' => -> { File.write(@work + '/inputs.txt', File.read(@work + '/inputs.txt').sub("target=#{@target}", "target=#{@target == 'amd64' ? 'aarch64' : 'amd64'}")) },
      'conflicting-target' => -> { File.write(@work + '/inputs.txt', File.read(@work + '/inputs.txt') + "target=#{@target}\n") },
      'source' => -> { File.write(@work + '/inputs.txt', File.read(@work + '/inputs.txt').sub(@archive_sha, 'c' * 64)) },
      'recipe' => -> { File.write(@pkgsrc + '/lang/gcc16/distinfo', 'modified') },
      'mutation' => -> { File.write(@stage + '/usr/pkg/gcc16/lib/libgcc_s.so.1', 'modified') },
      'unrecorded' => -> { File.write(@stage + '/unexpected', 'unrecorded') },
      'truncated-elf' => -> { File.write(@stage + '/usr/pkg/gcc16/lib/libgcc_s.so.1', "\x7fELF"); write_receipts },
      'rpath' => -> { p = @stage + '/usr/pkg/gcc16/lib/libgcc_s.so.1'; File.binwrite(p, File.binread(p).sub('/usr/pkg/gcc16/lib', '/tmp/bad'.ljust('/usr/pkg/gcc16/lib'.bytesize, 'x'))); write_receipts },
      'arch' => -> { File.write(@stage + '/usr/pkg/gcc16/lib/libgcc_s.so.1', elf('libgcc_s.so.1', @elf_machine == 62 ? 183 : 62)); write_receipts },
      'soname' => -> { File.write(@stage + '/usr/pkg/gcc16/lib/libstdc++.so.7.36', elf('libstdc++.so.9', @elf_machine)); write_receipts },
      'dependency' => -> { File.write(@stage + '/usr/pkg/gcc16/lib/libgcc_s.so.1', elf('libgcc_s.so.1', @elf_machine, ['libstdc++.so.9'])); write_receipts },
      'escape' => -> { File.unlink(@stage + '/usr/pkg/gcc16/lib/libstdc++.so.7'); File.symlink('/usr/lib/libstdc++.so.9', @stage + '/usr/pkg/gcc16/lib/libstdc++.so.7'); write_receipts },
      'indirect-unshipped-link' => -> { File.unlink(@stage + '/usr/pkg/gcc16/lib/libstdc++.so.7'); File.symlink('alias', @stage + '/usr/pkg/gcc16/lib/libstdc++.so.7'); File.symlink('libstdc++.so.7.36', @stage + '/usr/pkg/gcc16/lib/alias'); write_receipts },
      'unrecorded-link' => -> { File.write(@work + '/stage.symlinks', '') }
    }
    %w[amd64 aarch64].each do |target|
      changes.each do |name, change|
        with_fixture(target) { change.call; assert_raises(GCC16Runtime::Invalid, "#{target}/#{name}") { stage.verify } }
      end
    end
  end
  def test_real_native_package
    pkg_create = ENV['PKG_CREATE']
    skip 'Set PKG_CREATE to a native host tool' unless pkg_create
    %w[amd64 aarch64].each do |target|
      check_real_native_package(target, pkg_create)
      check_real_native_package(target, pkg_create, GCC16Runtime::SELECTIONS.last)
    end
  end

  def check_real_native_package(target, pkg_create, libraries = nil)
    with_fixture(target) do |d|
      add_optional_libraries(libraries) if libraries
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
      ["OPSYS=NetBSD", "OS_VERSION=11.0", "MACHINE_ARCH=#{@machine_arch}",
       "GCC_RUNTIME_TARGET=#{@target}", "GCC_RUNTIME_TRIPLET=#{@triplet}",
       "GCC_RUNTIME_MACHINE_ARCH=#{@machine_arch}",
       "GCC_RUNTIME_LIBRARIES=#{libraries || GCC16Runtime::SELECTIONS.first}"].each do |line|
        key = line.split('=', 2).first
        assert_equal [line], metadata.lines.map(&:chomp).grep(/^#{key}=/)
      end
      version, err, status = Open3.capture3(pkg_create, '-V')
      assert status.success?, err
      assert_equal ["PKGTOOLS_VERSION=#{version.chomp}"], metadata.lines.map(&:chomp).grep(/^PKGTOOLS_VERSION=/)
      assert_equal ["EMBERBSD_PKG_CREATE_SHA256=#{Digest::SHA256.file(pkg_create).hexdigest}"], metadata.lines.map(&:chomp).grep(/^EMBERBSD_PKG_CREATE_SHA256=/)
      if ENV['PKG_ADD']
        dest = d + '/installed'
        log, status = Open3.capture2e(ENV.fetch('PKG_ADD'), '-I', '-K', '/usr/pkg/pkgdb', '-P', dest, '-m', "NetBSD/#{@machine_arch} 11.0", package)
        assert status.success?, log
        refute_match(/warning|invalid pkg_install version|lacks pkg_install version data/, log)
        assert File.file?(dest + '/usr/pkg/pkgdb/' + GCC16Runtime::NAME + '/+BUILD_INFO')
        assert_equal File.binread(@stage + '/usr/pkg/gcc16/lib/libgcc_s.so.1'), File.binread(dest + '/usr/pkg/gcc16/lib/libgcc_s.so.1')
        stage.verify.fetch(:files).each do |path|
          source = @stage + '/usr/pkg/' + path
          installed = dest + '/usr/pkg/' + path
          if File.symlink?(source)
            assert File.symlink?(installed)
            assert_equal File.readlink(source), File.readlink(installed)
          else
            assert_equal File.binread(source), File.binread(installed)
          end
        end
        # Reproduce the pre-fix package with the real creator and installer.
        legacy = d + '/legacy'; FileUtils.mkdir(legacy)
        _, err, status = Open3.capture3('tar', '-xf', package, '-C', legacy)
        assert status.success?, err
        File.write(legacy + '/BUILD_INFO', metadata.lines.reject { |l| l.start_with?('PKGTOOLS_VERSION=', 'EMBERBSD_PKG_CREATE_SHA256=') }.join)
        File.write(legacy + '/PLIST', GCC16Runtime.plist(stage.verify))
        old_package = d + '/old.tgz'
        _, err, status = Open3.capture3(pkg_create, '-u', 'root', '-g', 'wheel', '-p', legacy, '-I', '/usr/pkg', '-B', legacy + '/BUILD_INFO', '-c', legacy + '/+COMMENT', '-d', legacy + '/+DESC', '-f', legacy + '/PLIST', old_package)
        assert status.success?, err
        log, status = Open3.capture2e(ENV.fetch('PKG_ADD'), '-I', '-K', '/usr/pkg/pkgdb', '-P', d + '/legacy-installed', '-m', "NetBSD/#{@machine_arch} 11.0", old_package)
        assert status.success?, log
        assert_match(/warning: lacks pkg_install version data/, log)
      end
      assert File.file?(output + '/package.sha256')
      assert File.file?(output + '/provenance.json')
      assert_raises(GCC16Runtime::Invalid) { GCC16Runtime.create(stage, pkg_create, output) }
    end
  end

  def test_native_pkgtools_version_rejects_invalid_queries_before_stage_or_output
    Dir.mktmpdir('gcc-runtime-pkgtools-') do |d|
      tool = d + '/pkg_create'
      untouched_stage = Object.new
      def untouched_stage.install(*) = raise('stage unexpectedly accessed')
      ["", "20260227nb1\n", "20260227\n20260227\n", " 20260227\n", "20260227 \n", "20260230\n", "00000000\n", "garbage\n"].each_with_index do |version, i|
        File.write(tool, "#!/bin/sh\nprintf '%s' '#{version}'\n")
        File.chmod(0755, tool)
        output = d + '/rejected-' + i.to_s
        assert_raises(GCC16Runtime::Invalid) { GCC16Runtime.create(untouched_stage, tool, output) }
        refute File.exist?(output)
      end
      File.write(tool, "#!/bin/sh\nprintf '20260227\\n'\nexit 1\n")
      assert_raises(GCC16Runtime::Invalid) { GCC16Runtime.create(untouched_stage, tool, d + '/failed-query') }
      refute File.exist?(d + '/failed-query')
      File.write(tool, "#!/bin/sh\nprintf '20260227\\n'\nprintf 'changed\\n' >> \"$0\"\n")
      assert_raises(GCC16Runtime::Invalid) { GCC16Runtime.create(untouched_stage, tool, d + '/changed-query') }
      refute File.exist?(d + '/changed-query')
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
      if ENV['GCC_ARCHIVE']
        %w[amd64 aarch64].each do |target|
          with_fixture(target) do
            # Real source-pin verification with synthetic stage DSOs, not a GCC build.
            @source = File.realpath(ENV.fetch('GCC_ARCHIVE'))
            @archive_sha = Digest::SHA256.file(@source).hexdigest
            assert_equal GCC16Runtime::SOURCE_SHA256, @archive_sha
            add_optional_libraries(GCC16Runtime::SELECTIONS.last) if target == 'aarch64'
            write_receipts
            [@machine_arch, @machine_arch == 'aarch64' ? 'x86_64' : 'aarch64'].each do |package_arch|
              out, err, status = Open3.capture3(bmake, '-C', d + '/lang/gcc16-runtime',
                'OPSYS=NetBSD', 'OS_VERSION=11.0', "MACHINE_ARCH=#{package_arch}",
                "GCC16_RUNTIME_RUBY=#{RbConfig.ruby}", "GCC16_RUNTIME_WORK=#{@work}",
                "GCC16_RUNTIME_ARCHIVE=#{@source}", "GCC16_RUNTIME_PKGSRC=#{@pkgsrc}",
                '-v', 'GCC_RUNTIME_TRIPLET', '-v', 'GCC_RUNTIME_LIBRARIES', '-v', 'PKG_FAIL_REASON')
              assert status.success?, out + err
              assert_equal @triplet, out.lines.first.chomp
              assert_equal @libraries || GCC16Runtime::SELECTIONS.first, out.lines[1].chomp
              refute_includes out, 'stage verification failed'
              message = 'Audited runtime architecture does not match the package target MACHINE_ARCH.'
              if package_arch == @machine_arch
                refute_includes out, message
              else
                assert_includes out, message
              end
            end
          end
        end
      end
    end
  end

end
