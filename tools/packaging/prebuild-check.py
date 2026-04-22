import sys, os, ast

VERSION_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'source', 'qavm', 'qavm_version.py')

def _read_variable(filepath, name):
	with open(filepath, 'r') as f:
		tree = ast.parse(f.read())
	for node in ast.iter_child_nodes(tree):
		if isinstance(node, ast.Assign):
			for target in node.targets:
				if isinstance(target, ast.Name) and target.id == name:
					return ast.literal_eval(node.value)
	return None

QAVM_VERSION = _read_variable(VERSION_FILE, 'QAVM_VERSION')
QAVM_VARIANT = _read_variable(VERSION_FILE, 'QAVM_VARIANT')

def main():
	if not QAVM_VERSION:
		print('Failed to read QAVM version info from source code. Please check the file: ' + VERSION_FILE)
		sys.exit(1)
	
	variantStr: str = QAVM_VARIANT or '<stable>'
	print(f'QAVM_VERSION is set to: {QAVM_VERSION} (variant: {variantStr})')
	answer = input('Do you want to continue? [y/N]: ').strip().lower()
	if answer != 'y':
		print('Aborted.')
		sys.exit(1)

if __name__ == '__main__':
	main()
