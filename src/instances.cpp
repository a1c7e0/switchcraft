#include "instances.hpp"
#include "prism_metadata.hpp"
#include <algorithm>
#include <cctype>
#include <cerrno>
#include <dirent.h>
#include <fcntl.h>
#include <fstream>
#include <filesystem>
#include <limits>
#include <map>
#include <set>
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
struct IniDocument {
    std::map<std::string,std::string> values;
    std::map<std::string,std::string> opaque_values;
};
void append_utf8(std::string &out,unsigned cp) {
    if(cp<=0x7f) out+=(char)cp;
    else if(cp<=0x7ff) { out+=(char)(0xc0|(cp>>6)); out+=(char)(0x80|(cp&0x3f)); }
    else if(cp<=0xffff) { out+=(char)(0xe0|(cp>>12)); out+=(char)(0x80|((cp>>6)&0x3f)); out+=(char)(0x80|(cp&0x3f)); }
    else { out+=(char)(0xf0|(cp>>18)); out+=(char)(0x80|((cp>>12)&0x3f)); out+=(char)(0x80|((cp>>6)&0x3f)); out+=(char)(0x80|(cp&0x3f)); }
}
unsigned hex4(const std::string &s,size_t p) {
    if(p+4>s.size()) throw std::runtime_error("Truncated Qt INI Unicode escape");
    unsigned value=0;
    for(size_t i=0;i<4;++i) { unsigned char c=s[p+i]; unsigned digit;
        if(c>='0'&&c<='9') digit=c-'0'; else if(c>='a'&&c<='f') digit=c-'a'+10; else if(c>='A'&&c<='F') digit=c-'A'+10; else throw std::runtime_error("Invalid Qt INI Unicode escape");
        value=(value<<4)|digit;
    }
    return value;
}
std::string ini_unescape(const std::string &s) {
    std::string out;
    for(size_t i=0;i<s.size();++i) {
        char c=s[i]; if(c!='\\') { out+=c; continue; }
        if(++i>=s.size()) throw std::runtime_error("Trailing Qt INI escape");
        c=s[i];
        if(c=='x') {
            unsigned cp=hex4(s,i+1); i+=4;
            if(cp>=0xd800&&cp<=0xdbff) {
                if(i+6>=s.size()||s[i+1]!='\\'||s[i+2]!='x') throw std::runtime_error("Invalid Qt INI surrogate pair");
                unsigned low=hex4(s,i+3); if(low<0xdc00||low>0xdfff) throw std::runtime_error("Invalid Qt INI surrogate pair");
                cp=0x10000+((cp-0xd800)<<10)+(low-0xdc00); i+=6;
            } else if(cp>=0xdc00&&cp<=0xdfff) throw std::runtime_error("Unpaired Qt INI low surrogate");
            append_utf8(out,cp);
        } else if(c=='n') out+='\n'; else if(c=='r') out+='\r'; else if(c=='t') out+='\t';
        else if(c=='b') out+='\b'; else if(c=='f') out+='\f'; else if(c=='v') out+='\v';
        else out+=c;
    }
    return out;
}
std::string trim_ascii(const std::string &s) {
    size_t first=s.find_first_not_of(" \t\r"),last=s.find_last_not_of(" \t\r");
    return first==s.npos?std::string():s.substr(first,last-first+1);
}
bool opaque_qsettings_value(const std::string &s) {
    return s.size()>1&&s[0]=='@'&&s[1]!='@'&&s.find('(')!=s.npos;
}
IniDocument read_ini(const std::string &path) {
    struct stat st{}; if(lstat(path.c_str(),&st)!=0||!S_ISREG(st.st_mode)||st.st_size<0||(size_t)st.st_size>kMetadataLimit) throw std::runtime_error("Invalid or oversized instance.cfg");
    std::ifstream in(path); if(!in) throw std::runtime_error("Cannot read instance.cfg");
    IniDocument doc; std::string line,section;
    while(std::getline(in,line)) {
        if(!line.empty()&&line.back()=='\r') line.pop_back();
        std::string trimmed=trim_ascii(line); if(trimmed.empty()||trimmed[0]=='#'||trimmed[0]==';') continue;
        if(trimmed.front()=='[') {
            if(trimmed.size()<3||trimmed.back()!=']'||trimmed.find('\\')!=trimmed.npos) throw std::runtime_error("Unsupported Qt INI section syntax");
            section=trimmed.substr(1,trimmed.size()-2);
            if(section=="General") section="";
            if(section.find_first_of("[]\r\n")!=section.npos) throw std::runtime_error("Invalid Qt INI section");
            continue;
        }
        auto eq=trimmed.find('='); if(eq==std::string::npos||eq==0) throw std::runtime_error("Unsupported Qt INI line");
        std::string key=trim_ascii(trimmed.substr(0,eq)),value=trim_ascii(trimmed.substr(eq+1));
        if(key.find('\\')!=key.npos) throw std::runtime_error("Unsupported Qt INI key escape");
        if(!section.empty()) key=section+"/"+key;
        std::string raw_value=value;
        if(value.size()>=2&&value.front()=='"'&&value.back()=='"') value=value.substr(1,value.size()-2);
        else if(value.find('"')!=value.npos) throw std::runtime_error("Unsupported quoted Qt INI value");
        if(value.rfind("@@",0)==0) value.erase(0,1);
        else if(opaque_qsettings_value(value)) { doc.values.erase(key);doc.opaque_values[key]=raw_value;continue; }
        doc.opaque_values.erase(key);
        doc.values[key]=ini_unescape(value);
    }
    return doc;
}
void set_ini(IniDocument &doc,const std::string &key,const std::string &value) {
    doc.opaque_values.erase(key); doc.values[key]=value;
}
std::string ini_escape(const std::string &s) {
    const bool quote=s.find_first_of(";=,")!=s.npos || s.find('"')!=s.npos || (!s.empty()&&(s.front()==' '||s.back()==' '));
    std::string out; if(quote) out+='"'; if(!s.empty()&&s.front()=='@') out+='@';
    for(char c:s) {
        if(c=='\\') out+="\\\\"; else if(c=='\n') out+="\\n"; else if(c=='\r') out+="\\r"; else if(c=='\t') out+="\\t";
        else if(c=='#') out+="\\#"; else if(c=='"'&&quote) out+="\\\""; else out+=c;
    }
    if(quote) out+='"';
    return out;
}
std::string ini_encode(const IniDocument &doc) {
    std::string out="ConfigVersion=1.3\n";
    auto write=[&](const std::string &full_key,const std::string &output_key,const std::string &value) { auto opaque=doc.opaque_values.find(full_key); out+=output_key+"="+(opaque==doc.opaque_values.end()?ini_escape(value):opaque->second)+"\n"; };
    for(const auto &p:doc.values) if(p.first!="ConfigVersion"&&p.first.find('/')==p.first.npos) write(p.first,p.first,p.second);
    for(const auto &p:doc.opaque_values) if(p.first!="ConfigVersion"&&p.first.find('/')==p.first.npos) write(p.first,p.first,"");
    std::string section;
    auto group_name=[](const std::string &group){return group;};
    for(const auto &p:doc.values) {
        auto slash=p.first.find('/'); if(slash==p.first.npos) continue;
        std::string group=p.first.substr(0,slash),key=p.first.substr(slash+1);
        if(group!=section) { section=group; out+="["+group_name(section)+"]\n"; }
        write(p.first,key,p.second);
    }
    for(const auto &p:doc.opaque_values) {
        auto slash=p.first.find('/'); if(slash==p.first.npos) continue;
        std::string group=p.first.substr(0,slash),key=p.first.substr(slash+1);
        if(group!=section) { section=group; out+="["+group_name(section)+"]\n"; }
        write(p.first,key,"");
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
Instance decode(const std::string &dir,const std::string &expected,bool importing=false) {
    auto cfg=read_ini(join(dir,"instance.cfg"));
    struct stat st{}; std::string pack_path=join(dir,"mmc-pack.json");
    if(lstat(pack_path.c_str(),&st)!=0||!S_ISREG(st.st_mode)||st.st_size<0||(size_t)st.st_size>kMetadataLimit) throw std::runtime_error("Invalid or oversized mmc-pack.json");
    std::ifstream in(pack_path); Json j; in>>j;
    if(j.value("formatVersion",0)!=1||!j.contains("components")||!j["components"].is_array()||j["components"].size()>128) throw std::runtime_error("Unsupported Prism component profile");
    std::string version; std::set<std::string> seen;
    for(const auto &c:j["components"]) {
        if(!c.is_object()||!c.contains("uid")||!c["uid"].is_string()||!c.contains("version")||!c["version"].is_string()) throw std::runtime_error("Malformed Prism component entry");
        std::string uid=c["uid"].get<std::string>(),component_version=c["version"].get<std::string>();
        if(!safe_id(uid)||!safe_id(component_version)||!seen.insert(uid).second) throw std::runtime_error("Unsafe or duplicate Prism component");
        bool disabled=false; if(c.contains("disabled")) { if(!c["disabled"].is_boolean()) throw std::runtime_error("Malformed Prism component disabled flag"); disabled=c["disabled"].get<bool>(); }
        if(uid=="net.minecraft"&&!disabled) version=component_version;
    }
    if(cfg.opaque_values.count("name")||cfg.opaque_values.count("MaxMemAlloc")) throw std::runtime_error("Prism name/heap setting has a non-scalar Qt type");
    Instance i{expected,cfg.values.count("name")?cfg.values["name"]:"Unnamed Instance",version,512};
    if(cfg.values.count("MaxMemAlloc")){try{
        unsigned long heap=std::stoul(cfg.values["MaxMemAlloc"]);
        if(importing) { if(heap>65536) throw std::runtime_error("Desktop heap exceeds import limit"); i.heap_mib=(unsigned)std::max<unsigned long>(kHeapMin,std::min<unsigned long>(heap,kHeapMax)); }
        else i.heap_mib=(unsigned)heap;
    }catch(const std::runtime_error &){throw;}catch(...){throw std::runtime_error("Invalid Prism MaxMemAlloc");}}
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
        write_atomic(join(dir,"instance.cfg"),ini_encode(IniDocument{cfg,{}}),true);
        write_atomic(join(dir,"mmc-pack.json"),pack(shared,version).dump(2)+"\n",true);
    } catch(...) { unlink(join(dir,"instance.cfg").c_str()); unlink(join(dir,"mmc-pack.json").c_str()); rmdir(join(dir,".minecraft").c_str()); rmdir(dir.c_str()); throw; }
    return i;
}
std::string archive_root(const std::string &root) { return join(root,"instance-archives"); }
void ensure_archive_dir(const std::string &root) {
    require_directory(root); const std::string path=archive_root(root);
    if(mkdir(path.c_str(),0755)!=0&&errno!=EEXIST) throw std::runtime_error("Cannot create archive directory");
    require_directory(path);
}
Json archive_marker(const std::string &path) {
    struct stat st{}; if(lstat(path.c_str(),&st)!=0||!S_ISREG(st.st_mode)||st.st_size<0||(size_t)st.st_size>4096) throw std::runtime_error("Invalid archive marker");
    std::ifstream in(path); Json j; in>>j; if(!j.is_object()||j.value("schema",0)!=1) throw std::runtime_error("Unsupported archive marker");
    if(!safe_id(j.at("archive_id").get<std::string>())||!safe_id(j.at("original_id").get<std::string>())) throw std::runtime_error("Unsafe archive marker ID");
    return j;
}
std::string available_id(const std::string &root,const std::string &name) {
    std::string base=slug(name),id=base;
    for(unsigned n=2;n<10000;++n) { struct stat st{}; if(lstat(dir_for(root,id).c_str(),&st)!=0&&errno==ENOENT) return id; id=base+"-"+std::to_string(n); }
    throw std::runtime_error("No free instance ID");
}
struct ImportEntry { std::string relative; bool directory; size_t size; };
void collect_import_tree(const std::string &source,const std::string &relative,const ImportOptions &opts,
                         std::vector<ImportEntry> &entries,size_t &files,size_t &bytes,unsigned depth=0) {
    if(depth>64) throw std::runtime_error("Import directory depth limit exceeded");
    const std::string path=relative.empty()?source:join(source,relative); DIR *d=opendir(path.c_str());
    if(!d) throw std::runtime_error("Cannot inspect import folder");
    try {
        while(auto *e=readdir(d)) {
            if(opts.should_cancel&&opts.should_cancel(files,bytes)) throw std::runtime_error("Import cancelled");
            std::string name=e->d_name; if(name=="."||name=="..") continue;
            if(name.empty()||name.find_first_of("/\\:\r\n\t")!=name.npos) throw std::runtime_error("Unsafe path in import folder");
            std::string rel=relative.empty()?name:join(relative,name),child=join(source,rel); struct stat st{};
            if(lstat(child.c_str(),&st)!=0) throw std::runtime_error("Cannot inspect imported file");
            if(S_ISLNK(st.st_mode)) throw std::runtime_error("Import contains a symbolic link");
            if(S_ISDIR(st.st_mode)) { if(entries.size()>=40000) throw std::runtime_error("Import entry limit exceeded"); entries.push_back({rel,true,0}); collect_import_tree(source,rel,opts,entries,files,bytes,depth+1); }
            else if(S_ISREG(st.st_mode)) {
                if(st.st_size<0) throw std::runtime_error("Invalid imported file size");
                if(++files>opts.max_files||(size_t)st.st_size>opts.max_bytes-bytes) throw std::runtime_error("Import size/file limit exceeded");
                bytes+=(size_t)st.st_size; if(entries.size()>=40000) throw std::runtime_error("Import entry limit exceeded"); entries.push_back({rel,false,(size_t)st.st_size});
            } else throw std::runtime_error("Import contains a special file");
        }
    } catch(...) { closedir(d); throw; }
    closedir(d);
}
void remove_tree(const std::string &path) {
    struct stat st{}; if(lstat(path.c_str(),&st)!=0) return;
    if(!S_ISDIR(st.st_mode)) { unlink(path.c_str()); return; }
    DIR *d=opendir(path.c_str()); if(d) { while(auto *e=readdir(d)) { std::string n=e->d_name; if(n!="."&&n!="..") remove_tree(join(path,n)); } closedir(d); }
    rmdir(path.c_str());
}
void copy_import_file(const std::string &source,const std::string &dest,size_t expected) {
    std::ifstream in(source,std::ios::binary); if(!in) throw std::runtime_error("Cannot open import source file");
    int fd=open(dest.c_str(),O_WRONLY|O_CREAT|O_EXCL,0644); if(fd<0) throw std::runtime_error("Cannot create imported file");
    char buffer[65536]; size_t copied=0; bool failed=false;
    while(in) {
        in.read(buffer,sizeof(buffer)); std::streamsize n=in.gcount(); if(n<=0) break;
        size_t off=0; while(off<(size_t)n) { ssize_t w=write(fd,buffer+off,(size_t)n-off); if(w<=0){failed=true;break;} off+=(size_t)w; }
        if(failed) break;
        copied+=(size_t)n;
    }
    int sync_result=failed?-1:fsync(fd); int close_result=close(fd);
    if(failed||sync_result!=0||(!in.eof()&&in.fail())||copied!=expected||close_result!=0) { unlink(dest.c_str()); throw std::runtime_error("Imported file changed or could not be copied"); }
}
bool path_within(const std::filesystem::path &path,const std::filesystem::path &base) {
    auto p=path.begin(),b=base.begin(); for(;b!=base.end();++b,++p) if(p==path.end()||*p!=*b) return false; return true;
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
    require_directory(root); require_directory(join(root,"instances"));
    std::string dir=dir_for(root,id); require_directory(dir);
    struct stat dot{},plain{}; bool has_dot=lstat(join(dir,".minecraft").c_str(),&dot)==0&&S_ISDIR(dot.st_mode);
    bool has_plain=lstat(join(dir,"minecraft").c_str(),&plain)==0&&S_ISDIR(plain.st_mode);
    if(!has_dot&&!has_plain) throw std::runtime_error("Instance game directory is missing");
    return decode(dir,id);
}
std::string archive_instance(const std::string &root,const std::string &id) {
    Instance i=load_instance(root,id); ensure_archive_dir(root);
    std::string base=slug(id),archive_id=base,archive_dir=join(archive_root(root),archive_id); bool found=false;
    for(unsigned n=1;n<=10000;++n) { if(n>1) { archive_id=base+"-"+std::to_string(n); archive_dir=join(archive_root(root),archive_id); } struct stat st{}; if(lstat(archive_dir.c_str(),&st)!=0&&errno==ENOENT) { found=true; break; } }
    if(!found||!safe_id(archive_id)) throw std::runtime_error("Cannot allocate archive ID");
    const std::string active=dir_for(root,id),marker=join(active,"archive.json");
    write_atomic(marker,Json{{"schema",1},{"archive_id",archive_id},{"original_id",id}}.dump(2)+"\n",true);
    if(rename(active.c_str(),archive_dir.c_str())!=0) { unlink(marker.c_str()); throw std::runtime_error("Cannot archive instance"); }
    (void)i; return archive_id;
}
std::vector<ArchivedInstance> list_archived_instances(const std::string &root) {
    std::vector<ArchivedInstance> out; const std::string dir=archive_root(root); struct stat st{};
    if(lstat(dir.c_str(),&st)!=0) { if(errno==ENOENT) return out; throw std::runtime_error("Cannot inspect archive directory"); }
    require_directory(dir); DIR *d=opendir(dir.c_str()); if(!d) throw std::runtime_error("Cannot scan archive directory");
    while(auto *e=readdir(d)) {
        std::string token=e->d_name; if(token=="."||token==".."||!safe_id(token)) continue;
        const std::string profile=join(dir,token); struct stat item{};
        if(lstat(profile.c_str(),&item)!=0||!S_ISDIR(item.st_mode)) continue;
        try {
            Json marker=archive_marker(join(profile,"archive.json"));
            if(marker.at("archive_id").get<std::string>()!=token) throw std::runtime_error("Archive token mismatch");
            auto i=decode(profile,marker.at("original_id").get<std::string>());
            out.push_back({token,i.id,i.name,i.version,i.heap_mib}); if(out.size()>=256) break;
        } catch(...) { /* ignore incomplete or malformed archive entries */ }
    }
    closedir(d); std::sort(out.begin(),out.end(),[](const auto&a,const auto&b){return a.name==b.name?a.archive_id<b.archive_id:a.name<b.name;}); return out;
}
Instance restore_instance(const std::string &root,const std::string &archive_id) {
    if(!safe_id(archive_id)) throw std::runtime_error("Unsafe archive ID");
    ensure_archive_dir(root); ensure_instances_dir(root);
    const std::string archive_dir=join(archive_root(root),archive_id);
    require_directory(archive_dir); Json marker=archive_marker(join(archive_dir,"archive.json"));
    if(marker.at("archive_id").get<std::string>()!=archive_id) throw std::runtime_error("Archive token mismatch");
    Instance archived=decode(archive_dir,marker.at("original_id").get<std::string>());
    std::string id=archived.id; const std::string preferred=dir_for(root,id); struct stat st{};
    if(lstat(preferred.c_str(),&st)==0||errno!=ENOENT) id=available_id(root,archived.name);
    const std::string destination=dir_for(root,id);
    if(lstat(destination.c_str(),&st)==0||errno!=ENOENT) throw std::runtime_error("Restore destination already exists");
    if(rename(archive_dir.c_str(),destination.c_str())!=0) throw std::runtime_error("Cannot restore archived instance");
    unlink(join(destination,"archive.json").c_str());
    archived.id=id; return archived;
}
Instance import_instance(const std::string &root,const std::string &shared,const std::string &source_directory,const ImportOptions &opts) {
    (void)shared;
    if(opts.max_files==0||opts.max_bytes==0) throw std::runtime_error("Import limits must be positive");
    require_directory(root); require_directory(source_directory); ensure_instances_dir(root);
    const auto source=std::filesystem::canonical(source_directory),runtime=std::filesystem::canonical(root);
    if(path_within(source,runtime)||path_within(runtime,source)) throw std::runtime_error("Import source overlaps the runtime destination tree");
    auto source_profile=decode(source.string(),"import-check",true);
    // Imported profiles may reference metadata that has not been cached yet. Keep their full
    // component pack and defer readiness checks to the planner once local metadata is available.
    (void)read_local_patches(source.string());
    std::vector<ImportEntry> entries; size_t files=0,bytes=0;
    collect_import_tree(source.string(),"",opts,entries,files,bytes);
    if(opts.should_cancel&&opts.should_cancel(0,0)) throw std::runtime_error("Import cancelled");
    ensure_instances_dir(root); const std::string id=available_id(root,source_profile.name);
    std::string staging=dir_for(root,id)+"-importing";
    for(unsigned n=2;;++n) {
        struct stat st{}; if(lstat(staging.c_str(),&st)!=0&&errno==ENOENT) break;
        staging=dir_for(root,id)+"-importing-"+std::to_string(n);
        if(n>10000) throw std::runtime_error("Cannot allocate import staging directory");
    }
    if(mkdir(staging.c_str(),0755)!=0) throw std::runtime_error("Cannot create import staging directory");
    size_t copied_files=0,copied_bytes=0;
    try {
        for(const auto &entry:entries) {
            if(opts.should_cancel&&opts.should_cancel(copied_files,copied_bytes)) throw std::runtime_error("Import cancelled");
            const std::string dest=join(staging,entry.relative);
            if(entry.directory) { if(mkdir(dest.c_str(),0755)!=0) throw std::runtime_error("Cannot create imported directory"); }
            else { copy_import_file(join(source.string(),entry.relative),dest,entry.size); ++copied_files; copied_bytes+=entry.size; }
        }
        // Revalidate the copied profile and local metadata before it becomes visible.
        source_profile=decode(staging,"import-check",true);
        auto imported_cfg=read_ini(join(staging,"instance.cfg"));
        set_ini(imported_cfg,"MaxMemAlloc",std::to_string(source_profile.heap_mib));
        set_ini(imported_cfg,"MinMemAlloc","64"); set_ini(imported_cfg,"OverrideMemory","true");
        std::string cfg_path=join(staging,"instance.cfg"),cfg_tmp=stage_atomic(cfg_path,ini_encode(imported_cfg));
        commit_staged(cfg_tmp,cfg_path);
        struct stat game{};
        if(lstat(join(staging,".minecraft").c_str(),&game)!=0&&lstat(join(staging,"minecraft").c_str(),&game)!=0) {
            if(mkdir(join(staging,".minecraft").c_str(),0755)!=0) throw std::runtime_error("Cannot create imported game directory");
        }
        std::string final=dir_for(root,id);
        struct stat occupied{}; if(lstat(final.c_str(),&occupied)==0||errno!=ENOENT) throw std::runtime_error("Import destination already exists");
        if(rename(staging.c_str(),final.c_str())!=0) throw std::runtime_error("Cannot finish instance import");
    } catch(...) { remove_tree(staging); throw; }
    source_profile.id=id; return source_profile;
}
void update_instance_version(const std::string &root,const std::string &shared,const std::string &id,const std::string &version) {
    if(!safe_id(version)) throw std::runtime_error("Invalid version ID");
    Instance current=load_instance(root,id); require_version(shared,root,version);
    const std::string dir=dir_for(root,id),path=join(dir,"mmc-pack.json");
    std::ifstream in(path); Json profile; in>>profile;
    if(!profile.is_object()||!profile.contains("components")||!profile["components"].is_array()) throw std::runtime_error("Invalid Prism component profile");
    for(const auto &component:profile["components"]) {
        std::string uid=component.value("uid",std::string());
        if(uid!="net.minecraft"&&uid!="org.lwjgl3") throw std::runtime_error("Cannot update version while preserving unsupported Prism component: "+uid);
    }
    const std::string cached=join(join(join(shared,"meta"),"net.minecraft"),version+".json");
    Json components=file_exists(cached)?prism_components_for_version(shared,version):Json::array({Json{{"uid","net.minecraft"},{"version",version},{"important",true}}});
    profile["formatVersion"]=1; profile["components"]=std::move(components);
    std::string temp=stage_atomic(path,profile.dump(2)+"\n"); commit_staged(temp,path);
    (void)current;
}
Instance create_instance(const std::string &root,const std::string &shared,const std::string &name,const std::string &version,unsigned heap) {
    validate_name(name); ensure_instances_dir(root); std::string base=slug(name),id=base;
    for(unsigned n=2;n<10000;++n) { struct stat st{}; if(lstat(dir_for(root,id).c_str(),&st)!=0&&errno==ENOENT) break; id=base+"-"+std::to_string(n); }
    return create_with_id(root,shared,name,version,heap,id);
}
void save_instance(const std::string &root,const Instance &i) {
    validate_instance(i); const std::string dir=dir_for(root,i.id); Instance old=load_instance(root,i.id); (void)old;
    auto cfg=read_ini(join(dir,"instance.cfg")); set_ini(cfg,"name",i.name); set_ini(cfg,"InstanceType","OneSix"); set_ini(cfg,"OverrideMemory","true"); set_ini(cfg,"MinMemAlloc","64"); set_ini(cfg,"MaxMemAlloc",std::to_string(i.heap_mib));
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
std::string instance_game_directory(const std::string &root,const std::string &id) {
    load_instance(root,id); const std::string dir=dir_for(root,id); struct stat plain{};
    if(lstat(join(dir,"minecraft").c_str(),&plain)==0&&S_ISDIR(plain.st_mode)) return join(dir,"minecraft");
    return join(dir,".minecraft");
}
Instance duplicate_instance(const std::string &root,const std::string &shared,const std::string &id,const std::string &new_name) {
    (void)shared; Instance src=load_instance(root,id); validate_name(new_name);
    const std::string source_dir=dir_for(root,id);
    auto cfg=read_ini(join(source_dir,"instance.cfg")); set_ini(cfg,"name",new_name);
    std::ifstream pack_in(join(source_dir,"mmc-pack.json"),std::ios::binary);
    std::string pack_data((std::istreambuf_iterator<char>(pack_in)),{});
    if(!pack_in.eof()&&!pack_in) throw std::runtime_error("Cannot read Prism component profile");
    Json parsed_pack=Json::parse(pack_data); if(!parsed_pack.is_object()) throw std::runtime_error("Invalid Prism component profile");
    auto patches=read_local_patches(source_dir);
    ensure_instances_dir(root); Instance dst{available_id(root,new_name),new_name,src.version,src.heap_mib};
    const std::string target_dir=dir_for(root,dst.id);
    if(mkdir(target_dir.c_str(),0755)!=0) throw std::runtime_error("Cannot create duplicate instance directory");
    if(mkdir(join(target_dir,".minecraft").c_str(),0755)!=0) { rmdir(target_dir.c_str()); throw std::runtime_error("Cannot create duplicate game directory"); }
    const std::string cfg_path=join(target_dir,"instance.cfg"), pack_path=join(target_dir,"mmc-pack.json");
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
