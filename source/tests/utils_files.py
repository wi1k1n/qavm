import sys
from pathlib import Path

qavmPath = Path("./source").resolve()
if str(qavmPath) not in sys.path:
	sys.path.insert(0, str(qavmPath))
import qavm.qavmapi.utils as utils

def run_tests():
	testFilesPath = Path('D:\\temp\\fs-objects')

	# === Ground truth paths created by batch script ===
	p_file = testFilesPath / "test_file.txt"
	p_dir = testFilesPath / "test_dir"
	p_shortcut = testFilesPath / "test_shortcut.lnk"
	p_symlink_file = testFilesPath / "file_symlink"
	p_symlink_dir = testFilesPath / "dir_symlink"
	p_junction = testFilesPath / "junction_dir"
	p_hardlink = testFilesPath / "file_hardlink"

	# === Check type detection ===
	assert utils.IsPathFile(p_file), "test_file.txt should be detected as regular file"
	assert utils.IsPathDir(p_dir), "test_dir should be detected as directory"
	assert utils.IsPathShortcut(p_shortcut), "test_shortcut.lnk should be detected as shortcut"
	assert utils.IsPathSymlinkF(p_symlink_file), "file_symlink should be a symlink to file"
	assert utils.IsPathSymlinkD(p_symlink_dir), "dir_symlink should be a symlink to dir"
	assert utils.IsPathJunction(p_junction), "junction_dir should be a junction"
	assert utils.IsPathHardlink(p_hardlink), "file_hardlink should be a hardlink"

	print("✅ Type detection passed.")

	# === Check target retrieval ===
	assert utils.GetShortcutTarget(p_shortcut).resolve() == p_file.resolve(), "Shortcut target mismatch"
	assert utils.GetSymlinkFTarget(p_symlink_file).resolve() == p_file.resolve(), "Symlink file target mismatch"
	assert utils.GetSymlinkDTarget(p_symlink_dir).resolve() == p_dir.resolve(), "Symlink dir target mismatch"
	assert utils.GetJunctionTarget(p_junction).resolve() == p_dir.resolve(), "Junction target mismatch"

	print("✅ Target resolution passed.")

	# === Test creating and deleting everything again ===
	pcreate_dir = testFilesPath / "z_mydir"
	pcreate_shortcut = testFilesPath / "z_shortcut.lnk"
	pcreate_symlink_file = testFilesPath / "z_symlink_file"
	pcreate_symlink_dir = testFilesPath / "z_symlink_dir"
	pcreate_junction = testFilesPath / "z_junction_dir"
	pcreate_hardlink = testFilesPath / "z_hardlink"

	utils.CreateDir(pcreate_dir, exist_ok=True)
	assert pcreate_dir.exists(), "CreateDir failed"

	utils.CreateShortcut(p_file, pcreate_shortcut, exist_overwrite=True)
	assert utils.IsPathShortcut(pcreate_shortcut), "CreateShortcut failed"

	utils.CreateSymlinkF(p_file, pcreate_symlink_file, exist_overwrite=True)
	assert utils.IsPathSymlinkF(pcreate_symlink_file), "CreateSymlinkF failed"

	utils.CreateSymlinkD(p_dir, pcreate_symlink_dir, exist_overwrite=True)
	assert utils.IsPathSymlinkD(pcreate_symlink_dir), "CreateSymlinkD failed"

	utils.CreateJunction(p_dir, pcreate_junction, exist_overwrite=True)
	assert utils.IsPathJunction(pcreate_junction), "CreateJunction failed"

	utils.CreateHardlink(p_file, pcreate_hardlink, exist_overwrite=True)
	assert utils.IsPathHardlink(pcreate_hardlink), "CreateHardlink failed"

	print("✅ Creation functions passed.")

	# === Test deletion ===
	for p in [pcreate_dir, pcreate_shortcut, pcreate_symlink_file, pcreate_symlink_dir, pcreate_junction, pcreate_hardlink]:
		utils.DeletePath(p)
		assert not p.exists(), f"DeletePath failed for {p}"

	print("✅ Deletion passed.")

	print("\n🎉 All tests passed successfully.")


if __name__ == "__main__":
	run_tests()