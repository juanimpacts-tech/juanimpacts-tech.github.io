#!/usr/bin/env bash
set -euo pipefail
ARCH=$(uname -m)
URL=""
if [ "$ARCH" = "x86_64" ] || [ "$ARCH" = "amd64" ]; then
  URL="https://openpolicyagent.org/downloads/latest/opa_linux_amd64_static"
elif [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
  URL="https://openpolicyagent.org/downloads/latest/opa_linux_arm64_static"
else
  echo "Unsupported arch: $ARCH"; exit 1
fi
curl -L -o opa "$URL"
chmod +x opa
sudo mv opa /usr/local/bin/opa
echo "OPA installed: $(opa version)"
