import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT=Path(__file__).resolve().parents[1]
GENERATOR=ROOT/'scripts/generate-sdl-symbols.py'


class SdlExportTests(unittest.TestCase):
    def test_generator_intersects_public_declarations_with_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            headers=root/'include/SDL3'
            headers.mkdir(parents=True)
            (headers/'SDL_minimal.h').write_text('''
#define SDL_DECLSPEC
#define SDLCALL
extern SDL_DECLSPEC int SDLCALL SDL_Declared(void);
extern SDL_DECLSPEC int SDLCALL SDL_Unavailable(void);
extern SDL_DECLSPEC int SDLCALL SDL_OnlyReal_REAL(void);
''')
            (root/'fixture.c').write_text('''
int SDL_Declared(void) { return 1; }
int SDL_Internal(void) { return 2; }
int SDL_OnlyReal_REAL(void) { return 3; }
''')
            subprocess.run(['gcc','-c',str(root/'fixture.c'),'-o',str(root/'fixture.o')],check=True,capture_output=True)
            subprocess.run(['ar','rcs',str(root/'libSDL3.a'),str(root/'fixture.o')],check=True,capture_output=True)
            output=root/'sdl_symbols_generated.h'
            manifest=root/'manifest.json'
            subprocess.run([
                'python3',str(GENERATOR),'--headers',str(headers),'--archive',str(root/'libSDL3.a'),
                '--output',str(output),'--manifest',str(manifest)
            ],check=True,capture_output=True,text=True)
            generated=output.read_text()
            proof=json.loads(manifest.read_text())
            self.assertIn('X(SDL_Declared)',generated)
            self.assertNotIn('X(SDL_Unavailable)',generated)
            self.assertNotIn('X(SDL_Internal)',generated)
            self.assertNotIn('X(SDL_OnlyReal_REAL)',generated)
            self.assertEqual(proof['exports'],['SDL_Declared'])
            self.assertEqual(proof['matched_export_count'],1)

    def test_pinned_switch_archive_has_complete_public_sdl_surface(self):
        archive=ROOT/'.deps/sdl3/lib/libSDL3.a'
        headers=ROOT/'.deps/sdl3/include/SDL3'
        if not archive.exists() or not headers.exists():
            self.skipTest('pinned SDL3 archive is not built')
        devkitpro=Path(os.environ.get('DEVKITPRO',ROOT/'.toolchain/opt/devkitpro'))
        compiler=devkitpro/'devkitA64/bin/aarch64-none-elf-gcc'
        if not compiler.exists():
            self.skipTest('pinned AArch64 Switch compiler is not installed')
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'sdl_symbols_generated.h'
            manifest=Path(directory)/'manifest.json'
            subprocess.run([
                'python3',str(GENERATOR),'--headers',str(headers),'--archive',str(archive),
                '--output',str(output),'--manifest',str(manifest),'--cc',str(compiler),
                '--include',str(headers.parent),'--include',str(ROOT/'.deps/nvk/include')
            ],check=True,capture_output=True,text=True)
            proof=json.loads(manifest.read_text())
            exports=set(proof['exports'])
            self.assertGreater(proof['matched_export_count'],1000)
            self.assertTrue({'SDL_Init','SDL_Quit','SDL_GetError','SDL_GetVersion',
                             'SDL_Vulkan_GetInstanceExtensions','SDL_Vulkan_CreateSurface'} <= exports)
            self.assertTrue(all(not name.endswith('_REAL') for name in exports))
            self.assertTrue({'SDL_GetAndroidActivity','SDL_GDKResumeGPU','SDL_RegisterApp'}.isdisjoint(exports))
            self.assertEqual(proof['excluded_public_but_unavailable'],[])


if __name__=='__main__':
    unittest.main()
