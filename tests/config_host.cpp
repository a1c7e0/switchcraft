#include "metadata.hpp"
#include <iostream>
int main(int argc,char**argv){try{if(argc!=2)return 2;auto config=sc::load_config(argv[1]);config.heap_mib=512;sc::save_config(argv[1],config);return 0;}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
