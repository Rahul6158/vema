#!/bin/bash
# Run this in a PythonAnywhere Bash console (user: vemahomeappliances)

set -e
USERNAME="vemahomeappliances"
PROJECT="$HOME/vema"
REPO="https://github.com/bunny7200d-bit/vema.git"

cd "$HOME"
if [ -d vema ]; then
  cd vema
  git pull origin main || true
else
  git clone "$REPO"
  cd vema
fi

python3.10 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

if [ ! -f .env ]; then
  cp .env.example .env
fi

python create_demo.py

echo "Setup complete. Configure Web tab:"
echo "  Virtualenv: /home/${USERNAME}/vema/venv"
echo "  Static: /static/ -> /home/${USERNAME}/vema/app/static"
echo "  Site: https://${USERNAME}.pythonanywhere.com"
