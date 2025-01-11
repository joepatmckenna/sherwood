#!/bin/bash

git add . && git commit -m '.' && git push

HOST_IP='208.68.37.48'

scp -i ~/.ssh/id_rsa_sherwood .env "root@${HOST_IP}:/root/sherwood/.env"

ssh "root@${HOST_IP}" << 'EOF'
SHERWOOD_REPO='https://github.com/joepatmckenna/sherwood.git'
SHERWOOD_DIR='/root/sherwood'
if [[ -d "${SHERWOOD_DIR}" ]]; then
  git -C "${SHERWOOD_DIR}" pull
else
  git clone "${SHERWOOD_REPO}" "${SHERWOOD_DIR}"
fi
source /root/sherwood/main.sh
main
integration_test
EOF
