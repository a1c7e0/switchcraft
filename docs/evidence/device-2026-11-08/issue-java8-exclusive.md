Runtime revision:
Class-library bytes from b7c2ac7fd422bc2543e5c698db4e33a01cc0312d, extracted from the immutable original SD ZIP. The host miniJVM runner used 9f6ac4efc04a1750fe54c62d72c4401fda89e68a; the failing Java class-library implementation is unchanged at B7. The fix is already in 6503f4f (now included in bff51f38e218af147ca0c9f255fcf1b43be72daf).

Switchcraft revision:
91b0eb029bfd2ef93bbf6527795e9642a83a15fa plus uncommitted R2 integration/evidence. This is independent of the sdmc:/ resolution defect in issue6.

Execution environment:
Linux x86_64 host execution of the real miniJVM interpreter and original Java8 class library; not Horizon. Host compile uses Temurin8 javac -source8 -target8 and the pinned miniJVM runtime bootclasspath. The corresponding device suite will run application-mode Switch firmware21.2.0; no new device result exists.

Reproduction:
Extract switch/mc-runtime/runtimes/minijvm/minijvm_rt.jar from the original test-suite-2026-11-08 ZIP (SHA256 5626a9e6e0f56cbbe89830e8e9bc35c93436a5f13fff1f3bb4037860ca4c696e). Compile a class named DiagnosticSmoke with the following code against that runtime JAR, put it in ROOT/tests/diagnostic-tests.jar, and run the real build/java-test-host ROOT. ROOT also needs runtimes/minijvm/minijvm_rt.jar and an empty tests/dependency.jar.

```java
import java.io.*;
public class DiagnosticSmoke {
 public static void main(String[] a) throws Exception {
  File dir=new File(a[0]);dir.mkdirs();
  File f=new File(dir,"owned-exclusivity-repro.tmp");
  if(f.exists())throw new IOException("refuse existing reproducer file");
  System.out.println("FIRST_CREATE="+f.createNewFile());
  try {
   try {System.out.println("SECOND_CREATE="+f.createNewFile());}
   catch(IOException e){System.out.println("SECOND_CREATE_THREW="+e);}
  } finally {f.delete();}
 }
}
```

Expected behavior:
First create returns true; second create returns false and preserves the existing file. Other native I/O failures throw IOException. Exclusive creation must use a native O_CREAT|O_EXCL primitive rather than a check-then-truncate race.

Actual behavior:
FIRST_CREATE=true; SECOND_CREATE_THREW=java.io.IOException: file exists.

Evidence:
```text
Initializing miniJVM interpreter, classic GC, Java 8 class library
[INFO] object layout: ptr=64b MemoryBlock=24 Instance=24 JArrayHeader=32 field_off=24 arr_len_off=24 arr_body_off=32
[INFO] gc backend : classic malloc
jvm_init -> 0
FIRST_CREATE=true
SECOND_CREATE_THREW=java.io.IOException: file exists.
call_main -> 0
JVM teardown begins
JVM teardown completed

```
No Horizon Java25 VM was involved; java25-test.log/stdout/stderr and crash reports are not relevant to this host Java8 API reproducer.

Analysis:
Confirmed source: FileSystemImpl.createFileExclusively throws on existing-file loadFS results and otherwise uses a separate existence check followed by fopen mode w, which violates the return contract and is not atomic. Device URI absolute resolution in issue6 is a separate prerequisite; this POSIX absolute host path reproduces without sdmc:/.

Requested action for java-switch:
Retain the maintained Java/native exclusive-create fix in 6503f4f, preserve existing bytes, and validate false-on-existing plus I/O errno distinctions. The new genuine miniJVM host regression passes; physical R2 java-test A must still validate the new path and API together before closing the device-facing work.
