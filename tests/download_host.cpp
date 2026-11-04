#include "download.hpp"
#include <cstdlib>
#include <iostream>

int main(int argc, char** argv) {
    try {
        if (argc >= 4 && (std::string(argv[1]) == "fetch" || std::string(argv[1]) == "fetch-restart")) {
            const uint64_t limit = std::strtoull(argv[3], nullptr, 10);
            const bool http = argc > 4 && std::string(argv[4]) == "http-test";
            const std::string ca = argc > 5 ? argv[5] : "";
            std::string body = sc::fetch_text(argv[2], limit, {}, ca, http);
            if (std::string(argv[1]) == "fetch-restart") {
                sc::shutdown_download_transport();
                body = sc::fetch_text(argv[2], limit, {}, ca, false);
            }
            std::cout << body;
            sc::shutdown_download_transport();
            return 0;
        }
        if (argc >= 9 && std::string(argv[1]) == "download") {
            sc::DownloadRequest r;
            r.url = argv[2]; r.target = argv[3]; r.algorithm = argv[4]; r.expected_hash = argv[5];
            r.expected_size = std::strtoull(argv[6], nullptr, 10);
            r.max_bytes = std::strtoull(argv[7], nullptr, 10);
            r.retries = std::strtoul(argv[8], nullptr, 10);
            r.allow_http_for_tests = argc > 9 && std::string(argv[9]) == "http-test";
            r.repair_corrupt = argc > 10 && std::string(argv[10]) == "repair";
            const std::string cancel_mode = argc > 11 ? argv[11] : "";
            const uint64_t cancel_after = cancel_mode != "cancel-callback" ? std::strtoull(cancel_mode.c_str(), nullptr, 10) : 0;
            sc::DownloadCallbacks callbacks;
            callbacks.progress = [cancel_after](const sc::DownloadProgress& p) { return !cancel_after || p.bytes < cancel_after; };
            if (cancel_mode == "cancel-callback") callbacks.cancelled = [] { return true; };
            const auto result = sc::download_verified(r, callbacks);
            std::cout << "bytes=" << result.bytes << " sha256=" << result.sha256
                      << " attempts=" << result.attempts << " from_cache=" << result.from_cache << '\n';
            sc::shutdown_download_transport();
            return 0;
        }
        if (argc == 5 && std::string(argv[1]) == "verify") {
            const bool ok = sc::verify_file(argv[2], argv[3], argv[4]);
            std::cout << (ok ? "valid\n" : "invalid\n");
            return ok ? 0 : 3;
        }
        std::cerr << "usage: download_host fetch URL MAX [http-test] | download URL TARGET ALG HASH SIZE MAX RETRIES [http-test] [repair] [CANCEL_AFTER] | verify PATH ALG HASH\n";
        return 2;
    } catch (const std::exception& e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
