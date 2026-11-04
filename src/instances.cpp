#include "instances.hpp"
#include "prism_metadata.hpp"
#include <algorithm>
#include <cctype>
#include <cerrno>
#include <dirent.h>
#include <fcntl.h>
#include <fstream>
#include <map>
#include <stdexcept>
#include <sys/stat.h>
#include <unistd.h>

namespace sc {
namespace {
constexpr size_t kMetadataLimit = 64 * 1024;
constexpr unsigned kHeapMin = 128, kHeapMax = 1024;
std::string join(const std::string &a, const std::string &b) { return a + "/" + b; }
void validate_name(const std::string &name) {
    if (name.empty() || name.size() > 96 || name.find_first_of("\r\n\t") != name.npos)
        throw std::runtime_error("Instance name must be 1..96 printable characters");
    for (unsigned char c : name) if (c < 32 || c == 127) throw std::runtime_error("Invalid instance name");
}
void validate_heap(unsigned heap) {
    if (heap < kHeapMin || heap > kHeapMax) throw std::runtime_error("Heap must be 128..1024 MiB");
}
void require_directory(const std::string &path, bool allow_missing=false) {
    struct stat st{};
    if (lstat(path.c_str(), &st) != 0) {
        if (allow_missing && errno == ENOENT) return;
        throw std::runtime_error("Cannot access directory: " + path);
    }
    if (!S_ISDIR(st.st_mode)) throw std::runtime_error("Expected real directory (symlinks are not allowed): " + path);
}
void ensure_instances_dir(const std::string &runtime_root) {
    require_directory(runtime_root);
    std::string path=join(runtime_root,"instances");
    if (mkdir(path.c_str(),0755)!=0 && errno!=EEXIST) throw std::runtime_error("Cannot create instances directory");
    require_directory(path);
}
std::string dir_for(const std::string &root,const std::string &id) {
    if (!safe_id(id)) throw std::runtime_error("Unsafe instance ID");
    return join(join(root,"instances"),id);
}
void validate_instance(const Instance &i) {
    if (!safe_id(i.id)) throw std::runtime_error("Unsafe instance ID");
    validate_name(i.name);
    if (!safe_id(i.version)) throw std::runtime_error("Invalid installed version ID");
    validate_heap(i.heap_mib);
}
std::string ini_unescape(const std::string &s) {
    std::string out; bool escaped=false;
    for(char c:s) {
        if(escaped) {
            if(c=='n') out+='\n'; else if(c=='t') out+='\t'; else out+=c;
            escaped=false;
        } else if(c=='\\') escaped=true; else out+=c;
    }
    if(escaped) throw std::runtime_error("Trailing Prism INI escape");
    return out;
}
std::map<std::string,std::string> read_ini(const std::string &path) {
    struct stat st{}; if(lstat(path.c_str(),&st)!=0||!S_ISREG(st.st_mode)||st.st_size<0||(size_t)st.st_size>kMetadataLimit) throw std::runtime_error("Invalid or oversized instance.cfg");
    std::ifstream in(path); if(!in) throw std::runtime_error("Cannot read instance.cfg");
    std::map<std::string,std::string> values; std::string line,section;
    while(std::getline(in,line)) {
        if(line.empty()||line[0]=='#'||line[0]==';') continue;
        if(line.front()=='[') {
            if(line.size()<3||line.back()!=']'||line.find('\\')!=line.npos) throw std::runtime_error("Unsupported Prism INI section syntax");
            section=line.substr(1,line.size()-2); if(section.find_first_of("[]\r\n")!=section.npos) throw std::runtime_error("Invalid Prism INI section"); continue;
        }
        auto eq=line.find('='); if(eq==std::string::npos||eq==0) throw std::runtime_error("Unsupported Prism INI line");
        std::string key=line.substr(0,eq),value=line.substr(eq+1);
        if(key.find('\\')!=key.npos) throw std::runtime_error("Unsupported Prism INI key escape");
        if(value.size()>=2&&value.front()=='"'&&value.back()=='"') value=value.substr(1,value.size()-2);
        else if(value.find('"')!=value.npos) throw std::runtime_error("Unsupported quoted Prism INI value");
        if(!section.empty()) key=section+"/"+key;
        values[key]=ini_unescape(value);
    }
    return values;
}
std::string ini_escape(const std::string &s) {
    const bool quote=s.find_first_of(";=,")!=s.npos;
    std::string out; if(quote) out+='"';
    for(char c:s) {
        if(c=='\\') out+="\\\\"; else if(c=='\n') out+="\\n"; else if(c=='\t') out+="\\t";
        else if(c=='#') out+="\\#"; else if(c=='"'&&quote) out+="\\\""; else out+=c;
    }
    if(quote) out+='"';
    return out;
}
std::string ini_encode(const std::map<std::string,std::string> &values) {
    std::string out="ConfigVersion=1.3\n";
    for(const auto &p:values) if(p.first!="ConfigVersion"&&p.first.find('/')==p.first.npos) out+=p.first+"="+ini_escape(p.second)+"\n";
    std::string section;
    for(const auto &p:values) {
        auto slash=p.first.find('/'); if(slash==p.first.npos) continue;
        std::string group=p.first.substr(0,slash),key=p.first.substr(slash+1);
        if(group!=section) { section=group; out+="["+section+"]\n"; }
        out+=key+"="+ini_escape(p.second)+"\n";
    }
    return out;
}
void write_atomic(const std::string &path,const std::string &data,bool exclusive) {
    std::string target=exclusive?path:path+".tmp";
    int fd=open(target.c_str(),O_WRONLY|O_CREAT|O_EXCL,0644);
    if(fd<0) throw std::runtime_error("Cannot create instance metadata file");
    size_t pos=0; bool failed=false;
    while(pos<data.size()) { ssize_t n=write(fd,data.data()+pos,data.size()-pos); if(n<=0){failed=true;break;} pos+=(size_t)n; }
    int sync_result=failed?-1:fsync(fd);
    int close_result=close(fd);
    if(failed||sync_result!=0||close_result!=0){unlink(target.c_str());throw std::runtime_error("Cannot flush instance metadata");}
    if(!exclusive&&rename(target.c_str(),path.c_str())!=0){unlink(target.c_str());throw std::runtime_error("Cannot commit instance metadata");}
}
std::string stage_atomic(const std::string &path,const std::string &data) {
    std::string temp=path+".tmp";
    int fd=open(temp.c_str(),O_WRONLY|O_CREAT|O_EXCL,0644);
    if(fd<0) throw std::runtime_error("Cannot create instance metadata temporary file");
    size_t pos=0; bool failed=false;
    while(pos<data.size()) { ssize_t n=write(fd,data.data()+pos,data.size()-pos); if(n<=0){failed=true;break;} pos+=(size_t)n; }
    int sync_result=failed?-1:fsync(fd); int close_result=close(fd);
    if(failed||sync_result!=0||close_result!=0){unlink(temp.c_str());throw std::runtime_error("Cannot flush instance metadata temporary file");}
    return temp;
}
void commit_staged(const std::string &temp,const std::string &path) {
    if(rename(temp.c_str(),path.c_str())!=0){unlink(temp.c_str());throw std::runtime_error("Cannot commit instance metadata");}
}
Json pack(const std::string &shared_root,const std::string &version) {
    if(!safe_id(version)) throw std::runtime_error("Invalid installed version ID");
    const std::string cached=join(join(join(shared_root,"meta"),"net.minecraft"),version+".json");
    Json components=file_exists(cached)?prism_components_for_version(shared_root,version):Json::array({Json{{"uid","net.minecraft"},{"version",version},{"important",true}}});
    return Json{{"formatVersion",1},{"components",std::move(components)}};
}
Instance decode(const std::string &dir,const std::string &expected) {
    auto cfg=read_ini(join(dir,"instance.cfg"));
    struct stat st{}; std::string pack_path=join(dir,"mmc-pack.json");
    if(lstat(pack_path.c_str(),&st)!=0||!S_ISREG(st.st_mode)||st.st_size<0||(size_t)st.st_size>kMetadataLimit) throw std::runtime_error("Invalid or oversized mmc-pack.json");
    std::ifstream in(pack_path); Json j; in>>j;
    if(j.value("formatVersion",0)!=1||!j.contains("components")||!j["components"].is_array()) throw std::runtime_error("Unsupported Prism component profile");
    std::string version; for(const auto &c:j["components"]) if(c.value("uid",std::string())=="net.minecraft") version=c.at("version").get<std::string>();
    Instance i{expected,cfg.count("name")?cfg["name"]:"Unnamed Instance",version,512};
    if(cfg.count("MaxMemAlloc")){try{i.heap_mib=(unsigned)std::stoul(cfg["MaxMemAlloc"]);}catch(...){throw std::runtime_error("Invalid Prism MaxMemAlloc");}}
    validate_instance(i); return i;
}
std::string slug(const std::string &name) {
    std::string out; bool dash=false;
    for(unsigned char c:name) {
        if(std::isalnum(c)) { out+=(char)std::tolower(c); dash=false; }
        else if(!out.empty()&&!dash) { out+='-'; dash=true; }
        if(out.size()>=48) break;
    }
    while(!out.empty()&&out.back()=='-') out.pop_back();
    if(out.empty()) out="instance";
    return out;
}
void require_version(const std::string &shared_root,const std::string &runtime_root,const std::string &version) {
    if(!safe_id(version)) throw std::runtime_error("Invalid version ID");
    struct stat st{};
    std::string versions=join(shared_root,"versions"), version_dir=join(versions,version);
    if(lstat(versions.c_str(),&st)==0&&S_ISDIR(st.st_mode)&&
       lstat(version_dir.c_str(),&st)==0&&S_ISDIR(st.st_mode)) {
        std::string meta=join(version_dir,version+".json");
        if(lstat(meta.c_str(),&st)==0&&S_ISREG(st.st_mode)&&st.st_size>=0&&st.st_size<=4*1024*1024) return;
    }
    std::string meta_root=join(shared_root,"meta"), mc_meta=join(meta_root,"net.minecraft");
    std::string prism_meta=join(mc_meta,version+".json");
    struct stat root_st{},meta_st{};
    if(lstat(meta_root.c_str(),&root_st)==0&&S_ISDIR(root_st.st_mode)&&
       lstat(mc_meta.c_str(),&meta_st)==0&&S_ISDIR(meta_st.st_mode)&&
       lstat(prism_meta.c_str(),&st)==0&&S_ISREG(st.st_mode)&&st.st_size>=0&&st.st_size<=4*1024*1024) return;
    (void)runtime_root;
    throw std::runtime_error("Version is not installed or present in Prism's local cache");
}
struct LocalPatch { std::string filename, data; };
std::vector<LocalPatch> read_local_patches(const std::string &instance_dir) {
    const std::string dir=join(instance_dir,"patches"); struct stat st{};
    if(lstat(dir.c_str(),&st)!=0) { if(errno==ENOENT) return {}; throw std::runtime_error("Cannot inspect Prism patches directory"); }
    if(!S_ISDIR(st.st_mode)) throw std::runtime_error("Prism patches path is not a real directory");
    DIR *d=opendir(dir.c_str()); if(!d) throw std::runtime_error("Cannot read Prism patches directory");
    std::vector<LocalPatch> out; size_t total=0;
    try {
        while(auto *entry=readdir(d)) {
            std::string filename=entry->d_name;
            if(filename=="."||filename=="..") continue;
            if(filename.size()<6||filename.substr(filename.size()-5)!=".json") throw std::runtime_error("Unsupported entry in Prism patches directory");
            std::string stem=filename.substr(0,filename.size()-5); if(!safe_id(stem)) throw std::runtime_error("Unsafe Prism patch filename");
            std::string path=join(dir,filename); struct stat file{};
            if(lstat(path.c_str(),&file)!=0||!S_ISREG(file.st_mode)||file.st_size<0||(size_t)file.st_size>4*1024*1024) throw std::runtime_error("Invalid or oversized Prism patch file");
            total+=(size_t)file.st_size; if(total>8*1024*1024||out.size()>=64) throw std::runtime_error("Prism patch size/count limit");
            std::ifstream in(path,std::ios::binary); std::string data((std::istreambuf_iterator<char>(in)),{});
            if(!in.eof()&&!in) throw std::runtime_error("Cannot read Prism patch file");
            Json parsed=Json::parse(data); if(!parsed.is_object()) throw std::runtime_error("Expected Prism patch object");
            out.push_back({filename,std::move(data)});
        }
    } catch(...) { closedir(d); throw; }
    closedir(d); return out;
}
Instance create_with_id(const std::string &root,const std::string &shared,const std::string &name,
                        const std::string &version,unsigned heap,const std::string &id) {
    validate_name(name); validate_heap(heap); require_version(shared,root,version); ensure_instances_dir(root);
    Instance i{id,name,version,heap}; validate_instance(i);
    std::string dir=dir_for(root,id);
    if(mkdir(dir.c_str(),0755)!=0) throw std::runtime_error("Instance ID already exists");
    if(mkdir(join(dir,".minecraft").c_str(),0755)!=0) { rmdir(dir.c_str()); throw std::runtime_error("Cannot create game directory"); }
    try {
        std::map<std::string,std::string> cfg{{"InstanceType","OneSix"},{"name",name},{"OverrideMemory","true"},{"MinMemAlloc","64"},{"MaxMemAlloc",std::to_string(heap)}};
        write_atomic(join(dir,"instance.cfg"),ini_encode(cfg),true);
        write_atomic(join(dir,"mmc-pack.json"),pack(shared,version).dump(2)+"\n",true);
    } catch(...) { unlink(join(dir,"instance.cfg").c_str()); unlink(join(dir,"mmc-pack.json").c_str()); rmdir(join(dir,".minecraft").c_str()); rmdir(dir.c_str()); throw; }
    return i;
}

}
std::vector<Instance> scan_instances(const std::string &runtime_root,std::vector<std::string> *errors) {
    ensure_instances_dir(runtime_root); std::vector<Instance> out;
    DIR *d=opendir(join(runtime_root,"instances").c_str()); if(!d) throw std::runtime_error("Cannot scan instances");
    while(auto *e=readdir(d)) {
        std::string id=e->d_name; if(id=="."||id==".."||!safe_id(id)) continue;
        struct stat st{}; std::string dir=dir_for(runtime_root,id);
        if(lstat(dir.c_str(),&st)!=0||!S_ISDIR(st.st_mode)) continue;
        struct stat cfg_st{},pack_st{};
        bool has_cfg=lstat(join(dir,"instance.cfg").c_str(),&cfg_st)==0;
        bool has_pack=lstat(join(dir,"mmc-pack.json").c_str(),&pack_st)==0;
        if(!has_cfg&&!has_pack) continue;
        try { out.push_back(load_instance(runtime_root,id)); } catch(const std::exception &e) { if(errors) errors->push_back(id+": "+e.what()); }
        if(out.size()>=256) break;
    }
    closedir(d); std::sort(out.begin(),out.end(),[](const Instance&a,const Instance&b){return a.name==b.name?a.id<b.id:a.name<b.name;}); return out;
}
Instance load_instance(const std::string &root,const std::string &id) {
    if(!safe_id(id)) throw std::runtime_error("Unsafe instance ID");
    require_directory(join(root,"instances"));
    std::string dir=dir_for(root,id); require_directory(dir); require_directory(join(dir,".minecraft"));
    return decode(dir,id);
}
Instance create_instance(const std::string &root,const std::string &shared,const std::string &name,const std::string &version,unsigned heap) {
    validate_name(name); ensure_instances_dir(root); std::string base=slug(name),id=base;
    for(unsigned n=2;n<10000;++n) { struct stat st{}; if(lstat(dir_for(root,id).c_str(),&st)!=0&&errno==ENOENT) break; id=base+"-"+std::to_string(n); }
    return create_with_id(root,shared,name,version,heap,id);
}
void save_instance(const std::string &root,const Instance &i) {
    validate_instance(i); const std::string dir=dir_for(root,i.id); Instance old=load_instance(root,i.id); (void)old;
    auto cfg=read_ini(join(dir,"instance.cfg")); cfg["name"]=i.name; cfg["InstanceType"]="OneSix"; cfg["OverrideMemory"]="true"; cfg["MinMemAlloc"]="64"; cfg["MaxMemAlloc"]=std::to_string(i.heap_mib);
    std::ifstream pin(join(dir,"mmc-pack.json")); Json profile; pin>>profile;
    bool found=false; for(auto &component:profile["components"]) if(component.value("uid",std::string())=="net.minecraft") { component["version"]=i.version; found=true; }
    if(!found) profile["components"].push_back({{"uid","net.minecraft"},{"version",i.version},{"important",true}});
    const std::string cfg_path=join(dir,"instance.cfg"), pack_path=join(dir,"mmc-pack.json");
    std::string cfg_tmp=stage_atomic(cfg_path,ini_encode(cfg)), pack_tmp;
    try { pack_tmp=stage_atomic(pack_path,profile.dump(2)+"\n"); }
    catch(...) { unlink(cfg_tmp.c_str()); throw; }
    commit_staged(cfg_tmp,cfg_path); commit_staged(pack_tmp,pack_path);
}
void rename_instance(const std::string &root,const std::string &id,const std::string &new_name) { Instance i=load_instance(root,id); i.name=new_name; save_instance(root,i); }
std::string instance_game_directory(const std::string &root,const std::string &id) { load_instance(root,id); return join(dir_for(root,id),".minecraft"); }
Instance duplicate_instance(const std::string &root,const std::string &shared,const std::string &id,const std::string &new_name) {
    Instance src=load_instance(root,id); validate_name(new_name);
    const std::string source_dir=dir_for(root,id);
    auto cfg=read_ini(join(source_dir,"instance.cfg")); cfg["name"]=new_name;
    std::ifstream pack_in(join(source_dir,"mmc-pack.json"),std::ios::binary);
    std::string pack_data((std::istreambuf_iterator<char>(pack_in)),{});
    if(!pack_in.eof()&&!pack_in) throw std::runtime_error("Cannot read Prism component profile");
    Json parsed_pack=Json::parse(pack_data); if(!parsed_pack.is_object()) throw std::runtime_error("Invalid Prism component profile");
    auto patches=read_local_patches(source_dir);
    Instance dst=create_instance(root,shared,new_name,src.version,src.heap_mib);
    const std::string target_dir=dir_for(root,dst.id), cfg_path=join(target_dir,"instance.cfg"), pack_path=join(target_dir,"mmc-pack.json");
    try {
        std::string cfg_tmp=stage_atomic(cfg_path,ini_encode(cfg)), pack_tmp;
        try { pack_tmp=stage_atomic(pack_path,pack_data); }
        catch(...) { unlink(cfg_tmp.c_str()); throw; }
        commit_staged(cfg_tmp,cfg_path); commit_staged(pack_tmp,pack_path);
        if(!patches.empty()) {
            std::string target_patches=join(target_dir,"patches");
            if(mkdir(target_patches.c_str(),0755)!=0) throw std::runtime_error("Cannot create duplicate patches directory");
            for(const auto &patch:patches) write_atomic(join(target_patches,patch.filename),patch.data,true);
        }
    } catch(...) {
        for(const auto &patch:patches) unlink(join(join(target_dir,"patches"),patch.filename).c_str());
        rmdir(join(target_dir,"patches").c_str()); unlink(cfg_path.c_str()); unlink(pack_path.c_str());
        unlink((cfg_path+".tmp").c_str()); unlink((pack_path+".tmp").c_str());
        rmdir(join(target_dir,".minecraft").c_str()); rmdir(target_dir.c_str()); throw;
    }
    return dst;
}
Config instance_config(const Instance &i,const std::string &shared_root) {
    validate_instance(i); Config c; c.root=shared_root; c.version=i.version; c.heap_mib=i.heap_mib; return c;
}
Json make_instance_plan(const Instance &i,const std::string &shared_root,const std::string &runtime_root) {
    const std::string cached=join(join(join(shared_root,"meta"),"net.minecraft"),i.version+".json");
    Json normalized;
    if(file_exists(cached)) normalized=resolve_prism_pack(shared_root,runtime_root,dir_for(runtime_root,i.id));
    return make_plan(instance_config(i,shared_root),runtime_root,instance_game_directory(runtime_root,i.id),normalized);
}
}
