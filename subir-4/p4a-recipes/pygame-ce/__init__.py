"""
Recipe de python-for-android para compilar pygame-ce (pygame Community Edition)
para Android usando el bootstrap ``sdl2``.

Basada en la receta oficial ``pygame`` de python-for-android, con estos ajustes:

* se fija la version 2.5.8, la misma que usa el juego en escritorio;
* las rutas de cabeceras de SDL2_image / SDL2_ttf / SDL2_mixer se pasan de
  forma defensiva (raiz y subcarpeta ``include``), porque la ubicacion exacta
  de ``SDL_*.h`` cambia segun la version de cada libreria;
* se anade Cython a ``hostpython_prerequisites``: pygame-ce genera los ficheros
  ``.c`` a partir de los ``.pyx`` durante la compilacion (su ``setup.py`` aborta
  con "You need cython" si no lo encuentra) y la receta ``cython`` de p4a
  todavia fija la version 0.29.36, que no soporta Python 3.14. La version 3.3.1
  si lo soporta y ademas tiene wheel ``cp314`` ya compilado, asi que no hay que
  compilar nada para el hostpython.
"""

from os.path import join

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
    # imprescindible para pygame-ce (genera los .c desde los .pyx).
    hostpython_prerequisites = ['setuptools', 'Cython==3.3.1']

    def _includes(self, jni_name):
        """Cabeceras de una libreria SDL2 del bootstrap (raiz + ``include``)."""
        base = join(self.ctx.bootstrap.build_dir, 'jni', jni_name)
        return '-I{base} -I{inc} '.format(base=base, inc=join(base, 'include'))

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
                sdl_ttf_includes=self._includes('SDL2_ttf'),
                sdl_image_includes=self._includes('SDL2_image'),
                sdl_mixer_includes=self._includes('SDL2_mixer'),
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
        return env


recipe = PygameCERecipe()
