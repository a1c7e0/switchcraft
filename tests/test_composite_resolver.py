import os
from pathlib import Path
import subprocess
import tempfile
import unittest
ROOT = Path(__file__).resolve().parents[1]
JAVA = Path(os.environ.get('JAVA_SWITCH_SOURCE', str(ROOT/'.deps/java-switch')))
class CompositeResolverTests(unittest.TestCase):
    def test_real_sdk_publication_and_composed_lookups(self):
        with tempfile.TemporaryDirectory() as d:
            exe = Path(d)/'resolver'
            subprocess.run(['gcc','-std=c11','-Wall','-Wextra','-Werror','-Iinclude',
                '-I'+str(JAVA/'include'), 'src/composite_resolver.c',
                str(JAVA/'src/native_resolver.c'), 'tests/composite_resolver_host.c',
                '-o',str(exe)],cwd=ROOT,check=True)
            subprocess.run([str(exe)],cwd=ROOT,check=True)
            for module in ['SDL3','vulkan','lwjgl','lwjgl_stb','lwjgl_vma','freetype','openal','shaderc','spirv-cross-c']:
                subprocess.run([str(exe)],cwd=ROOT,check=True,env={**os.environ,'SC_TEST_COLLISION':module})
