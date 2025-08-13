#!/bin/bash
# Encrypt environment file using OpenSSL and restrict permissions.

set -e
ENV_FILE=${1:-.env}
ENC_FILE=${2:-.env.enc}

if [ ! -f "$ENV_FILE" ]; then
  echo "Environment file $ENV_FILE not found"
  exit 1
fi

openssl aes-256-cbc -salt -in "$ENV_FILE" -out "$ENC_FILE"
chmod 600 "$ENC_FILE"
echo "Encrypted secrets saved to $ENC_FILE"
