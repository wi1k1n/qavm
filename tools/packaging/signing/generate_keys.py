from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import argparse
from pathlib import Path

def main():
	parser = argparse.ArgumentParser(description="Generate RSA private and public keys.")
	parser.add_argument("--private", type=str, default="private.pem", help="Path to save the private key (default: private.pem)")
	parser.add_argument("--public", type=str, default="public.pem", help="Path to save the public key (default: public.pem)")
	parser.add_argument("--key_size", type=int, default=2048, help="Size of the RSA key to generate (default: 2048 bits)")
	parser.add_argument("--deployPath", type=str, default="verification_key.py", help="Path to save the verification key script (default: verification_key.py)")
	args = parser.parse_args()

	print("Generating RSA keys...")

	private_key = rsa.generate_private_key(public_exponent=65537, key_size=args.key_size)
	public_key = private_key.public_key()

	# Save keys to files
	privatePath: Path = Path(args.private)
	if not privatePath.parent.exists():
		privatePath.parent.mkdir(parents=True, exist_ok=True)
	publicPath: Path = Path(args.public)
	if not publicPath.parent.exists():
		publicPath.parent.mkdir(parents=True, exist_ok=True)

	with open(privatePath, "wb") as f:
		f.write(private_key.private_bytes(
			serialization.Encoding.PEM,
			serialization.PrivateFormat.PKCS8,
			serialization.NoEncryption()
		))

	public_key_bytes = public_key.public_bytes(
		serialization.Encoding.PEM,
		serialization.PublicFormat.SubjectPublicKeyInfo
	)
	with open(publicPath, "wb") as f:
		f.write(public_key_bytes)

	print(f"Private key saved to: {privatePath.resolve().absolute()}")
	print(f"Public key saved to: {publicPath.resolve().absolute()}")

	if args.deployPath:
		# Create a verification key script
		deployPath: Path = Path(args.deployPath)
		with open(deployPath, "w") as f:
			f.write(f"""\
# This script contains the public key for signature verification.
VERIFICATION_KEY = \"\"\"{public_key_bytes.decode('utf-8')}\"\"\"
""")
		print(f"Verification key saved to: {deployPath.resolve().absolute()}")

if __name__ == "__main__":
	main()