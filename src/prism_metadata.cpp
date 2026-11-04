// SPDX-License-Identifier: GPL-3.0-only AND Apache-2.0
// Portable metadata subset derived from Prism Launcher; see vendor/prism/PROVENANCE.md.
#include "prism_metadata.hpp"
#include <algorithm>
#include <cctype>
#include <cstdint>
#include <map>
#include <set>
#include <stdexcept>

namespace sc {
namespace {
Json read_file(const std::string &path) { return read_json(path); }
std::string req_string(const Json &j, const char *key) {
    if (!j.contains(key) || !j[key].is_string()) throw std::runtime_error(std::string("Prism metadata missing string ")+key);
    return j[key].get<std::string>();
}
void validate_uid(const std::string &uid) {
    if (!safe_id(uid) || uid.find('/')!=uid.npos) throw std::runtime_error("Unsafe Prism component UID");
}
std::string maven_key(const Json &lib) {
    std::string name=req_string(lib,"name");
    auto a=name.find(':'), b=a==name.npos?a:name.find(':',a+1);
    if (b==name.npos) throw std::runtime_error("Invalid Prism Maven coordinate: "+name);
    auto c=name.find(':',b+1);
    return name.substr(0,b)+(c==name.npos?"":name.substr(c));
}
void merge_libraries(Json &into, const Json &add) {
    if (!add.is_array()) throw std::runtime_error("Prism libraries must be an array");
    for (const auto &lib:add) {
        auto key=maven_key(lib); bool replaced=false;
        for (auto &old:into) if (maven_key(old)==key) { old=lib; replaced=true; break; }
        if (!replaced) into.push_back(lib);
    }
}
std::int64_t iso_epoch(const std::string &s) {
    auto digit=[&](size_t i)->int { if(i>=s.size()||s[i]<'0'||s[i]>'9') throw std::runtime_error("Invalid Prism releaseTime"); return s[i]-'0'; };
    auto number=[&](size_t i,size_t n)->int { int v=0; for(size_t k=0;k<n;k++) v=v*10+digit(i+k); return v; };
    if(s.size()!=20&&s.size()!=25) throw std::runtime_error("Invalid Prism releaseTime length/timezone");
    if(s[4]!='-'||s[7]!='-'||s[10]!='T'||s[13]!=':'||s[16]!=':') throw std::runtime_error("Invalid Prism releaseTime syntax");
    int year=number(0,4), month=number(5,2), day=number(8,2), hour=number(11,2), minute=number(14,2), second=number(17,2);
    bool leap=(year%4==0&&(year%100!=0||year%400==0));
    static const int days_in_month[]={31,28,31,30,31,30,31,31,30,31,30,31};
    if(year<1||month<1||month>12||day<1||day>days_in_month[month-1]+(month==2&&leap)||hour>23||minute>59||second>59)
        throw std::runtime_error("Invalid Prism releaseTime fields");
    int offset=0;
    if(s.size()==20) { if(s[19]!='Z') throw std::runtime_error("Invalid Prism releaseTime timezone"); }
    else {
        if((s[19]!='+'&&s[19]!='-')||s[22]!=':') throw std::runtime_error("Invalid Prism releaseTime timezone");
        int oh=number(20,2),om=number(23,2); if(oh>23||om>59) throw std::runtime_error("Invalid Prism releaseTime timezone fields");
        offset=(oh*60+om)*60*(s[19]=='+'?1:-1);
    }
    // Proleptic Gregorian days since 1970-01-01 (Howard Hinnant civil calendar).
    int y=year-(month<=2); int era=(y>=0?y:y-399)/400; unsigned yoe=static_cast<unsigned>(y-era*400);
    unsigned mp=static_cast<unsigned>(month+(month>2?-3:9)); unsigned doy=(153*mp+2)/5+static_cast<unsigned>(day)-1;
    unsigned doe=yoe*365+yoe/4-yoe/100+doy;
    std::int64_t days=static_cast<std::int64_t>(era)*146097+doe-719468;
    return days*86400+hour*3600+minute*60+second-offset;
}
std::string maven_path(const std::string &name) {
    std::vector<std::string> parts; size_t at=0;
    while(true){auto end=name.find(':',at);parts.push_back(name.substr(at,end==name.npos?end:end-at));if(end==name.npos)break;at=end+1;}
    if(parts.size()<3||parts.size()>5||parts[0].empty()||parts[1].empty()||parts[2].empty()) throw std::runtime_error("Invalid Prism Maven coordinate: "+name);
    std::string group=parts[0]; std::replace(group.begin(),group.end(),'.','/');
    std::string file=parts[1]+"-"+parts[2]; if(parts.size()>=4&&!parts[3].empty()) file+="-"+parts[3];
    return group+"/"+parts[1]+"/"+parts[2]+"/"+file+".jar";
}
Json cache_file(const std::string &root,const std::string &uid,const std::string &version) {
    validate_uid(uid);
    if (!safe_id(version)) throw std::runtime_error("Unsafe Prism component version");
    return read_file(root+"/meta/"+uid+"/"+version+".json");
}
void verify_requirements(const Json &components) {
    std::map<std::string,std::string> selected;
    for(const auto &c:components) if(!c.value("disabled",false)) selected[req_string(c,"uid")]=req_string(c,"version");
    std::map<std::string,std::vector<std::string>> edges;
    for(const auto &c:components) {
        if(c.value("disabled",false)) continue;
        Json metadata=c.at("_metadata");
        for(const char *kind:{"requires","conflicts"}) if(metadata.contains(kind)) {
            if(!metadata[kind].is_array()) throw std::runtime_error(std::string("Prism ")+kind+" must be array");
            for(const auto &r:metadata[kind]) {
                auto uid=req_string(r,"uid"); validate_uid(uid);
                auto it=selected.find(uid);
                if(std::string(kind)=="requires") {
                    if(it==selected.end()) throw std::runtime_error("Prism component missing required component: "+uid);
                    if(r.contains("equals") && !r["equals"].is_string()) throw std::runtime_error("Prism requirement equals must be a string");
                    for(const char *constraint:{"lessThan","greaterThan","before","after"}) if(r.contains(constraint)) throw std::runtime_error(std::string("Unsupported Prism requirement constraint: ")+constraint);
                    if(r.contains("equals") && !r["equals"].get<std::string>().empty() && it->second!=r["equals"].get<std::string>())
                        throw std::runtime_error("Prism required component version mismatch: "+uid);
                    edges[req_string(c,"uid")].push_back(uid);
                    // Suggestions are advisory, as in ComponentUpdateTask::finalizeComponents.
                } else if(it!=selected.end()) throw std::runtime_error("Prism component conflict: "+uid);
            }
        }
    }
    std::map<std::string,int> state;
    auto visit=[&](auto &&self,const std::string &uid)->void {
        if(state[uid]==1) throw std::runtime_error("Prism component dependency cycle: "+uid);
        if(state[uid]==2) return;
        state[uid]=1; for(const auto &dep:edges[uid]) self(self,dep); state[uid]=2;
    };
    for(const auto &entry:selected) visit(visit,entry.first);
}
}

std::vector<PrismVersion> load_prism_versions(const std::string &sharedroot,const std::string &uid) {
    validate_uid(uid);
    Json index=read_file(sharedroot+"/meta/"+uid+"/index.json");
    if(index.value("formatVersion",1)!=1) throw std::runtime_error("Unsupported Prism metadata formatVersion");
    if(!index.contains("versions")||!index["versions"].is_array()) throw std::runtime_error("Prism version index has no versions array");
    std::vector<PrismVersion> out;
    for(const auto &v:index["versions"]) {
        PrismVersion p; p.version=req_string(v,"version"); if(!safe_id(p.version)) throw std::runtime_error("Unsafe Prism version ID");
        p.type=v.value("type",std::string{}); p.release_time=req_string(v,"releaseTime"); p.recommended=v.value("recommended",false);
        out.push_back(std::move(p));
    }
    std::stable_sort(out.begin(),out.end(),[](const auto&a,const auto&b){return iso_epoch(a.release_time)>iso_epoch(b.release_time);});
    return out;
}

Json prism_components_for_version(const std::string &sharedroot,const std::string &version) {
    if(!safe_id(version)) throw std::runtime_error("Unsafe Prism Minecraft version");
    Json comps=Json::array(); std::map<std::string,std::string> selected;
    std::vector<std::string> queue={"net.minecraft"}; selected["net.minecraft"]=version;
    for(size_t i=0;i<queue.size();++i) {
        const std::string uid=queue[i], ver=selected.at(uid);
        Json meta=cache_file(sharedroot,uid,ver);
        if(req_string(meta,"uid")!=uid || req_string(meta,"version")!=ver) throw std::runtime_error("Prism cache component identity mismatch");
        Json c={{"uid",uid},{"version",ver}}; comps.push_back(c);
        if(meta.contains("requires")) {
            if(!meta["requires"].is_array()) throw std::runtime_error("Prism requires must be array");
            for(const auto &req:meta["requires"]) {
                std::string dep=req_string(req,"uid"); validate_uid(dep);
                if(dep!="net.minecraft"&&dep!="org.lwjgl3") throw std::runtime_error("Unsupported required Prism component UID: "+dep);
                std::string wanted;
                if(req.contains("equals")) { if(!req["equals"].is_string()) throw std::runtime_error("Prism equals must be string"); wanted=req["equals"].get<std::string>(); }
                if(wanted.empty()&&req.contains("suggests")) { if(!req["suggests"].is_string()) throw std::runtime_error("Prism suggests must be string"); wanted=req["suggests"].get<std::string>(); }
                if(wanted.empty()) throw std::runtime_error("Prism requirement has no pinned/suggested version: "+dep);
                auto found=selected.find(dep);
                if(found!=selected.end()&&found->second!=wanted) throw std::runtime_error("Conflicting Prism dependency versions: "+dep);
                if(found==selected.end()) { if(!safe_id(wanted)) throw std::runtime_error("Unsafe suggested Prism version"); selected[dep]=wanted; queue.push_back(dep); }
            }
        }
    }
    return comps;
}

Json resolve_prism_pack(const std::string &sharedroot,const std::string &,const std::string &instance_dir) {
    Json pack=read_file(instance_dir+"/mmc-pack.json");
    if(pack.value("formatVersion",0)!=1||!pack.contains("components")||!pack["components"].is_array())
        throw std::runtime_error("Unsupported Prism mmc-pack format");
    Json components=pack["components"];
    if(components.size()>128) throw std::runtime_error("Prism component count limit");
    std::set<std::string> seen;
    for(auto &c:components) {
        auto uid=req_string(c,"uid"); validate_uid(uid);
        if(!seen.insert(uid).second) throw std::runtime_error("Duplicate Prism component: "+uid);
        if(!c.contains("version")||!c["version"].is_string()) throw std::runtime_error("Prism component version absent (cached-only resolver cannot select latest)");
        auto version=c["version"].get<std::string>();
        if(!safe_id(version)) throw std::runtime_error("Unsafe Prism component version");
        if(c.value("disabled",false)) continue;
        if(uid!="net.minecraft"&&uid!="org.lwjgl3") throw std::runtime_error("Unsupported Prism component UID: "+uid);
        Json meta=cache_file(sharedroot,uid,version);
        // PackProfile resolves an existing per-component patch before metadata cache.
        std::string patch_path=instance_dir+"/patches/"+uid+".json";
        if(file_exists(patch_path)) meta=read_file(patch_path);
        if(meta.value("uid",uid)!=uid) throw std::runtime_error("Prism patch UID mismatch");
        if(meta.contains("jarMods")&&!meta["jarMods"].empty()) throw std::runtime_error("Unsupported Prism jarMods operation");
        if(meta.contains("mods")&&!meta["mods"].empty()) throw std::runtime_error("Unsupported Prism mods operation");
        for(const char *unsupported:{"+agents","agents","mavenFiles","-libraries","-minecraftArguments","+minecraftArguments","tweakers","-tweakers"})
            if(meta.contains(unsupported)&&!meta[unsupported].empty()) throw std::runtime_error(std::string("Unsupported Prism operation: ")+unsupported);
        c["_metadata"]=std::move(meta);
    }
    verify_requirements(components);
    auto base=std::find_if(components.begin(),components.end(),[](const Json&c){return !c.value("disabled",false)&&c.value("uid","")=="net.minecraft";});
    if(base==components.end()) throw std::runtime_error("Prism profile has no enabled net.minecraft component");
    Json result=(*base)["_metadata"];
    result["id"]=req_string(*base,"version"); result["_jar"]=result.value("jar",req_string(*base,"version"));
    Json libs=Json::array();
    for(const auto &c:components) if(!c.value("disabled",false)) {
        auto uid=req_string(c,"uid"); const auto&m=c["_metadata"];
        if(m.contains("mainClass")&&m["mainClass"].is_string()&&!m["mainClass"].get<std::string>().empty()) result["mainClass"]=m["mainClass"];
        if(m.contains("mainJar")) result["mainJar"]=m["mainJar"];
        if(uid=="net.minecraft") for(const char *field:{"assetIndex","assets","type","javaVersion","arguments","minecraftArguments","downloads"}) if(m.contains(field)) result[field]=m[field];
        if(m.contains("compatibleJavaMajors")) result["compatibleJavaMajors"]=m["compatibleJavaMajors"];
        if(m.contains("+traits")) {
            if(!m["+traits"].is_array()) throw std::runtime_error("Prism +traits must be array");
            Json &traits=result["traits"]; if(!traits.is_array()) traits=Json::array();
            for(const auto &trait:m["+traits"]) {
                if(!trait.is_string()) throw std::runtime_error("Prism trait must be string");
                if(std::find(traits.begin(),traits.end(),trait)==traits.end()) traits.push_back(trait);
                if(trait=="XR:Initial") { Json &unsupported=result["_prism_unsupported_traits"]; if(!unsupported.is_array()) unsupported=Json::array(); unsupported.push_back(trait); }
            }
        }
        if(m.contains("+jvmArgs")) {
            if(!m["+jvmArgs"].is_array()) throw std::runtime_error("Prism +jvmArgs must be array");
            if(!result.contains("arguments")||!result["arguments"].is_object()) result["arguments"]=Json::object();
            auto &args=result["arguments"]["jvm"]; if(!args.is_array()) args=Json::array();
            for(auto &a:m["+jvmArgs"]) args.push_back(a);
        }
        if(m.contains("libraries")) merge_libraries(libs,m["libraries"]);
    }
    result["libraries"]=std::move(libs);
    result["_prism_component_order"]=Json::array();
    for(const auto &c:components) if(!c.value("disabled",false)) result["_prism_component_order"].push_back(c["uid"]);
    if(result.contains("mainJar")&&result["mainJar"].is_object()) {
        result["_main_jar_library"]=result["mainJar"];
        std::string path;
        const auto &jar=result["mainJar"];
        if(jar.contains("downloads")&&jar["downloads"].contains("artifact")&&jar["downloads"]["artifact"].contains("path")) path=jar["downloads"]["artifact"]["path"].get<std::string>();
        else path=maven_path(req_string(jar,"name"));
        if(path.empty()||path.front()=='/'||path.find("..")!=path.npos||path.find('\\')!=path.npos) throw std::runtime_error("Unsafe Prism mainJar path");
        result["_main_jar_path"]="libraries/"+path;
    }
    if(result.contains("compatibleJavaMajors")&&result["compatibleJavaMajors"].is_array()&&!result["compatibleJavaMajors"].empty()) {
        if(!result["javaVersion"].is_object()) result["javaVersion"]=Json::object();
        result["javaVersion"]["majorVersion"]=result["compatibleJavaMajors"][0];
    }
    return result;
}
}
