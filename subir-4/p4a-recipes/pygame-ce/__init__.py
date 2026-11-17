"""
Recipe de python-for-android para compilar pygame-ce (pygame Community Edition)
para Android usando el bootstrap ``sdl2``.

Basada en la receta oficial ``pygame`` de python-for-android, con estos ajustes,
todos verificados contra el codigo real de pygame-ce 2.5.8:

* se fija la version 2.5.8, la misma que usa el juego en escritorio;
* las cabeceras de SDL2_ttf / SDL2_image / SDL2_mixer se recogen de forma
  defensiva: se prueban las del bootstrap y las que declara cada receta
  (``get_include_dirs``). Un ``-I`` de mas nunca molesta;
* se instala Cython en el hostpython con el gancho oficial
  ``hostpython_prerequisites``: pygame-ce genera los ``.c`` de ``_sdl2`` a
  partir de los ``.pyx`` durante la compilacion y su ``setup.py`` aborta con
  "You need cython" si no lo encuentra. Se usa la 3.2.9 porque es la ultima que
  admite el propio pygame-ce 2.5.8 (``cython<=3.2.9``) y porque tiene wheel
  ``cp314`` (Python 3.14, el que usa p4a), asi que se instala sin compilar.
  La receta ``cython`` de p4a no sirve: todavia fija la 0.29.36;
* se borra la variable ``CI`` del entorno: si esta definida (GitHub Actions
  siempre la define), el ``setup.py`` de pygame-ce anade ``-Werror`` a todos los
  modulos y cualquier aviso de clang (NDK) rompe la compilacion.
"""

from os.path import join

from pythonforandroid.logger import warning
from pythonforandroid.recipe import CompiledComponentsPythonRecipe
from pythonforandroid.toolchain import current_directory


class PygameCERecipe(CompiledComponentsPythonRecipe):
    """
    Recipe para compilar pygame-ce para Android.

    El modulo ``freetype`` de pygame viene comentado en la plantilla
    ``Setup.Android.SDL2.in`` del propio pygame-ce, por lo que no hace falta
    enlazar libfreetype/libharfbuzz (evita un fallo de enlazado).
    """

    version = '2.5.8'
    url = 'https://github.com/pygame-community/pygame-ce/archive/{version}.tar.gz'

    site_packages_name = 'pygame-ce'
    name = 'pygame-ce'

    depends = ['sdl2', 'sdl2_image', 'sdl2_mixer', 'sdl2_ttf', 'setuptools', 'jpeg', 'png']
    call_hostpython_via_targetpython = False  # debido a setuptools
    install_in_hostpython = False

    # Paquetes que p4a instala en el hostpython antes de compilar. Cython es
    # imprescindible para pygame-ce (genera los .c de _sdl2 desde los .pyx).
    hostpython_prerequisites = ['setuptools', 'Cython==3.2.9']

    # Variantes que se prueban si la anterior no estuviera disponible.
    cython_attempts = [
        ['setuptools', 'Cython==3.2.9'],
        ['setuptools', 'Cython>=3.2,<3.3'],
        ['setuptools', 'Cython'],
    ]

    def install_hostpython_prerequisites(self, packages=None, force_upgrade=True):
        """Instala Cython en el hostpython, probando varias versiones si falla."""
        if packages:
            return super().install_hostpython_prerequisites(
                packages=packages, force_upgrade=force_upgrade)
        last_error = None
        for attempt in self.cython_attempts:
            try:
                super().install_hostpython_prerequisites(
                    packages=attempt, force_upgrade=force_upgrade)
                return
            except Exception as error:
                last_error = error
                warning('No se pudo instalar {} en el hostpython: {}'.format(
                    attempt, error))
        raise Exception(
            'No se pudo instalar Cython en el hostpython: {}'.format(last_error))

    def _includes(self, arch, recipe_name, jni_name):
        """Cabeceras de una libreria SDL2 (bootstrap + las de su receta)."""
        dirs = []
        base = join(self.ctx.bootstrap.build_dir, 'jni', jni_name)
        dirs.append(base)
        dirs.append(join(base, 'include'))
        try:
            recipe = self.get_recipe(recipe_name, self.ctx)
            dirs.extend(recipe.get_include_dirs(arch))
        except Exception as error:
            warning('No se pudieron obtener las cabeceras de {}: {}'.format(
                recipe_name, error))
        unique = []
        for directory in dirs:
            if directory not in unique:
                unique.append(directory)
        return ' '.join('-I{}'.format(directory) for directory in unique) + ' '

    def prebuild_arch(self, arch):
        super().prebuild_arch(arch)
        with current_directory(self.get_build_dir(arch.arch)):
            setup_template = open(join('buildconfig', 'Setup.Android.SDL2.in')).read()
            env = self.get_recipe_env(arch)
            env['ANDROID_ROOT'] = join(self.ctx.ndk.sysroot, 'usr')

            png = self.get_recipe('png', self.ctx)
            png_lib_dir = join(png.get_build_dir(arch.arch), '.libs')
            png_inc_dir = png.get_build_dir(arch)

            jpeg = self.get_recipe('jpeg', self.ctx)
            jpeg_inc_dir = jpeg_lib_dir = jpeg.get_build_dir(arch.arch)

            setup_file = setup_template.format(
                sdl_includes=(
                    ' -I' + join(self.ctx.bootstrap.build_dir, 'jni', 'SDL', 'include') +
                    ' -L' + join(self.ctx.bootstrap.build_dir, 'libs', str(arch)) +
                    ' -L' + png_lib_dir + ' -L' + jpeg_lib_dir +
                    ' -L' + arch.ndk_lib_dir_versioned),
                sdl_ttf_includes=self._includes(arch, 'sdl2_ttf', 'SDL2_ttf'),
                sdl_image_includes=self._includes(arch, 'sdl2_image', 'SDL2_image'),
                sdl_mixer_includes=self._includes(arch, 'sdl2_mixer', 'SDL2_mixer'),
                jpeg_includes='-I' + jpeg_inc_dir,
                png_includes='-I' + png_inc_dir,
                freetype_includes='',
            )
            open('Setup', 'w').write(setup_file)

    def get_recipe_env(self, arch):
        env = super().get_recipe_env(arch)
        env['USE_SDL2'] = '1'
        env['PYGAME_CROSS_COMPILE'] = 'TRUE'
        env['PYGAME_ANDROID'] = 'TRUE'
        # Sin esto, en GitHub Actions pygame-ce compila con -Werror y cualquier
        # aviso del compilador del NDK aborta la compilacion.
        env.pop('CI', None)
        env.pop('GITHUB_ACTIONS', None)
        return env


recipe = PygameCERecipe()
