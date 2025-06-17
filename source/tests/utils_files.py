import sys, platform, shutil, tempfile, os
from pathlib import Path

qavmPath = Path("./source").resolve()
if str(qavmPath) not in sys.path:
	sys.path.insert(0, str(qavmPath))
import qavm.qavmapi.utils as utils

def PlatformWindows():
	return platform.system() == 'Windows'

def PlatformMacOS():
	return platform.system() == 'Darwin'

def run_tests():
	testFilesPath = Path(tempfile.gettempdir()) / "fs-objects"
	print(f"Using test files path: {testFilesPath}")

	testFilesPath.mkdir(exist_ok=True)

	# === Ground truth paths ===
	p_file = testFilesPath / "test_file.txt"
	p_dir = testFilesPath / "test_dir"
	p_symlink_file = testFilesPath / "file_symlink"
	p_symlink_dir = testFilesPath / "dir_symlink"
	p_hardlink = testFilesPath / "file_hardlink"
	p_alias = testFilesPath / "file_alias"

	p_file.write_text("Hello world!")
	p_dir.mkdir(exist_ok=True)

	if p_symlink_file.exists(): p_symlink_file.unlink()
	p_symlink_file.symlink_to(p_file)

	if p_symlink_dir.exists(): p_symlink_dir.unlink()
	p_symlink_dir.symlink_to(p_dir, target_is_directory=True)

	if p_hardlink.exists(): p_hardlink.unlink()
	os.link(p_file, p_hardlink)

	if PlatformWindows():
		p_shortcut = testFilesPath / "test_shortcut.lnk"
		p_junction = testFilesPath / "junction_dir"

		if p_shortcut.exists(): p_shortcut.unlink()
		utils.CreateShortcut(p_file, p_shortcut, exist_overwrite=True)

		if p_junction.exists(): shutil.rmtree(p_junction, ignore_errors=True)
		utils.CreateJunction(p_dir, p_junction, exist_overwrite=True)

	if PlatformMacOS():
		utils.CreateAlias(p_file, p_alias, exist_overwrite=True)

	# === Type Detection ===
	assert utils.IsPathFile(p_file)
	assert utils.IsPathDir(p_dir)
	assert utils.IsPathSymlinkF(p_symlink_file)
	assert utils.IsPathSymlinkD(p_symlink_dir)
	assert utils.IsPathHardlink(p_hardlink)

	if PlatformWindows():
		assert utils.IsPathShortcut(p_shortcut)
		assert utils.IsPathJunction(p_junction)

	if PlatformMacOS():
		assert utils.IsPathAlias(p_alias)

	print("✅ Type detection passed.")

	# === Target Retrieval ===
	assert utils.GetSymlinkFTarget(p_symlink_file).resolve() == p_file.resolve()
	assert utils.GetSymlinkDTarget(p_symlink_dir).resolve() == p_dir.resolve()

	if PlatformWindows():
		assert utils.GetShortcutTarget(p_shortcut).resolve() == p_file.resolve()
		assert utils.GetJunctionTarget(p_junction).resolve() == p_dir.resolve()

	if PlatformMacOS():
		assert utils.GetAliasTarget(p_alias).resolve() == p_file.resolve()

	print("✅ Target resolution passed.")

	# === Test creation & deletion ===
	pcreate_dir = testFilesPath / "z_mydir"
	pcreate_symlink_file = testFilesPath / "z_symlink_file"
	pcreate_symlink_dir = testFilesPath / "z_symlink_dir"
	pcreate_hardlink = testFilesPath / "z_hardlink"
	pcreate_alias = testFilesPath / "z_alias"
	pcreate_shortcut = testFilesPath / "z_shortcut.lnk"
	pcreate_junction = testFilesPath / "z_junction"

	utils.CreateDir(pcreate_dir, exist_ok=True)
	assert pcreate_dir.exists()

	utils.CreateSymlinkF(p_file, pcreate_symlink_file, exist_overwrite=True)
	assert utils.IsPathSymlinkF(pcreate_symlink_file)

	utils.CreateSymlinkD(p_dir, pcreate_symlink_dir, exist_overwrite=True)
	assert utils.IsPathSymlinkD(pcreate_symlink_dir)

	utils.CreateHardlink(p_file, pcreate_hardlink, exist_overwrite=True)
	assert utils.IsPathHardlink(pcreate_hardlink)

	if PlatformWindows():
		utils.CreateShortcut(p_file, pcreate_shortcut, exist_overwrite=True)
		assert utils.IsPathShortcut(pcreate_shortcut)

		utils.CreateJunction(p_dir, pcreate_junction, exist_overwrite=True)
		assert utils.IsPathJunction(pcreate_junction)

	if PlatformMacOS():
		utils.CreateAlias(p_file, pcreate_alias, exist_overwrite=True)
		assert utils.IsPathAlias(pcreate_alias)

	print("✅ Creation functions passed.")

	# === Test deletion ===
	to_delete = [pcreate_dir, pcreate_symlink_file, pcreate_symlink_dir, pcreate_hardlink]
	if PlatformWindows():
		to_delete += [pcreate_shortcut, pcreate_junction]
	if PlatformMacOS():
		to_delete += [pcreate_alias]

	for p in to_delete:
		utils.DeletePath(p)
		assert not p.exists(), f"DeletePath failed for {p}"

	print("✅ Deletion passed.")

	print("\n🎉 All cross-platform tests passed successfully.")


if __name__ == "__main__":
	run_tests()
