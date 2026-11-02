import importlib.util,json,pathlib,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('profile',ROOT/'tools/check-vulkan-profile.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class SnapshotProfileTests(unittest.TestCase):
    def setUp(self):self.profile=json.loads((ROOT/'profiles/26.4-snapshot-6.json').read_text())
    def test_matching_base_features_never_claim_game_title(self):
        report={'target':'26.4-snapshot-6','api_version':(1<<22)|(2<<12),'features':dict.fromkeys(self.profile['required_features'],True),'extensions':self.profile['required_device_extensions']}
        result=module.evaluate(report,self.profile)
        self.assertTrue(result['base_profile_supported']);self.assertEqual(result['minecraft_title_on_horizon'],'NOT TESTED')
    def test_nonconformance_is_not_silently_hidden(self):
        result=module.evaluate({'target':'26.4-snapshot-6','api_version':(1<<22),'features':{},'extensions':[]},self.profile)
        self.assertFalse(result['base_profile_supported']);self.assertIn('feature:timelineSemaphore',result['missing']);self.assertIn('extension:VK_KHR_swapchain',result['missing'])
    def test_wrong_snapshot_is_rejected(self):
        result=module.evaluate({'target':'26.4-snapshot-4'},self.profile);self.assertIn('target-version',result['missing'])
