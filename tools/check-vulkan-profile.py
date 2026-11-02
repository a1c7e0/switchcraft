#!/usr/bin/env python3
"""Evaluate a measured base profile without claiming Minecraft/hardware success."""
import argparse,json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
def evaluate(report,profile):
    missing=[]
    if report.get('target')!=profile['version']:missing.append('target-version')
    major,minor,patch=profile['minimum_vulkan_api'];required=(major<<22)|(minor<<12)|patch
    if report.get('api_version',0)<required:missing.append('Vulkan API 1.2')
    for name in profile['required_features']:
        if report.get('features',{}).get(name) is not True:missing.append('feature:'+name)
    for name in profile['required_device_extensions']:
        if name not in report.get('extensions',[]):missing.append('extension:'+name)
    return {'target':profile['version'],'base_profile_supported':not missing,'missing':missing,
        'minecraft_title_on_horizon':'NOT TESTED','java25_horizon_runtime':'NOT AVAILABLE','presentation':'separate test required'}
def main():
    p=argparse.ArgumentParser();p.add_argument('report');a=p.parse_args()
    result=evaluate(json.loads(pathlib.Path(a.report).read_text()),json.loads((ROOT/'profiles/26.4-snapshot-6.json').read_text()))
    print(json.dumps(result,indent=2));return 0 if result['base_profile_supported'] else 1
if __name__=='__main__':sys.exit(main())
