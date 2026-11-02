#include "metadata.hpp"
#include <algorithm>
#include <cctype>
#include <cstdio>
#include <dirent.h>
#include <fstream>
#include <map>
#include <set>
#include <sstream>
#include <stdexcept>
#include <sys/stat.h>

namespace sc {
bool file_exists(const std::string &path) {
    struct stat st{};return stat(path.c_str(),&st)==0&&S_ISREG(st.st_mode);
}
bool safe_id(const std::string &id) {
    return !id.empty()&&id.size()<=128&&id!="."&&id!=".."&&
        std::all_of(id.begin(),id.end(),[](unsigned char c){return std::isalnum(c)||c=='.'||c=='_'||c=='-';});
}
static bool relative_path(const std::string &s) {
    if(s.empty()||s.front()=='/'||s.find(':')!=s.npos||s.find('\\')!=s.npos)return false;
    std::istringstream in(s);std::string part;
    while(std::getline(in,part,'/'))if(part.empty()||part=="."||part=="..")return false;
    return std::all_of(s.begin(),s.end(),[](unsigned char c){return c>=32&&c!=127;});
}
Json read_json(const std::string &path) {
    std::ifstream in(path,std::ios::binary|std::ios::ate);
    if(!in)throw std::runtime_error("Cannot read JSON: "+path);
    auto size=in.tellg();if(size<0||size>4*1024*1024)throw std::runtime_error("JSON size limit: "+path);
    in.seekg(0);Json result;in>>result;
    if(!result.is_object())throw std::runtime_error("Expected JSON object: "+path);
    return result;
}
static void validate_config(const Config &c) {
    if(c.root.empty()||c.root.size()>512||c.root.find("..")!=c.root.npos||
        c.root.find_first_of("\r\n\t")!=c.root.npos)throw std::runtime_error("Invalid Minecraft root");
    if(!c.version.empty()&&!safe_id(c.version))throw std::runtime_error("Invalid version ID");
    if(c.heap_mib<64||c.heap_mib>1024)throw std::runtime_error("Heap must be 64..1024 MiB");
    if(c.runtime!="diagnostic"&&c.runtime!="minijvm"&&c.runtime!="openjdk8"&&c.runtime!="openjdk21"&&c.runtime!="openjdk25"&&c.runtime!="aot")throw std::runtime_error("Unknown runtime");
    if(c.graphics!="nvc0"&&c.graphics!="nvk"&&c.graphics!="zink")throw std::runtime_error("Unknown graphics backend");
}
Config load_config(const std::string &path) {
    Config c;if(!file_exists(path))return c;
    Json j=read_json(path);c.root=j.value("minecraft_root",c.root);c.version=j.value("version",c.version);
    c.runtime=j.value("runtime",c.runtime);c.graphics=j.value("graphics",c.graphics);c.heap_mib=j.value("heap_mib",c.heap_mib);
    validate_config(c);return c;
}
void save_config(const std::string &path,const Config &c) {
    validate_config(c);
    Json j={{"minecraft_root",c.root},{"version",c.version},{"runtime",c.runtime},{"graphics",c.graphics},{"heap_mib",c.heap_mib}};
    std::string tmp=path+".tmp";std::ofstream out(tmp,std::ios::trunc);
    if(!out)throw std::runtime_error("Cannot write config temporary file");
    out<<j.dump(2)<<'\n';out.close();
    if(!out||std::rename(tmp.c_str(),path.c_str())!=0){std::remove(tmp.c_str());throw std::runtime_error("Cannot commit configuration");}
}
std::vector<std::string> scan_versions(const std::string &root) {
    std::vector<std::string> result;DIR *dir=opendir((root+"/versions").c_str());
    if(!dir)return result;
    while(auto *entry=readdir(dir)){
        std::string id=entry->d_name;
        if(safe_id(id)&&file_exists(root+"/versions/"+id+"/"+id+".json"))result.push_back(id);
        if(result.size()>=512)break;
    }
    closedir(dir);std::sort(result.begin(),result.end());return result;
}
static std::string library_key(const Json &lib) {
    std::string name=lib.at("name").get<std::string>();
    auto first=name.find(':'),second=first==name.npos?name.npos:name.find(':',first+1);
    if(second==name.npos)throw std::runtime_error("Invalid Maven coordinate");
    auto third=name.find(':',second+1);
    return name.substr(0,second)+(third==name.npos?"":name.substr(third));
}
static Json resolve(const std::string &root,const std::string &id,std::set<std::string> &seen) {
    if(!safe_id(id))throw std::runtime_error("Unsafe version identifier");
    if(seen.size()>=16||!seen.insert(id).second)throw std::runtime_error("Version inheritance cycle/depth limit");
    Json child=read_json(root+"/versions/"+id+"/"+id+".json"),base=Json::object();
    if(child.contains("inheritsFrom"))base=resolve(root,child.at("inheritsFrom").get<std::string>(),seen);
    Json libs=base.value("libraries",Json::array());
    if(!libs.is_array())throw std::runtime_error("libraries must be an array");
    for(const auto &lib:child.value("libraries",Json::array())) {
        std::string key=library_key(lib);bool replaced=false;
        for(auto &old:libs)if(library_key(old)==key){old=lib;replaced=true;break;}
        if(!replaced)libs.push_back(lib);
    }
    Json args=base.value("arguments",Json::object());
    if(child.contains("arguments"))for(const char *kind:{"jvm","game","default-user-jvm"}) {
        if(!args.contains(kind))args[kind]=Json::array();
        for(const auto &a:child["arguments"].value(kind,Json::array()))args[kind].push_back(a);
    }
    std::string jar=child.value("jar",base.value("_jar",id));
    if(child.contains("downloads")&&child["downloads"].contains("client"))jar=id;
    for(auto it=child.begin();it!=child.end();++it)base[it.key()]=it.value();
    base["libraries"]=libs;base["arguments"]=args;base["_jar"]=jar;base["id"]=id;
    return base;
}
Json resolve_version(const std::string &root,const std::string &id) {std::set<std::string> seen;return resolve(root,id,seen);}
static bool allowed(const Json &j) {
    if(!j.contains("rules"))return true;
    if(!j["rules"].is_array())throw std::runtime_error("rules must be an array");
    bool result=false;
    for(const auto &rule:j["rules"]) {
        bool match=true;
        if(rule.contains("os")) {
            const auto &os=rule["os"];
            if(os.contains("name")&&os["name"]!="horizon")match=false;
            if(os.contains("arch")&&os["arch"]!="aarch64"&&os["arch"]!="arm64")match=false;
            if(os.contains("version"))match=false; // Horizon version regex is not implemented.
        }
        if(rule.contains("features"))for(auto it=rule["features"].begin();it!=rule["features"].end();++it) {
            // All optional launcher features (demo, quickplay, resolution) are off.
            if(!it.value().is_boolean()||it.value().get<bool>())match=false;
        }
        std::string action=rule.at("action").get<std::string>();
        if(action!="allow"&&action!="disallow")throw std::runtime_error("Unknown rule action");
        if(match)result=action=="allow";
    }
    return result;
}
static std::string maven_path(std::string name) {
    std::vector<std::string> parts;std::istringstream in(name);std::string part;
    while(std::getline(in,part,':'))parts.push_back(part);
    if(parts.size()<3||parts.size()>4)throw std::runtime_error("Unsupported Maven coordinate");
    std::replace(parts[0].begin(),parts[0].end(),'.','/');
    return parts[0]+"/"+parts[1]+"/"+parts[2]+"/"+parts[1]+"-"+parts[2]+(parts.size()==4?"-"+parts[3]:"")+".jar";
}
static std::vector<std::string> split_legacy(const std::string &text) {
    std::vector<std::string> out;std::string word;char quote=0;bool active=false;
    for(char c:text) {
        if(c=='\''||c=='"') {if(!quote){quote=c;active=true;}else if(quote==c)quote=0;else word+=c;}
        else if(std::isspace((unsigned char)c)&&!quote){if(active){out.push_back(word);word.clear();active=false;}}
        else {word+=c;active=true;}
    }
    if(quote)throw std::runtime_error("Unclosed quote in legacy arguments");
    if(active)out.push_back(word);
    return out;
}
static void append_arguments(const Json &args,std::vector<std::string> &out) {
    if(!args.is_array())throw std::runtime_error("arguments must be arrays");
    for(const auto &a:args) {
        if(a.is_string())out.push_back(a.get<std::string>());
        else if(allowed(a)){
            if(a.at("value").is_array())for(const auto &v:a["value"])out.push_back(v.get<std::string>());
            else out.push_back(a.at("value").get<std::string>());
        }
    }
}
Json make_plan(const Config &config,const std::string &runtime_root) {
    validate_config(config);Json version=resolve_version(config.root,config.version);
    Json plan={{"version",config.version},{"runtime",config.runtime},{"graphics",config.graphics},
        {"java_major",version.value("javaVersion",Json::object()).value("majorVersion",8)},
        {"hardware_status","NOT TESTED"},{"launchable",false},{"classpath",Json::array()},
        {"missing_files",Json::array()},{"native_substitutions",Json::array()},
        {"blockers",Json::array()},{"unresolved_placeholders",Json::array()},
        {"skipped_libraries",Json::array()}};
    plan["main_class"]=version.value("mainClass","");
    if(plan["main_class"]=="")plan["blockers"].push_back("Version has no mainClass");
    std::string instance=runtime_root+"/instances/test/"+config.version;
    plan["game_directory"]=instance;
    plan["native_directory"]=runtime_root+"/natives/"+config.graphics;
    std::string classpath;
    // A colon is part of libnx's device path. A Horizon JVM adapter must use
    // the matching semicolon path separator, as the miniJVM diagnostic does.
    plan["classpath_separator"]=";";
    auto add=[&](const std::string &path){plan["classpath"].push_back(path);if(!file_exists(path))plan["missing_files"].push_back(path);if(!classpath.empty())classpath+=';';classpath+=path;};
    for(const auto &lib:version["libraries"]) {
        std::string name=lib.at("name").get<std::string>();
        if(!allowed(lib)){plan["skipped_libraries"].push_back(name);continue;}
        if(lib.contains("natives")&&!lib["natives"].empty())plan["native_substitutions"].push_back(name);
        if(name.find(":natives-")!=name.npos){plan["native_substitutions"].push_back(name);continue;}
        std::string path;
        if(lib.contains("downloads")) {
            if(!lib["downloads"].contains("artifact"))continue;
            path=lib["downloads"]["artifact"].at("path").get<std::string>();
        } else path=maven_path(name);
        if(!relative_path(path))throw std::runtime_error("Unsafe library path");
        add(config.root+"/libraries/"+path);
    }
    std::string jar=version.at("_jar").get<std::string>();if(!safe_id(jar))throw std::runtime_error("Unsafe JAR ID");
    add(config.root+"/versions/"+jar+"/"+jar+".jar");
    if(config.version=="26.4-snapshot-6")add(runtime_root+"/launchers/switchcraft-launcher-bridge.jar");
    std::string assets=version.value("assets","");
    if(version.contains("assetIndex"))assets=version["assetIndex"].at("id").get<std::string>();
    if(!assets.empty()) {
        if(!safe_id(assets))throw std::runtime_error("Unsafe asset index ID");
        std::string path=config.root+"/assets/indexes/"+assets+".json";
        plan["asset_index"]=path;
        if(!file_exists(path))plan["missing_files"].push_back(path);
        else {Json index=read_json(path);plan["asset_objects_declared"]=index.value("objects",Json::object()).size();}
    }
    std::vector<std::string> jvm={"-Xms64M","-Xmx"+std::to_string(config.heap_mib)+"M"},game;
    append_arguments(version["arguments"].value("jvm",Json::array()),jvm);
    append_arguments(version["arguments"].value("game",Json::array()),game);
    std::vector<std::string> official_defaults;
    append_arguments(version["arguments"].value("default-user-jvm",Json::array()),official_defaults);
    plan["official_default_user_jvm_arguments"]=official_defaults;
    plan["official_defaults_applied"]=false;
    if(config.version=="26.4-snapshot-6"){
        game.push_back("--graphicsBackend");game.push_back("VULKAN");
        plan["target_profile"]="26.4-snapshot-6";
        jvm.push_back("-javaagent:"+runtime_root+"/launchers/switchcraft-launcher-bridge.jar");
        plan["required_runtime_modules"]={"java.base","java.instrument"};
    }
    if(version.contains("minecraftArguments"))game=split_legacy(version["minecraftArguments"].get<std::string>());
    if(std::find(jvm.begin(),jvm.end(),"-cp")==jvm.end()&&std::find(jvm.begin(),jvm.end(),"-classpath")==jvm.end()){
        jvm.push_back("-cp");jvm.push_back("${classpath}");
    }
    std::map<std::string,std::string> vars={{"version_name",config.version},{"version_type",version.value("type","custom")},
        {"assets_root",config.root+"/assets"},{"game_assets",config.root+"/assets/virtual/legacy"},{"assets_index_name",assets},
        {"game_directory",instance},{"natives_directory",plan["native_directory"].get<std::string>()},
        {"library_directory",config.root+"/libraries"},{"classpath",classpath},{"classpath_separator",";"},
        {"launcher_name","Switchcraft"},{"launcher_version","0.1.0"}};
    for(auto *list:{&jvm,&game})for(auto &argument:*list) {
        for(const auto &pair:vars) {
            std::string needle="${"+pair.first+"}";size_t pos=0;
            while((pos=argument.find(needle,pos))!=argument.npos){argument.replace(pos,needle.size(),pair.second);pos+=pair.second.size();}
        }
        size_t pos=0;while((pos=argument.find("${",pos))!=argument.npos){auto end=argument.find('}',pos);if(end==argument.npos)break;
            plan["unresolved_placeholders"].push_back(argument.substr(pos,end-pos+1));pos=end+1;}
    }
    plan["jvm_arguments"]=jvm;plan["game_arguments"]=game;
    plan["blockers"].push_back("No Minecraft-capable Horizon JVM or AOT backend integrated in launcher");
    if(config.runtime=="minijvm")plan["blockers"].push_back("miniJVM is a separate Java 8 diagnostic; Minecraft compatibility is unimplemented");
    plan["blockers"].push_back("LWJGL/SDL3/Vulkan/FFM/OpenAL native bindings not integrated");
    if(config.graphics!="nvk")plan["blockers"].push_back("Mainline supports Vulkan NVK only; legacy OpenGL is on branch legacy/1.12.2");
    if(plan["java_major"].get<int>()>8&&config.runtime=="minijvm")plan["blockers"].push_back("Java version mismatch: miniJVM 8 cannot execute this classfile version");
    if(!plan["missing_files"].empty())plan["blockers"].push_back("Installation files missing");
    if(!plan["native_substitutions"].empty())plan["blockers"].push_back("Desktop native dependencies need Horizon replacements");
    if(!plan["unresolved_placeholders"].empty())plan["blockers"].push_back("Launch placeholders unresolved; account authentication is not implemented");
    return plan;
}
std::vector<std::string> manifest_ids(const Json &manifest) {
    std::vector<std::string> ids;
    for(const auto &entry:manifest.at("versions")){std::string id=entry.at("id").get<std::string>();if(safe_id(id))ids.push_back(id);}
    return ids;
}
}
