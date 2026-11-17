"""
Recipe de python-for-android para compilar pygame-ce (pygame Community Edition)
para Android usando el bootstrap ``sdl2``.

Basada en la receta oficial ``pygame`` de python-for-android, con los ajustes
necesarios para pygame-ce 2.5.8 (verificados contra su codigo fuente):

1. Version 2.5.8, la misma que usa el juego en escritorio.
2. Cabeceras de SDL2_ttf / SDL2_image / SDL2_mixer: se prueban las del bootstrap
   y las que declara cada receta (``get_include_dirs``). Un ``-I`` de mas no
   molesta nunca.
3. Cython en el hostpython (gancho oficial ``hostpython_prerequisites``):
   pygame-ce genera los ``.c`` de ``_sdl2`` desde los ``.pyx`` y su ``setup.py``
   aborta con "You need cython" si falta. Se usa la 3.2.9 porque es la ultima
   que admite el propio pygame-ce (``cython<=3.2.9``) y tiene wheel ``cp314``
   (Python 3.14), asi que se instala sin compilar. La receta ``cython`` de p4a
   no sirve: todavia fija la 0.29.36.
4. Se borra la variable ``CI`` del entorno: si esta definida (GitHub Actions
   siempre la define) el ``setup.py`` de pygame-ce anade ``-Werror`` y cualquier
   aviso de clang del NDK rompe la compilacion.
5. ``pyproject.toml``: p4a instala el paquete al final con ``pip install .``, y
   pip usa el backend que declare ese fichero. El que trae pygame-ce
   (``meson-python``) compila un binario para ARM e intenta ejecutarlo en el PC
   -> falla con "Could not invoke sanity check executable". El backend moderno
   de setuptools tambien falla, porque ejecuta ``setup.py`` sin poner la carpeta
   del proyecto en ``sys.path`` y su ``import buildconfig`` revienta. Se deja el
   backend **legacy** de setuptools (``setuptools.build_meta:__legacy__``), que
   es exactamente el que pip usa cuando el paquete no trae ``pyproject.toml``
   (o sea, el mismo camino que usa la receta oficial de pygame 2.1.0).
6. Como segundo cinturon, el propio ``setup.py`` se parchea para que anada la
   carpeta del proyecto a ``sys.path`` antes de ``import buildconfig``.
"""

import os
from os.path import join

from pythonforandroid.logger import warning
from pythonforandroid.recipe import CompiledComponentsPythonRecipe
from pythonforandroid.toolchain import current_directory

# Backend con el que se sustituye el de pygame-ce en pyproject.toml. Se declara
# Cython en ``requires`` para que pip lo tenga tambien en el entorno aislado que
# crea al instalar el paquete.
BACKEND_LEGACY = [
    'requires = ["setuptools", "wheel", "Cython==3.2.9"]',
    'build-backend = "setuptools.build_meta:__legacy__"',
]

# Marca que se inserta en setup.py para no parchearlo dos veces.
MARCA_SETUP_PY = '# --- p4a: carpeta del proyecto en sys.path ---'


class PygameCERecipe(CompiledComponentsPythonRecipe):
    """
    Recipe para compilar pygame-ce para Android.

    El modulo ``freetype`` de pygame viene comentado en la plantilla
    ``Setup.Android.SDL2.in`` del propio pygame-ce, por lo que no hace falta
    enlazar libfreetype/libharfbuzz (evita un fallo de enlazado).
    """

    version = '2.5.8'
    url = 'https://github.com/pygame-community/pygame-ce/archive/{version}.tar.gz'

    # El modulo instalado se llama ``pygame``, no ``pygame-ce``.
    site_packages_name = 'pygame'
    name = 'pygame-ce'

    depends = ['sdl2', 'sdl2_image', 'sdl2_mixer', 'sdl2_ttf', 'setuptools', 'jpeg', 'png']
    call_hostpython_via_targetpython = False  # debido a setuptools
    install_in_hostpython = False

    # Paquetes que p4a instala en el hostpython antes de compilar.
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

    def _parchear_pyproject(self):
        """Sustituye el backend de pygame-ce por el legacy de setuptools.

        El resto del fichero (la tabla ``[project]``, de la que ``setup.py``
        toma parte de los metadatos) se deja intacto.
        """
        if not os.path.exists('pyproject.toml'):
            return
        with open('pyproject.toml', encoding='utf-8') as fh:
            lineas = fh.read().splitlines()
        nuevas = []
        en_tabla = False
        cambiado = False
        for linea in lineas:
            if linea.strip() == '[build-system]':
                en_tabla = True
                cambiado = True
                nuevas.append('[build-system]')
                nuevas.extend(BACKEND_LEGACY)
                continue
            if en_tabla:
                if linea.startswith('['):
                    en_tabla = False
                else:
                    continue
            nuevas.append(linea)
        if not cambiado:
            nuevas.extend(['', '[build-system]'])
            nuevas.extend(BACKEND_LEGACY)
        with open('pyproject.toml', 'w', encoding='utf-8') as fh:
            fh.write('\n'.join(nuevas) + '\n')

    def _parchear_setup_py(self):
        """Hace que ``setup.py`` pueda importar ``buildconfig``.

        ``setup.py`` empieza con ``import buildconfig.get_version`` (linea 12).
        Con ``python setup.py`` funciona porque Python anade la carpeta del
        script a ``sys.path``, pero al instalar pip ejecuta ``setup.py`` dentro
        de su propio proceso y esa carpeta no esta en ``sys.path``, asi que
        falla con ``ModuleNotFoundError: No module named 'buildconfig'``. Aqui
        se anade la carpeta del proyecto a ``sys.path`` justo antes del import.
        """
        if not os.path.exists('setup.py'):
            return
        with open('setup.py', encoding='utf-8') as fh:
            contenido = fh.read()
        if MARCA_SETUP_PY in contenido:
            return
        lineas = contenido.splitlines()
        for indice, linea in enumerate(lineas):
            if linea.strip() == 'import buildconfig.get_version as pg_ver':
                lineas[indice:indice] = [
                    MARCA_SETUP_PY,
                    'import os as _p4a_os, sys as _p4a_sys',
                    '_p4a_raiz = _p4a_os.path.dirname(_p4a_os.path.abspath('
                    'globals().get("__file__") or "setup.py"))',
                    '_p4a_sys.path.insert(0, _p4a_raiz or _p4a_os.getcwd())',
                ]
                break
        else:
            warning('No se encontro el import de buildconfig en setup.py')
            return
        with open('setup.py', 'w', encoding='utf-8') as fh:
            fh.write('\n'.join(lineas) + '\n')

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
            self._parchear_pyproject()
            self._parchear_setup_py()

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
