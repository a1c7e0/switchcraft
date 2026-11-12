"""Exercise LWJGL's genuine libffi upcall path through the cached SDL3 natives."""
import importlib.util
import os
import platform
import sys
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT=Path(__file__).resolve().parents[1]
JDKS=sorted((ROOT/'.deps/host-jdk25').glob('*/bin'))

_spec=importlib.util.spec_from_file_location('lwjgl_dependencies',ROOT/'scripts/build-lwjgl-horizon.py')
_dependencies=importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_dependencies)


class TestLWJGLCoreCallbacks(unittest.TestCase):
    def test_sdl_timer_thread_calls_java_through_real_lwjgl_upcalls(self):
        if sys.platform != 'linux' or platform.machine().lower() not in ('x86_64','amd64'):
            self.skipTest('pinned callback native artifacts target Linux x86_64')
        if not JDKS:
            self.skipTest('pinned host JDK 25 is not installed')
        jdk=JDKS[0]
        core=_dependencies.fetch('lwjgl_core')
        sdl=_dependencies.fetch('lwjgl_sdl')
        sdl_natives=_dependencies.fetch('lwjgl_sdl_host_linux')
        core_natives=_dependencies.fetch('lwjgl_core_host_linux')
        jspecify=_dependencies.fetch('jspecify')
        subprocess.run(['python3',str(ROOT/'scripts/build-lwjgl-core.py'),'--host'],cwd=ROOT,check=True)
        with tempfile.TemporaryDirectory(prefix='lwjgl-core-upcall-') as directory:
            tmp=Path(directory)
            source=tmp/'LWJGLCoreCallbackProbe.java'
            source.write_text('''import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;
import org.lwjgl.sdl.SDLLog;
import org.lwjgl.sdl.SDL_LogOutputFunction;
import org.lwjgl.sdl.SDL_TimerCallback;
import org.lwjgl.sdl.SDLTimer;
import org.lwjgl.system.MemoryUtil;

public final class LWJGLCoreCallbackProbe {
    public static void main(String[] args) throws Exception {
        long mainThread = Thread.currentThread().getId();
        AtomicReference<String> text = new AtomicReference<>();
        AtomicReference<Long> callbackThread = new AtomicReference<>();
        CountDownLatch received = new CountDownLatch(1);
        CountDownLatch timerReturned = new CountDownLatch(1);

        SDL_LogOutputFunction logOutput = SDL_LogOutputFunction.create(
            (userdata, category, priority, message) -> {
                text.set(MemoryUtil.memUTF8(message));
                callbackThread.set(Thread.currentThread().getId());
                received.countDown();
            }
        );
        SDLLog.SDL_SetLogOutputFunction(logOutput, 0L);
        SDL_TimerCallback timerCallback = SDL_TimerCallback.create((userdata, timerID, interval) -> {
            try {
                SDLLog.SDL_Log("LWJGL core callback verified");
                return 0;
            } finally { timerReturned.countDown(); }
        });
        int timer = SDLTimer.SDL_AddTimer(10, timerCallback, 0L);
        if (timer == 0) throw new AssertionError("SDL_AddTimer failed");
        if (!received.await(10, TimeUnit.SECONDS)) throw new AssertionError("SDL log callback timed out");
        if (!timerReturned.await(10, TimeUnit.SECONDS)) throw new AssertionError("SDL timer callback did not return");
        SDLTimer.SDL_RemoveTimer(timer);
        SDLLog.nSDL_SetLogOutputFunction(0L, 0L);
        timerCallback.free();
        logOutput.free();

        if (!"LWJGL core callback verified".equals(text.get()))
            throw new AssertionError("unexpected SDL log callback: "+text.get());
        if (callbackThread.get() == null || callbackThread.get() == mainThread)
            throw new AssertionError("native SDL timer callback did not attach a foreign thread");
        System.out.println("LWJGL CORE SDL FOREIGN-THREAD UP-CALL PASS");
    }
}
''')
            classpath=os.pathsep.join(map(str,[core,sdl,jspecify]))
            subprocess.run([str(jdk/'javac'),'--release','25','-cp',classpath,'-d',str(tmp),str(source)],check=True)
            native_path=ROOT/'build/lwjgl-core/host'
            java=[str(jdk/'java'),'--enable-native-access=ALL-UNNAMED',
                  '-Dorg.lwjgl.util.NoHashChecks=true',
                  f'-Dorg.lwjgl.librarypath={native_path}',
                  f'-Djava.library.path={native_path}',
                  '-cp',os.pathsep.join(map(str,[tmp,core,core_natives,sdl,sdl_natives,jspecify])),
                  'LWJGLCoreCallbackProbe']
            run=subprocess.run(java,cwd=ROOT,capture_output=True,text=True,timeout=25)
            self.assertEqual(run.returncode,0,run.stdout+run.stderr)
            self.assertIn('LWJGL CORE SDL FOREIGN-THREAD UP-CALL PASS',run.stdout)


if __name__=='__main__':
    unittest.main()
