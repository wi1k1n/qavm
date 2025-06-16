#!/bin/bash
# filepath: /Users/i_mazlov/dev/qavm/tools/packaging/package_cinema4d.sh

APP_NAME=qavm

# Create build.txt during packaging phase
python create-build-info.py $APP_NAME
if [ $? -ne 0 ]; then
    exit 1
fi

# Prepare builtin plugins for further packaging
python gather-builtin-plugins.py --pluginsFolder ../../../qavm-plugins/plugins --destination build/qavm/builtin_plugins

# Sign the builtin plugins
python sign-builtin-plugins.py --pluginsFolder build/qavm/builtin_plugins --key signing/keys/private.pem --calculatePluginHashPythonScript ../../source/qavm/utils_plugin_package.py --calculatePluginHashFunction CalculatePluginHash

# Use PyInstaller to build the application
# Comment: pyinstaller --name "qavm" "../../source/qavm.py" # use this to create default PyInstaller config
pyinstaller ./$APP_NAME.spec --distpath dist