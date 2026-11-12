"""Exercise LWJGL's genuine libffi upcall path through the cached SDL3 natives."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT=Path(__file__).resolve().parents[1]
JDK=ROOT/'.deps/host-jdk25/jdk-25.0.5+8/bin'
REFERENCE=Path('/tmp/r4-mc-reference/libraries/org/lwjgl')
CORE=REFERENCE/'lwjgl/3.4.3/lwjgl-3.4.3.jar'
SDL=REFERENCE/'lwjgl-sdl/3.4.3/lwjgl-sdl-3.4.3.jar'
SDL_NATIVES=REFERENCE/'lwjgl-sdl/3.4.3/lwjgl-sdl-3.4.3-natives-linux.jar'
CORE_NATIVES=REFERENCE/'lwjgl/3.4.3/lwjgl-3.4.3-natives-linux.jar'
JAVASPECIFY=ROOT/'.deps/jspecify.jar'


class TestLWJGLCoreCallbacks(unittest.TestCase):
    def test_sdl_timer_thread_calls_java_through_real_lwjgl_upcalls(self):
        required=[CORE,SDL,SDL_NATIVES,CORE_NATIVES,JAVASPECIFY]
        missing=[str(path) for path in required if not path.is_file()]
        if missing:
            self.skipTest('cached snapshot LWJGL libraries unavailable: '+', '.join(missing))
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
            classpath=os.pathsep.join(map(str,[CORE,SDL,JAVASPECIFY]))
            subprocess.run([str(JDK/'javac'),'--release','25','-cp',classpath,'-d',str(tmp),str(source)],check=True)
            native_path=ROOT/'build/lwjgl-core/host'
            java=[str(JDK/'java'),'--enable-native-access=ALL-UNNAMED',
                  '-Dorg.lwjgl.util.NoHashChecks=true',
                  f'-Dorg.lwjgl.librarypath={native_path}',
                  f'-Djava.library.path={native_path}',
                  '-cp',os.pathsep.join(map(str,[tmp,CORE,CORE_NATIVES,SDL,SDL_NATIVES,JAVASPECIFY])),
                  'LWJGLCoreCallbackProbe']
            run=subprocess.run(java,cwd=ROOT,capture_output=True,text=True,timeout=25)
            self.assertEqual(run.returncode,0,run.stdout+run.stderr)
            self.assertIn('LWJGL CORE SDL FOREIGN-THREAD UP-CALL PASS',run.stdout)


if __name__=='__main__':
    unittest.main()
