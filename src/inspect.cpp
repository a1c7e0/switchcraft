#include "metadata.hpp"
#include <iostream>
int main(int argc,char **argv) {
    try {
        if(argc==3&&std::string(argv[1])=="--manifest") {
            for(const auto &id:sc::manifest_ids(sc::read_json(argv[2])))std::cout<<id<<'\n';
            return 0;
        }
        if(argc!=3){std::cerr<<"Usage: switchcraft-inspect ROOT VERSION | --manifest FILE\n";return 2;}
        sc::Config c;c.root=argv[1];c.version=argv[2];
        std::cout<<sc::make_plan(c,"/switch/mc-runtime").dump(2)<<'\n';
    }catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}
}
