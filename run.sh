#!/bin/bash
# EOS Assistant — quick start script

set -e
cd "$(dirname "$0")"

if [ ! -f src/config.py ]; then
  echo "ERROR: src/config.py not found. Copy from example:"
  echo "  cp src/config.example.py src/config.py"
  echo "  Then fill in EOS_IP and ANTHROPIC_API_KEY"
  exit 1
fi

cd src
python3 web/app.py
