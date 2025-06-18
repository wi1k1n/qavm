import sys, platform, shutil, tempfile, os
from pathlib import Path

qavmPath = Path("./source").resolve()
if str(qavmPath) not in sys.path:
	sys.path.insert(0, str(qavmPath))
import qavm.qavmapi.utils as qutils

def run_tests():
	testFilesPath = Path(tempfile.gettempdir()) / "fs-objects"
	print(f"Using test files path: {testFilesPath}")

	testFilesPath.mkdir(exist_ok=True)

	# === Ground truth paths ===
	p_file = testFilesPath / "test_file.txt"
	p_dir = testFilesPath / "test_dir"
	p_symlink_file = testFilesPath / "file_symlink"
	p_symlink_dir = testFilesPath / "dir_symlink"
	p_alias = testFilesPath / "file_alias"

	p_file.write_text("Hello world!")
	p_dir.mkdir(exist_ok=True)

	if p_symlink_file.exists(): p_symlink_file.unlink()
	p_symlink_file.symlink_to(p_file)

	if p_symlink_dir.exists(): p_symlink_dir.unlink()
	p_symlink_dir.symlink_to(p_dir, target_is_directory=True)

	if qutils.PlatformWindows():
		p_shortcut = testFilesPath / "test_shortcut.lnk"
		p_junction = testFilesPath / "junction_dir"

		if p_shortcut.exists(): p_shortcut.unlink()
		qutils.CreateShortcut(p_file, p_shortcut, exist_overwrite=True)

		if p_junction.exists(): shutil.rmtree(p_junction, ignore_errors=True)
		qutils.CreateJunction(p_dir, p_junction, exist_overwrite=True)

	if qutils.PlatformMacOS():
		qutils.CreateAlias(p_file, p_alias, exist_overwrite=True)

	# === Type Detection ===
	assert qutils.IsPathFile(p_file)
	assert qutils.IsPathDir(p_dir)
	assert qutils.IsPathSymlinkF(p_symlink_file)
	assert qutils.IsPathSymlinkD(p_symlink_dir)

	if qutils.PlatformWindows():
		assert qutils.IsPathShortcut(p_shortcut)
		assert qutils.IsPathJunction(p_junction)

	if qutils.PlatformMacOS():
		assert qutils.IsPathAlias(p_alias)

	print("✅ Type detection passed.")

	# === Target Retrieval ===
	assert qutils.GetSymlinkFTarget(p_symlink_file).resolve() == p_file.resolve()
	assert qutils.GetSymlinkDTarget(p_symlink_dir).resolve() == p_dir.resolve()

	if qutils.PlatformWindows():
		assert qutils.GetShortcutTarget(p_shortcut).resolve() == p_file.resolve()
		assert qutils.GetJunctionTarget(p_junction).resolve() == p_dir.resolve()

	if qutils.PlatformMacOS():
		assert qutils.GetAliasTarget(p_alias).resolve() == p_file.resolve()

	print("✅ Target resolution passed.")

	# === Test creation & deletion ===
	pcreate_dir = testFilesPath / "z_mydir"
	pcreate_symlink_file = testFilesPath / "z_symlink_file"
	pcreate_symlink_dir = testFilesPath / "z_symlink_dir"
	pcreate_alias = testFilesPath / "z_alias"
	pcreate_shortcut = testFilesPath / "z_shortcut.lnk"
	pcreate_junction = testFilesPath / "z_junction"

	qutils.CreateDir(pcreate_dir, exist_ok=True)
	assert pcreate_dir.exists()

	qutils.CreateSymlinkF(p_file, pcreate_symlink_file, exist_overwrite=True)
	assert qutils.IsPathSymlinkF(pcreate_symlink_file)

	qutils.CreateSymlinkD(p_dir, pcreate_symlink_dir, exist_overwrite=True)
	assert qutils.IsPathSymlinkD(pcreate_symlink_dir)

	if qutils.PlatformWindows():
		qutils.CreateShortcut(p_file, pcreate_shortcut, exist_overwrite=True)
		assert qutils.IsPathShortcut(pcreate_shortcut)

		qutils.CreateJunction(p_dir, pcreate_junction, exist_overwrite=True)
		assert qutils.IsPathJunction(pcreate_junction)

	if qutils.PlatformMacOS():
		qutils.CreateAlias(p_file, pcreate_alias, exist_overwrite=True)
		assert qutils.IsPathAlias(pcreate_alias)

	print("✅ Creation functions passed.")

	# === Test deletion ===
	to_delete = [pcreate_dir, pcreate_symlink_file, pcreate_symlink_dir]
	if qutils.PlatformWindows():
		to_delete += [pcreate_shortcut, pcreate_junction]
	if qutils.PlatformMacOS():
		to_delete += [pcreate_alias]

	for p in to_delete:
		qutils.DeletePath(p)
		assert not p.exists(), f"DeletePath failed for {p}"

	print("✅ Deletion passed.")

		# === Test Copy ===
	copy_targets = []

	def test_copy(src: Path, label: str, is_type_fn, suffix: str = "_copy"):
		dst = testFilesPath / f"{src.name}{suffix}"
		copy_targets.append(dst)

		# Initial copy
		qutils.CopyPath(src, dst, exist_overwrite=True)
		assert dst.exists(), f"{label} copy not created"
		assert is_type_fn(dst), f"{label} copy is not of expected type"

		# Overwrite protection test
		try:
			qutils.CopyPath(src, dst, exist_overwrite=False)
			assert False, f"{label} copy overwrite protection failed"
		except FileExistsError:
			pass

	test_copy(p_file, "File", qutils.IsPathFile)
	test_copy(p_dir, "Directory", qutils.IsPathDir)
	test_copy(p_symlink_file, "SymlinkF", qutils.IsPathSymlinkF)
	test_copy(p_symlink_dir, "SymlinkD", qutils.IsPathSymlinkD)

	if qutils.PlatformWindows():
		test_copy(p_shortcut, "Shortcut", qutils.IsPathShortcut, '_shortcut.lnk')
		test_copy(p_junction, "Junction", qutils.IsPathJunction)

	if qutils.PlatformMacOS():
		test_copy(p_alias, "Alias", qutils.IsPathAlias)

	print("✅ CopyPath function passed.")

	# === Clean up copy targets ===
	for p in copy_targets:
		qutils.DeletePath(p)
		assert not p.exists(), f"Cleanup failed for {p}"

	print("✅ CopyPath cleanup passed.")

	print("\n🎉 All cross-platform tests passed successfully.")


if __name__ == "__main__":
	run_tests()
