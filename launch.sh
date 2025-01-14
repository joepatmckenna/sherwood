#!/bin/bash

git add .
git commit -m 'fix password validator websocket'
git push

# copy .env to /root/.env on host
# scp -i ~/.ssh/id_rsa_sherwood .env "root@${HOST_IP}:/root/sherwood/.env"

# run on host
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