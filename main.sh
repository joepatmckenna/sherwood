#!/bin/bash

########################################

: <<'USAGE'
source /root/shwerwood/main.sh
launch
integration_test
USAGE

########################################

: <<'LOGS'
sudo journalctl -u sherwood
LOGS

########################################

: <<'POSTGRES_MODS'
/etc/postgresql/16/main/pg_hba.conf
- local   all             postgres                                peer
+ local   all             postgres                                scram-sha-256
+ host    all             all            <LOCAL_IP_ADDR>/32       scram-sha-256
/etc/postgresql/16/main/postgresql.conf
+ listen_addresses = '*'`
+ port = 5432
POSTGRES_MODS

########################################

SHERWOOD_REPO='https://github.com/joepatmckenna/sherwood.git'
SHERWOOD_DIR='/root/sherwood'
VENV_DIR='/root/venv'
PYTHON="${VENV_DIR}"/bin/python 

launch() {
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

########################################

integration_test_case() {
  email="${1}"
  method="${2}"
  route="${3}"
  data="${4:-}"

  DOMAIN='https://writewell.tech'

  tmp_res=$(mktemp)

  cmd=(curl -s -o "${tmp_res}" -w "%{http_code}" -X "${method}" "${DOMAIN}${route}")
  if [ -n "${data}" ]; then
    cmd+=(-d "${data}" -H "Content-Type: application/json")
  fi
  access_token="${access_token_by_email[${email}]}"
  if [ -n "${access_token}" ]; then
    cmd+=(-H "X-Sherwood-Authorization: Bearer ${access_token}")
  fi

  status_code=$("${cmd[@]}")

  res=$(cat "$tmp_res")
  rm "$tmp_res"

  echo "${status_code}" "${email}" "${method}" "${route}"
  if [ "${status_code}" -ne 200 ]; then
    echo "${cmd[@]}"
    echo "$res"
  elif [ "${route}" = "/sign-in" ]; then
    access_token_by_email["${email}"]=$(echo $res | jq -r .access_token)
  elif [ "${route}" = "/user" ]; then
    user_id_by_email["${email}"]=$(echo $res | jq -r .id)
  fi

}

integration_test() {
  email_1="integration-test-$((RANDOM * RANDOM))@web.com"
  email_2="integration-test-$((RANDOM * RANDOM))@web.com"

  PASSWORD='Abcd@1234'

  declare -A access_token_by_email
  declare -A user_id_by_email

  integration_test_case "${email_1}" GET /
  integration_test_case "${email_1}" POST /sign-up '{"email": "'"${email_1}"'", "password": "'"${PASSWORD}"'"}'
  integration_test_case "${email_1}" POST /sign-in '{"email": "'"${email_1}"'", "password": "'"${PASSWORD}"'"}'
  integration_test_case "${email_2}" POST /sign-up '{"email": "'"${email_2}"'", "password": "'"${PASSWORD}"'"}'
  integration_test_case "${email_2}" POST /sign-in '{"email": "'"${email_2}"'", "password": "'"${PASSWORD}"'"}'
  integration_test_case "${email_1}" GET /user
  integration_test_case "${email_2}" GET /user
  integration_test_case "${email_1}" POST /deposit '{"dollars": 1010}'
  integration_test_case "${email_1}" POST /withdraw '{"dollars": 10}'
  integration_test_case "${email_2}" POST /deposit '{"dollars": 1000}'
  integration_test_case "${email_1}" POST /buy '{"symbol": "TSLA", "dollars": 500}'
  integration_test_case "${email_1}" POST /sell '{"symbol": "TSLA", "dollars": 100}'
  integration_test_case "${email_2}" POST /invest '{"investee_portfolio_id": "'"${user_id_by_email[${email_1}]}"'", "dollars": 100}'

  for email in "${!access_token_by_email[@]}"; do
      echo
      echo email: "${email}"
      echo user id: "${user_id_by_email[$email]}"
      echo access token: "${access_token_by_email[$email]}"
      echo
  done

#   sudo -i -u postgres psql <<EOF
# ALTER USER postgres WITH PASSWORD 'password';
# EOF

}



# sudo -i -u postgres psql -U postgres -d db -c "DELETE FROM users WHERE email LIKE 'integration-test-%';"

