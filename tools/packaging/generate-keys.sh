#!/bin/bash

# Generate signing keys
python signing/generate_keys.py --private signing/keys/private.pem --public signing/keys/public.pem --deployPath ../../source/qavm/verification_key.py
if [ $? -ne 0 ]; then
    exit 1
fi

echo "Keys generated successfully."