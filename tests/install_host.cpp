#include "install.hpp"
#include <iostream>
int main(int argc,char**argv){
 try{
  if(argc<6)return 2;
  sc::InstallOptions o;o.prism_base_url=argv[3];o.asset_base_url=argv[4];o.allow_test_mirror=std::string(argv[2])!="badmirror";o.allow_http_for_tests=o.allow_test_mirror;
  if(argc>6)o.repair_corrupt_managed_cache=std::string(argv[6])=="repair";
  sc::DownloadCallbacks cb;if(std::string(argv[2])=="cancel"||std::string(argv[2])=="verifycancel")cb.cancelled=[](){return true;};
  sc::InstallReport r;
  if(std::string(argv[2])=="refresh")r=sc::refresh_catalog(argv[1],argv[5],o,cb);
  else if(std::string(argv[2])=="install"||std::string(argv[2])=="cancel")r=sc::prepare_install(argv[1],argv[5],o,cb);
  else if(std::string(argv[2])=="verify"||std::string(argv[2])=="verifycancel")r=sc::verify_install(argv[1],argv[5],o,cb);
  else if(std::string(argv[2])=="badmirror")r=sc::refresh_catalog(argv[1],argv[5],o,cb);
  else return 2;
  std::cout<<r.to_json().dump()<<'\n';return r.ok?0:1;
 }catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}
}
