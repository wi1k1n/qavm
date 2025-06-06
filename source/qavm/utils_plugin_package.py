import os
from pathlib import Path
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

def CalculatePluginHash(pluginFolderPath: Path) -> bytes:
	"""Recursively hash a folder's contents (filenames + file contents)."""
	import os, hashlib
	sha256 = hashlib.sha256()
	for root, dirs, files in sorted(os.walk(pluginFolderPath)):
		for name in sorted(files):
			file_path = os.path.join(root, name)  # TODO: use pathlib instead
			rel_path = os.path.relpath(file_path, pluginFolderPath).replace(os.sep, '/')
			sha256.update(rel_path.encode('utf-8'))
			with open(file_path, 'rb') as f:
				while chunk := f.read(8192):
					sha256.update(chunk)
	return sha256.digest()

def VerifyPlugin(pluginFolderPath: Path, pluginSignaturePath: Path, publicKey: bytes) -> bool:
	"""Verify the signature of a plugin folder."""
	
	try:
		# Load public key
		public_key = serialization.load_pem_public_key(publicKey)

		# Calculate the plugin hash
		plugin_hash = CalculatePluginHash(pluginFolderPath)

		# Read the signature
		with open(pluginSignaturePath, 'rb') as f:
			signature = f.read()

		# Verify the signature
		public_key.verify(
			signature,
			plugin_hash,
			padding.PSS(
				mgf=padding.MGF1(hashes.SHA256()),
				salt_length=padding.PSS.MAX_LENGTH
			),
			hashes.SHA256()
		)
	except Exception as e:
		return False
		# print(f"❌ Plugin {pluginFolderPath} verification failed: {e}")
	return True