import os, subprocess, glob, re
from collections import defaultdict

from llnl.util import lang, filesystem, tty
from spack.util.environment import is_system_path, dump_environment
from spack.util.executable import which_string, which


def check_variant_fcgroup(fcgroup):
    pattern = re.compile(r"^[A-Z]+;.+;.")
    # fcgroup is False as default
    if pattern.match(fcgroup) or fcgroup == 'none':
        return True
    else:
        tty.warn('Variant fcgroup needs format GROUP;files;flag')
        return False


class Icon(AutotoolsPackage):
    """Icosahedral Nonhydrostatic Weather and Climate Model."""

    homepage = 'https://code.mpimet.mpg.de/projects/iconpublic'
    url = 'https://gitlab.dkrz.de/icon/icon/-/archive/icon-2.6.5.1/icon-icon-2.6.5.1.tar.gz'
    git = 'ssh://git@gitlab.dkrz.de/icon/icon.git'

    version('develop', submodules=True)
    version('2.6.5.1', tag='icon-2.6.5.1', submodules=True)
    version('exclaim-master',
            branch='master',
            git='ssh://git@github.com/C2SM/icon-exclaim.git',
            submodules=True)
    version('exclaim-test',
            branch='test_spec',
            git='ssh://git@github.com/C2SM/icon-exclaim.git',
            submodules=True)
    version('nwp-master',
            git='ssh://git@gitlab.dkrz.de/icon/icon-nwp.git',
            submodules=True)

    # The variants' default follow those of ICON
    # as described here
    # https://gitlab.dkrz.de/icon/icon/-/blob/icon-2.6.5.1/configure#L1454-1557

    # Model Features:
    variant('atmo',
            default=True,
            description='Enable the atmosphere component')
    variant('edmf',
            default=True,
            description='Enable the EDMF turbulence component')  #
    variant('les',
            default=True,
            description='Enable the Large-Eddy Simulation component')  #
    variant('upatmo',
            default=True,
            description='Enable the upper atmosphere component')  #
    variant('ocean', default=True, description='Enable the ocean component')
    variant('jsbach', default=True, description='Enable the land component')
    variant('waves',
            default=False,
            description='Enable the surface wave component')  #
    variant('coupling', default=True, description='Enable the coupling')
    variant('aes', default=True, description='Enable the AES physics package')
    variant('ecrad',
            default=False,
            description='Enable usage of the ECMWF radiation scheme')
    variant('rte-rrtmgp',
            default=False,
            description='Enable usage of the RTE+RRTMGP toolbox '
            'for radiation calculations')
    variant(
        'rttov',
        default=False,
        description='Enable usage of the radiative transfer model for TOVS')
    variant('dace',
            default=False,
            description='Enable the DACE modules for data assimilation')
    variant('emvorado',
            default=False,
            description='Enable the radar forward operator EMVORADO')
    variant('art',
            default=False,
            description='Enable the aerosols and reactive trace component ART')

    # Infrastructural Features:
    variant('mpi',
            default=True,
            description='Enable MPI (parallelization) support')
    variant(
        'active-target-sync',
        default=False,
        description=
        'Enable MPI active target mode (otherwise, passive target mode is used)'
    )
    variant('openmp', default=False, description='Enable OpenMP support')

    # https://en.wikipedia.org/wiki/CUDA#GPUs_supported
    gpu_values = ('10', '11', '12', '13', '20', '21', '30', '32', '35', '37',
                  '50', '52', '53', '60', '61', '62', '70', '72', '75', '80',
                  '86')
    variant('gpu',
            default='none',
            values=('none', ) + gpu_values,
            description='Enable GPU support with the specified compute '
            'capability version')

    variant('cuda-gcc',
            default=False,
            description='Use GCC as the CUDA host compiler')

    variant('grib2', default=True, description='Enable GRIB2 I/O')
    variant('parallel-netcdf',
            default=False,
            description='Enable usage of the parallel features of NetCDF')
    variant('cdi-pio',
            default=False,
            description='Enable usage of the parallel features of CDI')
    variant('sct', default=False, description='Enable the SCT timer')
    variant('yaxt', default=False, description='Enable the YAXT data exchange')

    claw_values = ('std', 'validate')
    variant('claw',
            default='none',
            values=('none', ) + claw_values,
            description='Enable CLAW preprocessing')

    serialization_values = ('read', 'perturb', 'create')
    variant('serialization',
            default='none',
            values=('none', ) + serialization_values,
            description='Enable the Serialbox2 serialization')

    # Optimization Features:
    variant('loop-exchange', default=True, description='Enable loop exchange')
    variant('vectorized-lrtm',
            default=False,
            description='Enable the parallelization-invariant version of LRTM')
    variant('mixed-precision',
            default=False,
            description='Enable mixed precision dycore')
    variant(
        'pgi-inlib',
        default=False,
        description=
        'Enable PGI/NVIDIA cross-file function inlining via an inline library')
    variant('nccl',
            default=False,
            description='Ennable NCCL for communication')

    variant(
        'fcgroup',
        default='none',
        multi=True,
        values=check_variant_fcgroup,
        description=
        'Create a Fortran compile group: GROUP;files;flag \nNote: flag can only be one single value, i.e. -O1'
    )

    # C2SM specific Features:
    variant(
        'infero',
        description=
        'Build with Infero to replace ecRad with ML implementation. Experimental, needs non-standard codebase!',
        default=False)

    variant(
        'eccodes-definitions',
        default=False,
        description=
        'Enable extension of eccodes with center specific definition files')

    depends_on('infero +quiet', when='+infero')

    depends_on('libxml2', when='+coupling')
    depends_on('libxml2', when='+art')

    depends_on('rttov+hdf5', when='+rttov')
    depends_on('rttov~openmp', when='~openmp+rttov')

    for x in serialization_values:
        depends_on('serialbox+fortran~shared',
                   when='serialization={0}'.format(x))

    depends_on('libcdi-pio+fortran+netcdf', when='+cdi-pio')
    depends_on('libcdi-pio grib2=eccodes', when='+cdi-pio+grib2')
    depends_on('libcdi-pio+mpi', when='+cdi-pio+mpi')

    depends_on('eccodes +fortran', when='+emvorado')
    depends_on('eccodes', when='+grib2 ~cdi-pio')
    depends_on('cosmo-eccodes-definitions',
               type=('build', 'run'),
               when='+eccodes-definitions')

    depends_on('yaxt+fortran', when='+cdi-pio')
    depends_on('lapack')
    depends_on('blas')
    depends_on('netcdf-fortran')

    depends_on('netcdf-c', when='~cdi-pio')
    depends_on('netcdf-c', when='+coupling')
    depends_on('netcdf-c+mpi', when='+parallel-netcdf~cdi-pio')

    depends_on('hdf5 +szip +hl +fortran', when='+emvorado')
    depends_on('hdf5 +szip', when='+sct')

    depends_on('zlib', when='+emvorado')
    depends_on('mpi', when='+mpi')

    for x in gpu_values:
        depends_on('cuda', when='gpu={0}'.format(x))

    depends_on('python', type='build')
    depends_on('perl', type='build')

    for x in claw_values:
        depends_on('claw', type='build', when='claw={0}'.format(x))

    conflicts('claw=validate', when='serialization=none')
    conflicts('+cuda-gcc', when='gpu=none')

    for x in claw_values:
        conflicts('+sct', when='claw={0}'.format(x))

    conflicts('+dace', when='~mpi')
    conflicts('+emvorado', when='~mpi')

    # Flag to mark if we build out-of-source
    # Needed to trigger sync of input files for experiments
    out_of_source_build = False

    # patch_libtool is a function from Autotoolspackage.
    # For BB we cannot use it because it finds all files
    # named "libtool". spack-c2sm is cloned into icon-repo,
    # therefore this function detects not only "libtool" files, but
    # also the folder where libtool package itself is installed.
    patch_libtool = False

    # We need an existing gcc compiler when '+cuda-gcc'. Taking one from the
    # PATH is not an option because we cannot always make sure that it will be
    # a particular installation of gcc. For example, we might want to build icon
    # with pgi compiler and use a system installation of gcc from '/usr/bin' as
    # the CUDA host compiler. Prepending '/usr/bin' to the PATH when pgi is used
    # breaks the building environment. We also cannot tell Spack to unload
    # particular environment modules that the user might have loaded before
    # running Spack and that put other installations of gcc on the PATH.
    # Therefore, our best option is to use gcc from compilers.yaml. The least
    # confusing way to get the required gcc when a different compiler is used to
    # build icon is to introduce a restriction: '^cuda%gcc' when '+cuda-gcc'.
    # This way, the users have control over what version of gcc will be used as
    # the CUDA host compiler and we can be sure that it will be a configured and
    # existing installation of gcc. There are two ways to introduce the
    # restriction:
    #   1) depends_on('cuda%gcc', when='+cuda-gcc') - this is the easiest way
    #      but it affects the compiler preferences in packages.yaml:
    #      'icon +cuda-gcc' always leads to 'icon%gcc';
    #   2) conflicts('+cuda-gcc', '^cuda%x') where x are all supported compilers
    #      except for gcc - this way does not affect the concretization
    #      preferences and does not even require the user to specify '^cuda%gcc'
    #      when cuda is configured as a non-buildable external for compatible
    #      compilers only.
    # Currently, we prefer the second option:
    for x in spack.compilers.supported_compilers():
        if x != 'gcc':
            conflicts('+cuda-gcc',
                      '^cuda%{0}'.format(x),
                      msg='"+cuda-gcc" requires "^cuda%gcc"')

    @when('%cce~openmp')
    def patch(self):
        # Cray Fortran preprocessor removes the OpenMP conditional compilation
        # sentinels (i.e. '!$') regardless of whether OpenMP is enabled.
        # Therefore, in cases when OpenMP support is disabled and separate
        # Fortran preprocessing is required, we substitute the sentinels with
        # '#ifdef _OPENMP' directives:
        if any(self.spec.variants[x].value != 'none'
               for x in ['serialization', 'claw']):
            src_files = find(join_path(self.stage.source_path, 'src'), '*.f90')
            filter_file(r'^(\s*)!\$(\s+.*)',
                        '#ifdef _OPENMP\n\\1  \\2\n#endif',
                        *src_files,
                        backup=False)

    def setup_build_environment(self, env):
        if '+cuda-gcc' in self.spec:
            # Make sure that the compiler in use adds an RPATH entry for the
            # directory containing the C++ standard library of the CUDA host
            # compiler:
            link_dirs = self._get_cuda_ccbin_link_paths(
                self.spec['cuda'].package.compiler, 'libstdc++')

            for d in link_dirs:
                env.append_path('SPACK_COMPILER_IMPLICIT_RPATHS', d)

    @run_before('configure')
    def downgrade_opt_level(self):
        # We try to prevent compiler crashes by reducing the optimization level
        # for certain files in certain configurations. This method extends the
        # makefile (i.e. icon.mk.in) with file-specific compilation rules that
        # call the compiler with the default flags plus the provided extra
        # flags. The extra flags must not affect the dependencies (e.g. define
        # additional macros).
        file_flags = []

        if self.compiler.name == 'intel':
            if self.spec.satisfies('%intel@17:17.0.2+ocean+openmp'):
                file_flags.append(
                    ('src/hamocc/common/mo_sedmnt_diffusion.f90',
                     '$(ICON_OCEAN_FCFLAGS) $(make_FCFLAGS) -O1'))
        elif self.compiler.name in ['pgi', 'nvhpc']:
            if '+emvorado' in self.spec:
                file_flags.append(
                    ('src/data_assimilation/interfaces/radar_interface.f90',
                     '$(ICON_FCFLAGS) $(make_FCFLAGS) -O1'))
        elif self.compiler.name == 'cce':
            if self.compiler.version == ver('12.0.2'):
                file_flags.append(
                    ('src/parallel_infrastructure/mo_setup_subdivision.f90',
                     '$(ICON_FCFLAGS) $(make_FCFLAGS) -O0'))
            elif self.compiler.version == ver('13.0.0'):
                file_flags.append(
                    ('src/parallel_infrastructure/mo_extents.f90',
                     '$(ICON_FCFLAGS) $(make_FCFLAGS) -O0'))
            if '+jsbach' in self.spec:
                file_flags.append(
                    ('externals/jsbach/src/base/mo_jsb_process_factory.f90',
                     '$(ICON_FCFLAGS) $(make_FCFLAGS) -O0'))

        if not file_flags:
            return

        recipe_prefix = '$(silent_FC)$(FC) -o $@ -c $(FCFLAGS)'
        recipe_suffix = '@FCFLAGS_f90@ $<'

        rules = []
        for file, flags in file_flags:
            recipe = '{0} {1} {2}'.format(recipe_prefix, flags, recipe_suffix)
            target = '{0}.@OBJEXT@'.format(os.path.splitext(file)[0])
            rules.extend([
                # Rule for the original file:
                '{0}: {1}; {2}'.format(target, file, recipe),
                # Rule for the preprocessed file:
                '%{0}: %{1}; {2}'.format(target, file, recipe)
            ])

        with open(join_path(self.stage.source_path, 'icon.mk.in'), 'a') as f:
            f.writelines(['\n', '\n'.join(rules)])

    def configure_args(self):
        config_args = ['--disable-rpaths', '--disable-silent-rules']
        config_vars = defaultdict(list)
        libs = LibraryList([])

        for x in [
                'atmo',
                'edmf',
                'les',
                'upatmo',
                'ocean',
                'jsbach',
                'waves',
                'coupling',
                'aes',
                'ecrad',
                'rte-rrtmgp',
                'rttov',
                'dace',
                'emvorado',
                'art',
                'mpi',
                'active-target-sync',
                'openmp',
                'grib2',
                'parallel-netcdf',
                'sct',
                'yaxt',
                'loop-exchange',
                'vectorized-lrtm',
                'mixed-precision',
                'pgi-inlib',
                'nccl',
        ]:
            config_args += self.enable_or_disable(x)

        if '+cdi-pio' in self.spec:
            config_args.extend([
                '--enable-cdi-pio', '--with-external-cdi',
                '--with-external-yaxt'
            ])

        gpu = self.spec.variants['gpu'].value

        if self.compiler.name == 'gcc' or self._compiler_is_mixed_gfortran():
            config_vars['CFLAGS'].append('-g')
            config_vars['ICON_CFLAGS'].append('-O3')
            config_vars['ICON_BUNDLED_CFLAGS'].append('-O2')
            config_vars['FCFLAGS'].extend([
                '-g',
                '-fmodule-private',
                '-fimplicit-none',
                '-fmax-identifier-length=63',
                '-Wall',
                '-Wcharacter-truncation',
                '-Wconversion',
                '-Wunderflow',
                '-Wunused-parameter',
                '-Wno-surprising',
                '-fall-intrinsics',
            ])
            config_vars['ICON_FCFLAGS'].extend([
                '-O2', '-fbacktrace', '-fbounds-check',
                '-fstack-protector-all', '-finit-real=nan',
                '-finit-integer=-2147483648', '-finit-character=127'
            ])
            config_vars['ICON_OCEAN_FCFLAGS'].append('-O3')

            # Version-specific workarounds:
            fc_version = (ver(self.compiler.fc_version(self.compiler.fc))
                          if self._compiler_is_mixed_gfortran() else
                          self.compiler.version)
            if fc_version >= ver(10):
                config_vars['ICON_FCFLAGS'].append('-fallow-argument-mismatch')
                config_vars['ICON_OCEAN_FCFLAGS'].append(
                    '-fallow-argument-mismatch')
                if '+ecrad' in self.spec:
                    # For externals/ecrad/ifsaux/random_numbers_mix.F90:
                    config_vars['ICON_ECRAD_FCFLAGS'].append(
                        '-fallow-invalid-boz')
        elif self.compiler.name == 'intel':
            config_vars['CFLAGS'].extend(
                ['-g', '-gdwarf-4', '-O3', '-qno-opt-dynamic-align', '-ftz'])
            config_vars['FCFLAGS'].extend(
                ['-g', '-gdwarf-4', '-traceback', '-fp-model source'])
            config_vars['ICON_FCFLAGS'].extend(
                ['-O2', '-assume realloc_lhs', '-ftz'])
            config_vars['ICON_OCEAN_FCFLAGS'].extend([
                '-O3', '-assume norealloc_lhs', '-reentrancy threaded',
                '-qopt-report-file=stdout', '-qopt-report=0',
                '-qopt-report-phase=vec'
            ])
            config_args.append('--enable-intel-consistency')
        elif self.compiler.name == 'nag':
            config_vars['CFLAGS'].append('-g')
            config_vars['ICON_CFLAGS'].append('-O3')
            config_vars['ICON_BUNDLED_CFLAGS'].append('-O2')
            config_vars['FCFLAGS'].extend([
                '-g', '-Wc,-g', '-O0', '-colour', '-f2008', '-w=uep',
                '-float-store', '-nan'
            ])
            if '~openmp' in self.spec:
                # The -openmp option is incompatible with the -gline option:
                config_vars['FCFLAGS'].append('-gline')
            config_vars['ICON_FCFLAGS'].extend([
                '-Wc,-pipe',
                '-Wc,--param,max-vartrack-size=200000000',
                '-Wc,-mno-fma',
                # Spack compiler wrapper (see the respective compilers.yaml)
                # injects '-mismatch', which is incompatible with '-C=calls'
                # Therefore, we specify the following flags instead of a single
                # '-C=all', which implies '-C=calls'.
                '-C=alias',
                '-C=array',
                '-C=bits',
                '-C=dangling',
                '-C=do',
                '-C=intovf',
                '-C=present',
                '-C=pointer',
                '-C=recursion'
            ])
            config_vars['ICON_BUNDLED_FCFLAGS'] = []
        elif self.compiler.name in ['pgi', 'nvhpc']:
            config_vars['CFLAGS'].extend(['-g', '-O2'])
            config_vars['FCFLAGS'].extend(
                ['-g', '-O', '-Mrecursive', '-Mallocatable=03', '-Mbackslash'])
            if gpu != 'none':
                config_vars['FCFLAGS'].extend([
                    '-acc=verystrict', '-Minfo=accel,inline',
                    '-gpu=cc{0}'.format(gpu)
                ])
                config_vars['ICON_FCFLAGS'].append('-D__SWAPDIM')
        elif self.compiler.name == 'cce':
            config_vars['CFLAGS'].append('-g')
            config_vars['ICON_CFLAGS'].append('-O3')
            if self.spec.satisfies('%cce@13.0.0+coupling'):
                # For externals/yac/tests/test_interpolation_method_conserv.c:
                config_vars['ICON_YAC_CFLAGS'].append('-O2')
            config_vars['FCFLAGS'].extend([
                '-hadd_paren', '-r am', '-Ktrap=divz,ovf,inv',
                '-hflex_mp=intolerant', '-hfp0', '-O0'
            ])
            if gpu != 'none':
                config_vars['FCFLAGS'].extend(['-hnoacc'])
        elif self.compiler.name == 'aocc':
            config_vars['CFLAGS'].extend(['-g', '-O2'])
            config_vars['FCFLAGS'].extend(['-g', '-O2'])
            if self.spec.satisfies('~cdi-pio+yaxt'):
                # Enable the PGI/Cray (NO_2D_PARAM) workaround for the test
                # suite of the bundled YAXT (apply also when not self.run_tests
                # to make sure we get identical installations):
                config_vars['ICON_YAXT_FCFLAGS'].append('-DNO_2D_PARAM')
        else:
            config_vars['CFLAGS'].extend(['-g', '-O2'])
            config_vars['FCFLAGS'].extend(['-g', '-O2'])

        if '+coupling' in self.spec or '+art' in self.spec:
            xml2_spec = self.spec['libxml2']
            libs += xml2_spec.libs
            # Account for the case when libxml2 is an external package installed
            # to a system directory, which means that Spack will not inject the
            # required -I flag with the compiler wrapper:
            if is_system_path(xml2_spec.prefix):
                xml2_headers = xml2_spec.headers
                # We, however, should filter the pure system directories out:
                xml2_headers.directories = [
                    d for d in xml2_headers.directories
                    if not is_system_path(d)
                ]
                config_vars['CPPFLAGS'].append(xml2_headers.include_flags)

        serialization = self.spec.variants['serialization'].value
        if serialization == 'none':
            config_args.append('--disable-serialization')
        else:
            config_args.extend([
                '--enable-serialization={0}'.format(serialization),
                '--enable-explicit-fpp',
                'SB2PP={0}'.format(self.spec['serialbox'].pp_ser)
            ])
            libs += self.spec['serialbox:fortran'].libs
            # static libs from serialbox need libstdc++ to link
            config_vars['LIBS'].extend(['-lstdc++ -lstdc++fs'])

        if '+cdi-pio' in self.spec:
            libs += self.spec['libcdi-pio:fortran'].libs

        if '+emvorado' in self.spec:
            libs += self.spec['eccodes:fortran'].libs

        if '+grib2~cdi-pio' in self.spec:
            libs += self.spec['eccodes:c'].libs

        if '+cdi-pio' in self.spec:
            libs += self.spec['yaxt:fortran'].libs

        if '+rttov' in self.spec:
            libs += self.spec['rttov'].libs

        libs += self.spec['lapack:fortran'].libs
        libs += self.spec['blas:fortran'].libs
        libs += self.spec['netcdf-fortran'].libs

        if '+coupling' in self.spec or '~cdi-pio' in self.spec:
            libs += self.spec['netcdf-c'].libs

        if '+emvorado' in self.spec or '+rttov' in self.spec:
            libs += self.spec['hdf5:fortran,hl'].libs
        elif '+sct' in self.spec:
            libs += self.spec['hdf5'].libs

        if '+emvorado' in self.spec:
            libs += self.spec['zlib'].libs

        if '+mpi' in self.spec:
            config_args.extend([
                'CC=' + self.spec['mpi'].mpicc,
                'FC=' + self.spec['mpi'].mpifc,
                # We cannot provide a universal value for MPI_LAUNCH, therefore
                # we have to disable the MPI checks:
                '--disable-mpi-checks'
            ])

        if '+infero' in self.spec:
            libs += self.spec['infero'].libs

        fcgroup = self.spec.variants['fcgroup'].value
        # ('none',) is the values spack assign if fcgroup is not set
        if fcgroup != ('none', ):
            config_args.extend(self.fcgroup_to_config_arg())
            config_vars.update(self.fcgroup_to_config_var())

        claw = self.spec.variants['claw'].value
        if claw == 'none':
            config_args.append('--disable-claw')
        else:
            config_args.extend([
                '--enable-claw={0}'.format(claw),
                'CLAW={0}'.format(self.spec['claw'].prefix.bin.clawfc)
            ])
            config_vars['CLAWFLAGS'].append(
                self.spec['netcdf-fortran'].headers.include_flags)
            if '+cdi-pio' in self.spec:
                config_vars['CLAWFLAGS'].append(
                    self.spec['libcdi-pio'].headers.include_flags)

        if gpu == 'none':
            config_args.append('--disable-gpu')
        else:
            config_args.extend([
                '--enable-gpu', '--disable-loop-exchange',
                'NVCC={0}'.format(self.spec['cuda'].prefix.bin.nvcc)
            ])

            libs += self.spec['cuda'].libs

            if '+cuda-gcc' in self.spec:
                # We know that the compiler of cuda is gcc:
                gcc = self.spec['cuda'].package.compiler
                cuda_host_compiler = self._get_cuda_ccbin_wrapper(gcc)
                cuda_host_compiler_stdcxx_libs = [
                    '-L{0}'.format(d)
                    for d in self._get_cuda_ccbin_link_paths(gcc, 'libstdc++')
                ]
                cuda_host_compiler_stdcxx_libs.append('-lstdc++')
            else:
                cuda_host_compiler = self.compiler.cxx
                cuda_host_compiler_stdcxx_libs = self.compiler.stdcxx_libs

            config_vars['NVCFLAGS'].extend([
                '-ccbin {0}'.format(cuda_host_compiler), '-g', '-O3',
                '-arch=sm_{0}'.format(gpu)
            ])
            # cuda_host_compiler_stdcxx_libs might contain compiler-specific
            # flags (i.e. not the linker -l<library> flags), therefore we put
            # the value to the config_flags directly.
            config_vars['LIBS'].extend(cuda_host_compiler_stdcxx_libs)

        # Finalize the LIBS variable (we always put the real collected
        # libraries to the front):
        config_vars['LIBS'].insert(0, libs.link_flags)

        # Help the libtool scripts of the bundled libraries find the correct
        # paths to the external libraries. Specify the library search (-L) flags
        # in the reversed order
        # (see https://gitlab.dkrz.de/icon/icon#icon-dependencies):
        # and for non-system directories only:
        config_vars['LDFLAGS'].extend([
            '-L{0}'.format(d) for d in reversed(libs.directories)
            if not is_system_path(d)
        ])

        config_args.extend([
            '{0}={1}'.format(var, ' '.join(val))
            for var, val in config_vars.items()
        ])

        return config_args

    def fcgroup_to_config_arg(self):
        arg = []
        for group in self.spec.variants['fcgroup'].value:
            name = group.split(';')[0]
            files = group.split(';')[1]
            arg.append(f'--enable-fcgroup-{name}={files}')
        return arg

    def fcgroup_to_config_var(self):
        var = {}
        for group in self.spec.variants['fcgroup'].value:
            name = group.split(';')[0]
            flag = group.split(';')[2]
            # Note: flag needs to be a list
            var[f'ICON_{name}_FCFLAGS'] = [flag]
        return var

    @run_after('configure')
    def adjust_rttov_macro(self):
        if '+rttov' in self.spec:
            rttov_major_version = self.spec['rttov'].version.up_to(1)
            if rttov_major_version != ver(13):
                filter_file('_RTTOV_VERSION=13',
                            '_RTTOV_VERSION={0}'.format(rttov_major_version),
                            'icon.mk',
                            string=True,
                            backup=False)

    def build(self, spec, prefix):
        claw = self.spec.variants['claw'].value
        if claw != 'none' and make_jobs > 8:
            # Limit CLAW preprocessing to 8 parallel jobs to avoid
            # claw_f_lib.sh: fork: retry: Resource temporarily unavailable
            # ...
            # Error: Could not create the Java Virtual Machine.
            # Error: A fatal exception has occurred. Program will exit.
            make.jobs = 8
            make('preprocess')
            make.jobs = make_jobs
        make(*self.build_targets)

    @run_before('install')
    @on_package_attributes(run_tests=True)
    def check(self):
        # script needs cdo to work, but not listed as dep of ICON
        test_script = 'scripts/spack/test.py'
        if os.path.exists(test_script):
            test_py = Executable(test_script)

            # test.py fails if PYTHONHOME has any value,
            # even '' or ' ' is failing, therefore delete
            # it temporary from env
            PYTHONHOME = os.environ['PYTHONHOME']
            os.environ.pop('PYTHONHOME')

            with open('spec.yaml', mode='w') as f:
                f.write(self.spec.to_yaml())
            try:
                test_py('--spec', 'spec.yaml')
            except:
                raise InstallError('Tests failed')

            # restore PYTHONHOME after test.py
            os.environ['PYTHONHOME'] = PYTHONHOME
        else:
            tty.warn('Cannot find test.py -> skipping tests')

    @property
    def archive_files(self):
        # Archive files that are normally archived for AutotoolsPackage:
        archive = list(super(Icon, self).archive_files)
        # Archive makefiles:
        archive.extend(
            [join_path(self.build_directory, f) for f in ['Makefile', '*.mk']])
        # Archive CUDA GCC wrapper:
        archive.append(join_path(self._cuda_ccbin_wrapper_dir, '*'))
        return archive

    @property
    def _cuda_ccbin_wrapper_dir(self):
        # Path to the CUDA host compiler wrapper directory:
        return join_path(self.stage.path, 'spack-cuda-ccbin')

    @lang.memoized
    def _get_cuda_ccbin_wrapper(self, compiler):
        # The version of CUDA in use might be incompatible with the C++ compiler
        # of the compiler toolchain that needs to be used to build ICON. For
        # example, we might be limited to CUDA 10.0.130 (due to the
        # compatibility with the GPU drivers on the compute nodes), which is
        # incompatible with pgc++ from the PGI 19.9 toolchain - the only
        # available compiler toolchain with the Fortran compiler that can handle
        # OpenACC directives in the source code of ICON. To cover such cases, we
        # introduced a fallback solution (see variant 'cuda-gcc'), which is to
        # make sure that self.spec['cuda'].package.compiler is an instance of
        # spack.compilers.Gcc and use its cxx as the CUDA host compiler. The
        # problem is that the user might have configured the compiler (in
        # compilers.yaml) to be run in a modified environment with additional
        # flags. We address that by creating a wrapper, which is in fact a very
        # simplified version of the Spack compiler wrapper (which we cannot use
        # because the current build environment is configured for the compiler
        # that ICON must be built with).
        #
        # This method is not limited to gcc and can create a wrapper for any
        # subclass of spack.compiler.

        # Create a directory for the wrapper:
        mkdirp(self._cuda_ccbin_wrapper_dir)

        # Dump the modified compiler environment to a source-able file:
        env_file = join_path(self._cuda_ccbin_wrapper_dir, 'ccbin-env.txt')
        with compiler._compiler_environment():
            dump_environment(env_file)

        # Create the wrapper:
        ccbin_wrapper = join_path(self._cuda_ccbin_wrapper_dir, 'ccbin')
        with open(ccbin_wrapper, 'w') as f:
            f.writelines([
                '#!{0}\n'.format(which_string('bash', required=True)),
                '. {0}\n'.format(env_file), 'exec {0} {1} "$@"\n'.format(
                    compiler.cxx,
                    ' '.join(flag for flag_type in ['cppflags', 'cxxflags']
                             for flag in compiler.flags.get(flag_type, [])))
            ])
        os.chmod(ccbin_wrapper, 0o755)

        return ccbin_wrapper

    @lang.memoized
    def _get_cuda_ccbin_link_paths(self, compiler, *required_libs):
        # The compiler in use might not know how to find the runtime libraries
        # of the CUDA host compiler (i.e. when '+cuda-gcc', see comments in the
        # _get_cuda_ccbin_wrapper method). For example, the Fortran compiler of
        # the PGI toolchain might not know where to find libstdc++ of g++ that
        # is used as the CUDA host compiler. This method requests the provided
        # instance of spack.compiler (does not have to be spack.compilers.Gcc)
        # for paths that its cxx implicitly passes to the linker and returns a
        # a list of (non-system) directories that contain at least one library
        # from the required_libs argument.

        link_dirs = compiler._get_compiler_link_paths([compiler.cxx])
        return list(filesystem.paths_containing_libs(link_dirs, required_libs))

    @lang.memoized
    def _compiler_is_mixed_gfortran(self):
        if self.compiler.name == 'gcc' or not self.compiler.fc:
            return False

        fc_name, _, _ = os.path.basename(self.compiler.fc).partition('-')

        if not fc_name:
            return False

        from spack.compilers.gcc import Gcc
        return fc_name in Gcc.fc_names

    @property
    def build_directory(self):
        """Overrides function from spack.build_system.autotools
        
        By default build_directory is identical as configure_directory
        To enable out-of-source builds this is not the case anymore
        """

        return self.stage.source_path

    @property
    def configure_directory(self):
        """Returns the directory where 'configure' resides.

        Overides function from spack.build_systems.autotools

        CAUTION: Does only work if Spack is inside the git-repo
                 of ICON, otherwise "git rev-pars --show-toplevel"
                 fails!

        """

        Git = which('git', required=True)
        git_root = Git('rev-parse', '--show-toplevel',
                       output=str).replace("\n", "")
        if git_root != self.stage.source_path:
            # mark out-of-source build for function
            # copy_runscript_related_input_files
            self.out_of_source_build = True
            return git_root
        else:
            return self.stage.source_path

    def configure(self, spec, prefix):
        if os.path.exists(
                os.path.join(self.build_directory,
                             'icon.mk')) and self.build_uses_same_spec():
            tty.warn(
                'icon.mk already present -> skip configure stage',
                '\t delete "icon.mk" or run "make distclean" to not skip configure'
            )
            return

        # use configure provided by Spack
        AutotoolsPackage.configure(self, spec, prefix)

    def build_uses_same_spec(self):
        """
        Ensure that configure is rerun in case spec has changed,
        otherwise for the case below

            $ spack dev-build icon @develop gpu=none ~dace
            $ spack dev-build icon @develop gpu=none +dace
        
        configure is skipped for the latter.
        """

        is_same_spec = False

        previous_spec = os.path.join(self.build_directory,
                                     '.previous_spec.yaml')

        # not the first build in self.build_directory
        if os.path.exists(previous_spec):
            with open(previous_spec, mode='r') as f:
                if self.spec == Spec.from_yaml(f):
                    is_same_spec = True
                else:
                    is_same_spec = False
                    tty.warn(
                        'Cannot skip configure phase because spec changed')

        # first build in self.build_directory, no worries
        else:
            is_same_spec = True

        # dump spec of new build
        with open(previous_spec, mode='w') as f:
            f.write(self.spec.to_yaml())

        return is_same_spec

    @run_after('configure')
    def copy_runscript_related_input_files(self):
        if self.out_of_source_build:
            with working_dir(self.build_directory):
                Rsync = which('rsync', required=True)
                icon_dir = self.configure_directory
                Rsync("-uavz", f"{icon_dir}/run", ".", "--exclude=*.in",
                      "--exclude=.*", "--exclude=standard_*")
                Rsync("-uavz", f"{icon_dir}/externals", ".", "--exclude=.git",
                      "--exclude=*.f90", "--exclude=*.F90", "--exclude=*.c",
                      "--exclude=*.h", "--exclude=*.Po", "--exclude=tests",
                      "--exclude=*.mod", "--exclude=*.o")
                Rsync("-uavz", f"{icon_dir}/make_runscripts", ".")

                Ln = which('ln', required=True)
                dirs = glob.glob(f"{icon_dir}/run/standard_*")
                for dir in dirs:
                    Ln("-sf", "-t", "run/", f"{dir}")
                Ln("-sf", f"{icon_dir}/data")
                Ln("-sf", f"{icon_dir}/vertical_coord_tables")
