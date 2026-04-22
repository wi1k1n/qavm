import sys
import platform

# Inject default --defaultGlobalSearchPath if not explicitly provided by the user
if '--defaultGlobalSearchPath' not in sys.argv:
    if platform.system() == 'Windows':
        sys.argv.extend(['--defaultGlobalSearchPath', r'C:\Program Files'])
    elif platform.system() == 'Darwin':
        sys.argv.extend(['--defaultGlobalSearchPath', '/Applications'])
