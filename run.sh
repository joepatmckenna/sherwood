#!/bin/bash


SHERWOOD_REPO='https://github.com/joepatmckenna/sherwood.git'
SHERWOOD_DIR='/root/sherwood'
VENV_DIR='/root/venv'
PYTHON="${VENV_DIR}"/bin/python 

main() {
  sudo apt update && sudo apt upgrade -y
  sudo apt install -y \
    certbot \
    git \
    nginx \
    postgresql \
    python3 \
    python3-certbot-nginx \
    python3-pip \
    python3-venv

  # postgresql
  # change
  # local postgres peer
  # local postgres sha-..
  # in
  # /etc/postgresql/16/main/pg_hba.conf
  sudo systemctl start postgresql
  sudo systemctl enable postgresql
  sudo -i -u postgres psql <<EOF
ALTER USER postgres WITH PASSWORD 'password';
EOF

  # sherwood
  if [[ -d "${SHERWOOD_DIR}" ]]; then
    git -C "${SHERWOOD_DIR}" pull
  else
    git clone "${SHERWOOD_REPO}" "${SHERWOOD_DIR}"
  fi
  "${PYTHON}" -m pip install "${SHERWOOD_DIR}" --no-cache-dir
  sudo cp "${SHERWOOD_DIR}"/sherwood.service /etc/systemd/system/sherwood.service
  sudo systemctl daemon-reload
  sudo systemctl enable sherwood
  sudo systemctl start sherwood

  # nginx
  sudo cp "${SHERWOOD_DIR}"/sherwood.nginx /etc/nginx/sites-available/sherwood
  if [ -L /etc/nginx/sites-enabled/sherwood ] && [ "$(readlink /etc/nginx/sites-enabled/sherwood)" = "/etc/nginx/sites-available/sherwood" ]; then
    sudo rm /etc/nginx/sites-enabled/sherwood
  fi
  sudo ln -s /etc/nginx/sites-available/sherwood /etc/nginx/sites-enabled/
  `sudo nginx -t` || exit 1;

  sudo systemctl restart nginx  
  sudo systemctl restart sherwood

  sudo certbot --nginx -d writewell.tech -d www.writewell.tech
  sudo certbot renew --dry-run  
}

integration_test_case() {
  method="${1}"
  route="${2}"
  data="${3:-}"

  tmp_res=$(mktemp)

  cmd=(curl -s -o "${tmp_res}" -w "%{http_code}" -X "${method}" "${DOMAIN}${route}")
  if [ "${method}" = "POST" ] && [ -n "${data}" ]; then
    cmd+=(-d "${data}" -H "Content-Type: application/json")
  fi
  if [ -n "${ACCESS_TOKEN}" ]; then
    cmd+=(-H "X-Sherwood-Authorization: Bearer ${ACCESS_TOKEN}")
  fi

  status_code=$("${cmd[@]}")

  res=$(cat "$tmp_res")
  rm "$tmp_res"

  echo "${status_code}" "${method}" "${route}"
  if [ "${status_code}" -ne 200 ]; then
    echo "Response: $res"
  elif [ "${route}" = "/sign-in" ]; then
    ACCESS_TOKEN=$(echo $res | jq -r .access_token)
  fi

}

integration_test() {
  DOMAIN='https://writewell.tech'
  EMAIL=''
  PASSWORD='Abcd@1234'
  ACCESS_TOKEN=''

  EMAIL="integration-test-$((RANDOM * RANDOM * RANDOM * RANDOM))@web.com"
  integration_test_case GET /
  integration_test_case POST /sign-up "{\"email\": \"${EMAIL}\", \"password\": \"${PASSWORD}\"}"
  integration_test_case POST /sign-in "{\"email\": \"${EMAIL}\", \"password\": \"${PASSWORD}\"}"
  integration_test_case GET /user
  integration_test_case POST /deposit "{\"dollars\": 1001}"
  integration_test_case POST /withdraw "{\"dollars\": 1}"
  integration_test_case POST /buy "{\"symbol\": \"TSLA\", \"dollars\": 500}"
}

integration_test

# sudo journalctl -u sherwood



# # status_code=$("${cmd[@]}")
# # res=$(cat "$tmp_res")
# # rm "$tmp_res"

# # if [ "${status_code}" -ne 200 ]; then
# #   echo "${res}"
# # fi


#   echo "${status_code}" "${res}"


#   res=$(curl -s \
#     -w "%{http_code} https://writewell.tech\n" \
#     https://writewell.tech)
#   curl -s -o /dev/null \
#     -w "%{http_code} https://www.writewell.tech\n" \
#     https://www.writewell.tech
#   curl -s -o /dev/null \
#     -w "%{http_code} https://writewell.tech/sign-up" \
#     -X POST https://writewell.tech/sign-up \
#     -H "Content-Type: application/json" \
#     -d "{\"email\": \"${EMAIL}\", \"password\": \"${PASSWORD}\"}"

#   token=$(curl -X POST https://www.writewell.tech/sign-in \
#   -H "Content-Type: application/json" \
#   -d "{\"email\": \"${EMAIL}\", \"password\": \"${PASSWORD}\"}")

#   token_type=$(echo $token | jq -r .token_type)
#   access_token=$(echo $token | jq -r .access_token)

#   curl https://www.writewell.tech/user \
#   -H "Content-Type: application/json" \
#   -H "X-Sherwood-Authorization: ${token_type} ${access_token}" 

#   curl -X POST https://www.writewell.tech/deposit \
#   -H "Content-Type: application/json" \
#   -H "X-Sherwood-Authorization: ${token_type} ${access_token}" \
#   -d "{\"dollars\": "100"}"

