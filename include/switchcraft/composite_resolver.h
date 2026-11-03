#ifndef SWITCHCRAFT_COMPOSITE_RESOLVER_H
#define SWITCHCRAFT_COMPOSITE_RESOLVER_H
#ifdef __cplusplus
extern "C" {
#endif
/* Install the immutable JDK + Switchcraft provider before VM initialization. */
int sc_install_composite_resolver(void);
#ifdef __cplusplus
}
#endif
#endif
