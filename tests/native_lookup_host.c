#include <switchcraft/native_lookup.h>
#include <assert.h>
#include <stddef.h>
static int add(int a,int b) { return a+b; }
int main(void) {
    const ScNativeSymbol table[]={{"sample","add",(ScNativeFunction)add},{"bad","null",NULL}};
    ScNativeFunction f=sc_lookup_table(table,2,"sample","add");
    assert(f && ((int (*)(int,int))f)(20,22)==42);
    assert(!sc_lookup_table(table,2,"sample","missing"));
    assert(!sc_lookup_table(table,2,"other","add"));
    assert(!sc_lookup_table(table,2,"bad","null"));
    assert(!sc_lookup_table(NULL,2,"sample","add"));
    assert(!sc_lookup_table(table,2,NULL,"add"));
    assert(!sc_lookup_table(table,2,"sample",""));
    return 0;
}
