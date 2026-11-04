#include "instances.hpp"
#include <iostream>
#include <stdexcept>

int main(int argc,char **argv) {
    try {
        if(argc<3) throw std::runtime_error("usage");
        std::string runtime=argv[1],shared=argv[2],op=argc>3?argv[3]:"";
        if(op=="create"&&argc==7) { auto i=sc::create_instance(runtime,shared,argv[4],argv[5],(unsigned)std::stoul(argv[6])); std::cout<<sc::Json{{"id",i.id},{"name",i.name},{"version",i.version},{"heap_mib",i.heap_mib}}.dump()<<'\n'; }
        else if(op=="list"&&argc==4) { sc::Json out=sc::Json::array(); for(const auto&i:sc::scan_instances(runtime)) out.push_back({{"id",i.id},{"name",i.name},{"version",i.version},{"heap_mib",i.heap_mib}}); std::cout<<out.dump()<<'\n'; }
        else if(op=="load"&&argc==5) { auto i=sc::load_instance(runtime,argv[4]); std::cout<<i.id<<'\n'; }
        else if(op=="rename"&&argc==6) { sc::rename_instance(runtime,argv[4],argv[5]); }
        else if(op=="set"&&argc==7) { auto i=sc::load_instance(runtime,argv[4]);i.version=argv[5];i.heap_mib=(unsigned)std::stoul(argv[6]);sc::save_instance(runtime,i); }
        else if(op=="duplicate"&&argc==6) {auto i=sc::duplicate_instance(runtime,shared,argv[4],argv[5]);std::cout<<sc::Json{{"id",i.id},{"name",i.name},{"version",i.version},{"heap_mib",i.heap_mib}}.dump()<<'\n';}
        else if(op=="plan"&&argc==5) {auto i=sc::load_instance(runtime,argv[4]);std::cout<<sc::make_instance_plan(i,shared,runtime).dump()<<'\n';}
        else throw std::runtime_error("invalid arguments");
    } catch(const std::exception &e) { std::cerr<<e.what()<<'\n'; return 1; }
    return 0;
}
