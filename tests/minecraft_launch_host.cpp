#include "switchcraft/minecraft_launch.h"
#include "json.hpp"
#include <iostream>
#include <string>

int main(int argc, char **argv) {
    if (argc != 5) return 2;
    const std::string op=argv[1], runtime=argv[2], shared=argv[3], id=argv[4];
    char error[512]{};
    if (op=="prepare") {
        int ok=sc_minecraft_launch_prepare(runtime.c_str(),shared.c_str(),id.c_str(),nullptr,nullptr,error,sizeof(error));
        std::cout<<nlohmann::json{{"ok",bool(ok)},{"error",error}}.dump()<<'\n';
        return 0;
    }
    if (op=="consume") {
        ScMinecraftLaunchRequest request{};
        int ok=sc_minecraft_launch_consume(runtime.c_str(),&request,error,sizeof(error));
        nlohmann::json result={{"ok",bool(ok)},{"error",error}};
        if(ok) {
            result["classpath"]=request.classpath;
            result["main_class"]=request.main_class;
            result["game_directory"]=request.game_directory;
            result["heap_mib"]=request.heap_mib;
            result["arguments"]=nlohmann::json::array();
            for(size_t i=0;i<request.argument_count;i++)result["arguments"].push_back(request.arguments[i]);
            result["options"]=nlohmann::json::array();
            for(size_t i=0;i<request.option_count;i++)result["options"].push_back(request.options[i]);
        }
        std::cout<<result.dump()<<'\n';
        return 0;
    }
    return 2;
}
