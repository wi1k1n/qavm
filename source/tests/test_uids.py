import sys, unittest
from pathlib import Path

qavmPath = Path("./source").resolve()
if str(qavmPath) not in sys.path:
	sys.path.insert(0, str(qavmPath))

from qavm.manager_plugin import UID


class TestUID_Basic(unittest.TestCase):
	def test_plugin_id_validity(self):
		valid_ids = [
			"plugin", "plugin.id", "com.example.plugin", "a.b.c_d", "a1.b2.c-3",
			"plugin_id", "plugin-id", "com.plugin-id_name.example"
		]
		invalid_ids = [
			"", ".", "..", "plugin..id", ".plugin", "plugin.", "plugin id", "plugin/id",
			"plugin*", "plugin?", "plugin.id*", "plugin.id?",
			# Unsupported characters
			"plugin id", "plugin/id", "plugin\\id", "plugin:id", "plugin|id",
			"plugin<id", "plugin>id", "plugin\"id", "plugin?id", "plugin*id"
		]
		for pid in valid_ids:
			self.assertTrue(UID.IsPluginIDValid(pid), f"Should be valid: {pid}")
		for pid in invalid_ids:
			self.assertFalse(UID.IsPluginIDValid(pid), f"Should be invalid: {pid}")

	def test_data_path_validity(self):
		valid_paths = [
			"path", "path/sub_path", "a/b-c/d_e", "123/abc_123/456", "tiles/c4d",
			"some-path/with_under-scores", "path/*", "path/?", "path/*/sub", "path/*_suffix",
			"path/*/*", "path/?/?", "path/*/sub/*", "path/*_suffix?", "path?question_mark", "path*asterisk"
		]
		invalid_paths = [
			"", "/", "//", "path//sub", "/start", "end/", "with space", "bad\\slash",
			# Unsupported characters
			"with space", "bad\\slash", "path:colon", "path|pipe",
			"path<less_than", "path>greater_than", "path\"quote",
		]
		for path in valid_paths:
			self.assertTrue(UID.IsDataPathValid(path), f"Should be valid: {path}")
		for path in invalid_paths:
			self.assertFalse(UID.IsDataPathValid(path), f"Should be invalid: {path}")

	def test_uid_validity(self):
		valid_uids = [
			"com.plugin-id#software.abc#tiles/c4d",
			"a_b.c-d#x_y-z#x1/y_2/z-3",
			"a#b#c",
			"com.plugin_name#software-name_123#view-cam1/render_result",
			"com.plugin-id#software.abc#path/*",
			"com.plugin-id#software.abc#path/?"
		]
		invalid_uids = [
			"", "#", "#a#b", "a#b", "a#b#c#d",  # wrong parts count
			"#b#c", "a##c", "a#b#",             # missing parts
			"a.b#c.d#invalid..path",            # bad datapath
			"bad/id#c.d#valid/path",            # bad plugin ID
			"a.b#bad/id#valid/path",            # bad software ID
			"com.plugin-id#software.abc*#path/t",  # invalid wildcard usage
			"com.plugin-id#software.abc?#path/?/*",   # invalid wildcard usage
			# Unsupported characters
			"com.plugin id#software.abc#path/with space",
			"com.plugin-id#software.abc#path\\with_backslash",
			"com.plugin-id#software:abc#path/with:colon",
			"com.plugin-id#software|abc#path/with|pipe",
			"com.plugin-id#software<abc#path/with<less_than",
			"com.plugin-id#software>abc#path/with>greater_than",
			"com.plugin-id#software\"abc#path/with\"quote",
			"com.plugin-id#software?abc#path/with?question_mark",
			"com.plugin-id#software*abc#path/with*asterisk"
		]
		for uid in valid_uids:
			self.assertTrue(UID.IsUIDValid(uid), f"Should be valid: {uid}")
		for uid in invalid_uids:
			self.assertFalse(UID.IsUIDValid(uid), f"Should be invalid: {uid}")

	def test_fetch_methods(self):
		cases = [
			("com.plugin-id#software_name.c4d#view/tiles-c4d", "com.plugin-id", "software_name.c4d", "view/tiles-c4d"),

			("bad id#software.c4d#view/tiles", None, "software.c4d", "view/tiles"),
			("com.plugin#bad/id#view/tiles", "com.plugin", None, "view/tiles"),
			("com.plugin#software.c4d#bad..path", "com.plugin", "software.c4d", None),
			("onlyonepart", "onlyonepart", "onlyonepart", "onlyonepart"),
			("", None, None, None),
			("a#b", "a", "b", "b"),
			("com.plugin-id#software.abc#path/*", "com.plugin-id", "software.abc", "path/*"),
			("com.plugin-id#software.abc#path/?", "com.plugin-id", "software.abc", "path/?"),
			# Unsupported characters
			("com.plugin id#software.abc#path/with space", None, "software.abc", None),  # space in plugin ID doesn't matter for the software ID
			("com.plugin-id#software.abc#path\\with_backslash", "com.plugin-id", "software.abc", None),
			("com.plugin-id#software:abc#path/with:colon", "com.plugin-id", None, None),
			("com.plugin-id#software|abc#path/with|pipe", "com.plugin-id", None, None),
			("com.plugin-id#software<abc#path/with<less_than", "com.plugin-id", None, None),
			("com.plugin-id#software>abc#path/with>greater_than", "com.plugin-id", None, None),
			("com.plugin-id#software\"abc#path/with\"quote", "com.plugin-id", None, None),
			("com.plugin-id#software?abc#path/with?question_mark", "com.plugin-id", None, "path/with?question_mark"),
			("com.plugin-id#software*abc#path/with*asterisk", "com.plugin-id", None, "path/with*asterisk")
		]

		for uid, expected_pid, expected_sid, expected_dpath in cases:
			self.assertEqual(UID.FetchPluginID(uid), expected_pid, f"Plugin ID mismatch for {uid}")
			self.assertEqual(UID.FetchSoftwareID(uid), expected_sid, f"Software ID mismatch for {uid}")
			self.assertEqual(UID.FetchDataPath(uid), expected_dpath, f"Data path mismatch for {uid}")

	def test_plugin_software_id_validity(self):
		valid = [
			"plugin.id#software-id",
			"a-b#b_1",
			"plugin_name#software123"
		]
		invalid = [
			"", "a#", "#b", "#", "plugin#bad/id", "plugin id#software.id"
		]
		for uid in valid:
			self.assertTrue(UID.IsPluginSoftwareIDValid(uid), f"Should be valid: {uid}")
		for uid in invalid:
			self.assertFalse(UID.IsPluginSoftwareIDValid(uid), f"Should be invalid: {uid}")

	def test_software_id_data_path_validity(self):
		valid = [
			"software.id#view/tiles", "a#b_c", "soft1#path/to-data",
			"engine_01#shader/graph-output"
		]
		invalid = [
			"", "#", "#b", "a#", "soft/id#view", "soft#bad..path"
		]
		for uid in valid:
			self.assertTrue(UID.IsSoftwareIDDataPathValid(uid), f"Should be valid: {uid}")
		for uid in invalid:
			self.assertFalse(UID.IsSoftwareIDDataPathValid(uid), f"Should be invalid: {uid}")

	def test_fetch_plugin_software_id(self):
		cases = [
			("com.plugin#software.abc#tiles/c4d", "com.plugin#software.abc"),
			("com.plugin#software.abc", "com.plugin#software.abc"),
			("com.plugin#bad/id#view", None),
			("invalid", None),
		]
		for uid, expected in cases:
			self.assertEqual(UID.FetchPluginSoftwareID(uid), expected)

	def test_fetch_software_id_data_path(self):
		cases = [
			("com.plugin#software.abc#tiles/c4d", "software.abc#tiles/c4d"),
			("software.abc#tiles/c4d", "software.abc#tiles/c4d"),
			("software.abc#bad..path", None),
			("onlyonepart", None),
		]
		for uid, expected in cases:
			self.assertEqual(UID.FetchSoftwareIDDataPath(uid), expected)

	def test_long_ids(self):
		long_plugin = "plug-in_name" + ".b" * 10
		long_software = "s1_name-" * 10
		long_path = "d" * 10 + "/e_" * 5 + "z-"
		uid = f"{long_plugin}#{long_software}#{long_path}"
		self.assertTrue(UID.IsUIDValid(uid))
		self.assertEqual(UID.FetchPluginID(uid), long_plugin)
		self.assertEqual(UID.FetchSoftwareID(uid), long_software)
		self.assertEqual(UID.FetchDataPath(uid), long_path)
		
	def test_match_data_path(self):
		# Valid wildcard patterns and matching paths
		valid_cases = [
			("path/*", "path/subpath"),
			("path/*", "path/another_subpath"),
			("path/?", "path/a"),
			("path/?", "path/b"),
			("path/*/sub", "path/any/sub"),
			("path/*", "path/with-multiple/levels"),
			("path/*_suffix", "path/with_suffix"),
			("?path/*", "1path/with_underscores"),
			("path*/*", "path123/with-dashes"),
			("path/*", "path/with123numbers"),
		]

		for pattern, path in valid_cases:
			self.assertTrue(UID.MatchDataPath(pattern, path), f"Pattern '{pattern}' should match path '{path}'")

		# Invalid wildcard patterns and non-matching paths
		invalid_cases = [
			("path/*", "otherpath/subpath"),
			("path/?", "path/too_long"),
			("path/*/sub", "path/sub"),
			("path/test*_suffix", "path/without_suffix"),
			("path/*", "otherpath/with_underscores"),
			("path/*", "otherpath/with-dashes"),
			("path*/*", "path123"),
			("path/*", "otherpath/with123numbers"),
			# Unsupported characters
			("path/*", "path/with space"),
			("path/*", "path\\with_backslash"),
			("path/*", "path/with:colon"),
			("path/*", "path/with|pipe"),
			("path/*", "path/with<less_than"),
			("path/*", "path/with>greater_than"),
			("path/*", "path/with\"quote"),
			("path/*", "path/with?question_mark"),
			("path/*", "path/with*asterisk"),
		]

		for pattern, path in invalid_cases:
			self.assertFalse(UID.MatchDataPath(pattern, path), f"Pattern '{pattern}' should not match path '{path}'")



if __name__ == "__main__":
	unittest.main()