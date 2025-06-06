import argparse, hashlib, os
from pathlib import Path
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

def sign_bytes(data: bytes, private_key):
    """Sign a byte string using the provided private key."""
    return private_key.sign(
        data,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )

def write_signature(file_path: Path, signature: bytes):
    """Write the signature to a file with the same name and a .sig extension."""
    sig_path = file_path.with_suffix(file_path.suffix + ".sig")
    with open(sig_path, "wb") as f:
        f.write(signature)

# def sign_file(file_path: Path, private_key):
#     data = file_path.read_bytes()
#     signature = sign_bytes(data, private_key)
#     write_signature(file_path, signature)
#     print(f"Signed: {file_path} -> {file_path.with_suffix(file_path.suffix + '.sig')}")

def sign_folder(folder_path: Path, private_key, calculate_plugin_hash_func):
    """Sign the hash of a folder using the private key."""
    folder_hash = calculate_plugin_hash_func(folder_path)
    signature = sign_bytes(folder_hash, private_key)
    write_signature(folder_path, signature)
    print(f"Signed folder: {folder_path} -> {folder_path.with_suffix('.sig')}")

def main():
    parser = argparse.ArgumentParser(description="Sign all files in a plugin folder using a private key.")
    parser.add_argument("plugin_folder", type=str, help="Path to the plugin folder")
    parser.add_argument("--key", type=str, default="signing/keys/private.pem", help="Path to the private key file (default: signing/keys/private.pem)")
    parser.add_argument("--calculatePluginHashPythonScript", type=str, help="Path to the python script that calculates the plugin hash")
    parser.add_argument("--calculatePluginHashFunction", type=str, default="CalculatePluginHash", help="Name of the function that calculates the plugin hash (default: CalculatePluginHash)")
    args = parser.parse_args()

    print("Signing plugin folder:", args.plugin_folder)

    # get the function to calculate the plugin hash
    calculate_plugin_hash_func = None
    if args.calculatePluginHashPythonScript:
        import importlib.util
        script_path = Path(args.calculatePluginHashPythonScript)
        spec = importlib.util.spec_from_file_location("calcPluginHashScript", script_path)
        calcPluginHashScript = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(calcPluginHashScript)
        calculate_plugin_hash_func = getattr(calcPluginHashScript, args.calculatePluginHashFunction)
    
    if not callable(calculate_plugin_hash_func):
        print(f"Error: {args.calculatePluginHashFunction} is not a callable function in the provided script.")
        return

    plugin_folder = Path(args.plugin_folder)
    if not plugin_folder.exists() or not plugin_folder.is_dir():
        print(f"Error: {plugin_folder} is not a valid directory.")
        return

    # Load private key
    with open(args.key, "rb") as f:
        private_key = serialization.load_pem_private_key(f.read(), password=None)

    sign_folder(plugin_folder, private_key, calculate_plugin_hash_func)
    print(f"✅ Plugin folder signed successfully: {plugin_folder}")

if __name__ == "__main__":
    main()