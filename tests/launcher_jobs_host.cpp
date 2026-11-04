#include "launcher_jobs.hpp"
#include <cassert>
#include <chrono>
#include <thread>
int main(){
 sc::LauncherJob job;job.start("install",[](const sc::DownloadCallbacks& cb){
  for(int i=0;i<1000;i++){if(cb.cancelled())return sc::Json{{"cancelled",true}};cb.progress({(uint64_t)i,1000,"chunk"});std::this_thread::sleep_for(std::chrono::milliseconds(1));}
  return sc::Json{{"ok",true}};
 });
 std::this_thread::sleep_for(std::chrono::milliseconds(5));assert(job.snapshot().running);
 bool refused=false;try{job.start("overlap",{});}catch(...){refused=true;}assert(refused);
 job.cancel();for(int i=0;i<1000&&!job.snapshot().complete;i++)std::this_thread::sleep_for(std::chrono::milliseconds(1));
 assert(job.snapshot().complete&&job.snapshot().cancelled);job.reap();
 job.start("retry",[](const auto&){return sc::Json{{"ok",true}};});
 for(int i=0;i<1000&&!job.snapshot().complete;i++)std::this_thread::sleep_for(std::chrono::milliseconds(1));
 assert(job.snapshot().result["ok"]==true);job.reap();
 job.start("failure",[](const auto&)->sc::Json{throw std::runtime_error("visible error");});
 for(int i=0;i<1000&&!job.snapshot().complete;i++)std::this_thread::sleep_for(std::chrono::milliseconds(1));
 assert(job.snapshot().error=="visible error");job.reap();
}
