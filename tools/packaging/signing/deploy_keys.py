import argparse
from pathlib import Path


def deploy_keys(publicPath: Path, deployPath: Path) -> Path:
	"""Create a verification key script from a public key.

	Reads the public key from publicPath and writes a Python script to deployPath
	that exposes the public key as a VERIFICATION_KEY string constant.
	Returns the resolved deploy path.
	"""
	publicPath = Path(publicPath)
	deployPath = Path(deployPath)

	public_key_bytes = publicPath.read_bytes()

	if not deployPath.parent.exists():
		deployPath.parent.mkdir(parents=True, exist_ok=True)

	with open(deployPath, "w") as f:
		f.write(f"""\
# This script contains the public key for signature verification.
VERIFICATION_KEY = \"\"\"{public_key_bytes.decode('utf-8')}\"\"\"
""")

	return deployPath.resolve().absolute()


def main():
	parser = argparse.ArgumentParser(description="Deploy a public key as a verification key script.")
	parser.add_argument("--private", type=str, default="private.pem", help="Path to the private key (default: private.pem)")
	parser.add_argument("--public", type=str, default="public.pem", help="Path to the public key (default: public.pem)")
	parser.add_argument("--deployPath", type=str, default="verification_key.py", help="Path to save the verification key script (default: verification_key.py)")
	args = parser.parse_args()

	deployedPath = deploy_keys(Path(args.public), Path(args.deployPath))
	print(f"Verification key saved to: {deployedPath}")


if __name__ == "__main__":
	main()
