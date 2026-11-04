// Host CLI for the same production installer linked into the launcher NRO.
#include "install.hpp"
#include <chrono>
#include <csignal>
#include <fstream>
#include <iostream>
#include <filesystem>
static volatile std::sig_atomic_t interrupted=0;
static void on_signal(int){interrupted=1;}
int main(int argc,char **argv){
 try{
  if(argc<3){std::cerr<<"Usage: switchcraft-install ROOT refresh|install|verify [VERSION] [--repair]\n";return 2;}
  std::filesystem::path root=std::filesystem::absolute(argv[1]).lexically_normal();
  auto repo=std::filesystem::current_path();auto dist=repo/"dist";
  auto relative=root.lexically_relative(dist);
  if(root==dist||(!relative.empty()&&*relative.begin()!=".."))throw std::runtime_error("Use a private cache outside dist");
  std::string action=argv[2],version=argc>3?argv[3]:sc::kPinnedMinecraftVersion;
  sc::InstallOptions options;for(int n=4;n<argc;n++)if(std::string(argv[n])=="--repair")options.repair_corrupt_managed_cache=true;else throw std::runtime_error("Unknown option");
  std::signal(SIGINT,on_signal);sc::DownloadCallbacks cb;cb.cancelled=[](){return interrupted!=0;};
  auto last=std::chrono::steady_clock::now();cb.progress=[&](const auto&p){auto now=std::chrono::steady_clock::now();if(now-last>std::chrono::milliseconds(750)){std::cerr<<p.bytes<<"/"<<p.total<<" "<<p.message<<'\n';last=now;}return interrupted==0;};
  sc::InstallReport report;
  if(action=="refresh")report=sc::refresh_catalog(root.string(),version,options,cb);
  else if(action=="install")report=sc::prepare_install(root.string(),version,options,cb);
  else if(action=="verify")report=sc::verify_install(root.string(),version,options,cb);
  else throw std::runtime_error("Unknown action");
  std::cout<<report.to_json().dump(2)<<'\n';sc::shutdown_download_transport();return report.ok?0:1;
 }catch(const std::exception&e){std::cerr<<e.what()<<'\n';sc::shutdown_download_transport();return 1;}
}
