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
        else if(op=="archive"&&argc==5) {std::cout<<sc::archive_instance(runtime,argv[4])<<'\n';}
        else if(op=="archives"&&argc==4) {sc::Json out=sc::Json::array();for(const auto&i:sc::list_archived_instances(runtime))out.push_back({{"archive_id",i.archive_id},{"original_id",i.original_id},{"name",i.name},{"version",i.version},{"heap_mib",i.heap_mib}});std::cout<<out.dump()<<'\n';}
        else if(op=="restore"&&argc==5) {auto i=sc::restore_instance(runtime,argv[4]);std::cout<<sc::Json{{"id",i.id},{"name",i.name},{"version",i.version},{"heap_mib",i.heap_mib}}.dump()<<'\n';}
        else if(op=="import"&&(argc==7||argc==8)) {sc::ImportOptions o;o.max_files=(size_t)std::stoull(argv[5]);o.max_bytes=(size_t)std::stoull(argv[6]);if(argc==8)o.should_cancel=[](size_t,size_t){return true;};auto i=sc::import_instance(runtime,shared,argv[4],o);std::cout<<sc::Json{{"id",i.id},{"name",i.name},{"version",i.version},{"heap_mib",i.heap_mib}}.dump()<<'\n';}
        else if(op=="update"&&argc==6) {sc::update_instance_version(runtime,shared,argv[4],argv[5]);}
        else if(op=="plan"&&argc==5) {auto i=sc::load_instance(runtime,argv[4]);std::cout<<sc::make_instance_plan(i,shared,runtime).dump()<<'\n';}
        else throw std::runtime_error("invalid arguments");
    } catch(const std::exception &e) { std::cerr<<e.what()<<'\n'; return 1; }
    return 0;
}
