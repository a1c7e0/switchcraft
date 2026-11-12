"""Reject a Java artifact that cannot supply the locked launcher profile."""
import copy
import importlib.util
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("java25_inputs",ROOT/"scripts/prepare-java25-runtime.py")
inputs=importlib.util.module_from_spec(spec)
spec.loader.exec_module(inputs)

class RuntimeProfileTests(unittest.TestCase):
    def setUp(self):
        self.data={"java_instrument":True,"cross_built_genuine_vm":True,"link_exit_status":0,
            "jvm_features":["jni-check","jvmti","serialgc","services","zero"],
            "runtime_image_modules":["java.base","java.instrument"]}

    def test_instrument_profile_requires_real_vm_and_agent_features(self):
        inputs.verify_profile(self.data,{"build_profile":"instrument"})
        for key,value in [("java_instrument",False),("cross_built_genuine_vm",False),
                          ("link_exit_status",1),("jvm_features",["zero"]),
                          ("runtime_image_modules",["java.base"])]:
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                changed=copy.deepcopy(self.data);changed[key]=value
                inputs.verify_profile(changed,{"build_profile":"instrument"})

    def test_game_profile_rejects_base_sdk_and_mismatched_module_image(self):
        modules=["java.base","java.instrument","java.management","java.desktop"]
        locked={"build_profile":"minecraft","runtime_image_modules":modules}
        with self.assertRaises(RuntimeError): inputs.verify_profile(self.data,locked)
        self.data.update(minecraft_profile=True,runtime_image_modules=modules)
        inputs.verify_profile(self.data,locked)
        for inventory in [modules[:-1],modules+["java.naming"]]:
            with self.subTest(inventory=inventory), self.assertRaises(RuntimeError):
                inputs.verify_profile(dict(self.data,runtime_image_modules=inventory),locked)
        for bad_lock in [{"build_profile":"minecraft"},{"build_profile":"unknown"}]:
            with self.assertRaises(RuntimeError): inputs.verify_profile(self.data,bad_lock)
