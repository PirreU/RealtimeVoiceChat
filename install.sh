#!/usr/bin/env sh
set -eu

cd "$(dirname "$0")"

printf '%s\n' "Select how to use Real-Time Voice Chat:" \
  "  S - Set up this computer as a server (installs the AI stack)" \
  "  C - Connect as a client (no AI stack is installed)"
printf 'Choose S or C: '
read -r install_role

case "$install_role" in
  [cC])
    exec python3 setup.py --client
    ;;
  [sS])
    ;;
  *)
    echo "Invalid choice. Run install.sh again and choose S or C." >&2
    exit 1
    ;;
esac

python3 -m venv venv
. venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if [ "$(uname -s)" = "Linux" ]; then
  python -m pip install deepspeed
else
  echo "DeepSpeed is not installed on macOS; Coqui will run without that optional acceleration."
fi

python setup.py --configure-server
printf '\nServer dependencies and secure LAN settings are ready.\n'
printf 'Activate the environment, change to code/, and run: python server.py\n'
