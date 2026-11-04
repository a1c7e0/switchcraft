#include "prism_metadata.hpp"
#include <iostream>
int main(int argc,char**argv) {
  try {
    if(argc!=4) return 2;
    if(std::string(argv[3])=="components") { std::cout<<sc::prism_components_for_version(argv[1],argv[2]).dump()<<'\n'; return 0; }
    if(std::string(argv[3])=="index") {
      auto versions=sc::load_prism_versions(argv[1],"org.example");
      sc::Json out=sc::Json::array(); for(const auto &v:versions) out.push_back({{"version",v.version},{"type",v.type},{"releaseTime",v.release_time},{"recommended",v.recommended}});
      std::cout<<out.dump()<<'\n'; return 0;
    }
    std::cout << sc::resolve_prism_pack(argv[1],"",argv[2]).dump() << '\n';
    return 0;
  } catch(const std::exception&e) { std::cerr<<e.what()<<'\n'; return 1; }
}
