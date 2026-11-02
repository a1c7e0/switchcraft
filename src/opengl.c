#include "platform.h"
#include <EGL/egl.h>
#include <EGL/eglext.h>
#include <glad/glad.h>
#include <stdio.h>

static GLuint shader(GLenum type,const char *source) {
    GLuint s=glCreateShader(type); if(!s)return 0;
    glShaderSource(s,1,&source,NULL); glCompileShader(s);
    GLint ok=0; glGetShaderiv(s,GL_COMPILE_STATUS,&ok);
    if(!ok) {char log[1024];glGetShaderInfoLog(s,sizeof(log),NULL,log);
        sc_log("GL shader compile FAILED: %s\n",log); glDeleteShader(s);return 0;}
    return s;
}
static void test(void) {
    EGLDisplay display=EGL_NO_DISPLAY;
    EGLSurface surface=EGL_NO_SURFACE;
    EGLContext context=EGL_NO_CONTEXT;
    GLuint vs=0,fs=0,program=0,vao=0;
    unsigned frames=0; bool rendered=false;
    sc_log("Stage: EGL initialization (Mesa NVC0); entering graphics\n");
    sc_console(false);
    display=eglGetDisplay(EGL_DEFAULT_DISPLAY);
    EGLint major=0,minor=0,count=0; EGLConfig config;
    if(display==EGL_NO_DISPLAY||!eglInitialize(display,&major,&minor))goto done;
    sc_log("EGL %d.%d vendor=%s\n",major,minor,eglQueryString(display,EGL_VENDOR));
    if(!eglBindAPI(EGL_OPENGL_API))goto done;
    const EGLint attrs[]={EGL_RENDERABLE_TYPE,EGL_OPENGL_BIT,EGL_SURFACE_TYPE,EGL_WINDOW_BIT,
        EGL_RED_SIZE,8,EGL_GREEN_SIZE,8,EGL_BLUE_SIZE,8,EGL_NONE};
    if(!eglChooseConfig(display,attrs,&config,1,&count)||count!=1)goto done;
    surface=eglCreateWindowSurface(display,config,nwindowGetDefault(),NULL);
    if(surface==EGL_NO_SURFACE)goto done;
    const EGLint ctx[]={EGL_CONTEXT_MAJOR_VERSION_KHR,3,EGL_CONTEXT_MINOR_VERSION_KHR,3,
        EGL_CONTEXT_OPENGL_PROFILE_MASK_KHR,EGL_CONTEXT_OPENGL_CORE_PROFILE_BIT_KHR,EGL_NONE};
    context=eglCreateContext(display,config,EGL_NO_CONTEXT,ctx);
    if(context==EGL_NO_CONTEXT||!eglMakeCurrent(display,surface,surface,context))goto done;
    if(!gladLoadGL()) {sc_log("GLAD loader FAILED\n");goto done;}
    sc_log("GL_VENDOR=%s\nGL_RENDERER=%s\nGL_VERSION=%s\nGLSL=%s\n",
        glGetString(GL_VENDOR),glGetString(GL_RENDERER),glGetString(GL_VERSION),glGetString(GL_SHADING_LANGUAGE_VERSION));
    GLint extensions=0;glGetIntegerv(GL_NUM_EXTENSIONS,&extensions);
    for(GLint i=0;i<extensions;i++)sc_log("GL extension %s\n",glGetStringi(GL_EXTENSIONS,i));
    vs=shader(GL_VERTEX_SHADER,"#version 330 core\nconst vec2 p[3]=vec2[3](vec2(-0.7,-0.6),vec2(0.7,-0.6),vec2(0,0.7));void main(){gl_Position=vec4(p[gl_VertexID],0,1);}");
    fs=shader(GL_FRAGMENT_SHADER,"#version 330 core\nout vec4 color;void main(){color=vec4(0.15,0.85,0.3,1);}");
    if(!vs||!fs)goto done;
    program=glCreateProgram();glAttachShader(program,vs);glAttachShader(program,fs);glLinkProgram(program);
    GLint linked=0;glGetProgramiv(program,GL_LINK_STATUS,&linked);
    if(!linked) {char log[1024];glGetProgramInfoLog(program,sizeof(log),NULL,log);sc_log("GL link FAILED %s\n",log);goto done;}
    glGenVertexArrays(1,&vao); glBindVertexArray(vao);glUseProgram(program);
    PadState pad;padInitializeDefault(&pad);
    while(appletMainLoop()&&frames<600) {
        padUpdate(&pad);if(padGetButtonsDown(&pad)&(HidNpadButton_Plus|HidNpadButton_B))break;
        EGLint w=0,h=0;eglQuerySurface(display,surface,EGL_WIDTH,&w);eglQuerySurface(display,surface,EGL_HEIGHT,&h);
        if(w<=0||h<=0){sc_log("GL invalid surface size\n");break;}
        glViewport(0,0,w,h);glClearColor(0.02,0.06,0.15,1);glClear(GL_COLOR_BUFFER_BIT);
        glDrawArrays(GL_TRIANGLES,0,3);
        if(frames==0) {
            unsigned char pixel[4]={0};glReadPixels(w/2,h/2,1,1,GL_RGBA,GL_UNSIGNED_BYTE,pixel);
            rendered=pixel[1]>150&&pixel[0]<100&&pixel[2]<130;
            sc_log("GL center pixel=%u,%u,%u,%u %s\n",pixel[0],pixel[1],pixel[2],pixel[3],rendered?"PASS":"FAIL");
        }
        GLenum err=glGetError();
        if(err!=GL_NO_ERROR){sc_log("glGetError=0x%x\n",err);rendered=false;break;}
        if(!eglSwapBuffers(display,surface)){sc_log("eglSwapBuffers FAILED\n");rendered=false;break;}
        frames++;
    }
done:
    sc_log("EGL last error=0x%x; GL frames=%u readback=%s\n",eglGetError(),frames,rendered?"PASS":"NOT PASSED");
    if(vao)glDeleteVertexArrays(1,&vao);
    if(program)glDeleteProgram(program);
    if(vs)glDeleteShader(vs);
    if(fs)glDeleteShader(fs);
    if(display!=EGL_NO_DISPLAY) {
        eglMakeCurrent(display,EGL_NO_SURFACE,EGL_NO_SURFACE,EGL_NO_CONTEXT);
        if(context!=EGL_NO_CONTEXT)eglDestroyContext(display,context);
        if(surface!=EGL_NO_SURFACE)eglDestroySurface(display,surface);
        eglTerminate(display);
    }
    sc_console(true);
    sc_log("OpenGL test finished: frames=%u readback=%s. See opengl-test.log\n",frames,rendered?"PASS":"NOT PASSED");
}
int main(void) {
    sc_init("opengl-test");
    sc_log("A: test EGL/OpenGL and green triangle (up to 600 frames)\nB: diagnostics | +: exit\n");
    u64 keys;
    while(sc_frame(&keys)) {
        if(keys&HidNpadButton_A)test();
        if((keys&HidNpadButton_B)&&sc_chain("switch-diagnostics"))break;
    }
    sc_exit();return 0;
}
