#!/bin/bash


: <<'USAGE'
SHERWOOD_REPO='https://github.com/joepatmckenna/sherwood.git'
SHERWOOD_DIR='/root/sherwood'
if [[ -d "${SHERWOOD_DIR}" ]]; then
  git -C "${SHERWOOD_DIR}" pull
else
  git clone "${SHERWOOD_REPO}" "${SHERWOOD_DIR}"
fi

sudo systemctl restart sherwood

sudo rsync -a --delete /root/sherwood/ui/ /var/www/html/
sudo chown -R www-data:www-data /var/www/html
sudo chmod -R 755 /var/www/html

sudo systemctl status sherwood  
sudo systemctl status nginx  
USAGE

########################################

: <<'USAGE'
source /root/shwerwood/main.sh
main
integration_test
USAGE

########################################

: <<'LOGS'
sudo journalctl -u postgres
sudo journalctl -u sherwood
sudo journalctl -u nginx
LOGS

########################################

: <<'POSTGRES_CMDS'
sudo -u postgres psql -c "ALTER USER postgres WITH PASSWORD 'password';"
POSTGRES_CMDS

: <<'POSTGRES_MODS'
/etc/postgresql/16/main/pg_hba.conf
- local   all             postgres                                peer
+ local   all             postgres                                scram-sha-256
+ host    all             all            <LOCAL_IP_ADDR>/32       scram-sha-256
/etc/postgresql/16/main/postgresql.conf
+ listen_addresses = '*'`
+ port = 5432
sudo ufw allow 5432/tcp
POSTGRES_MODS

########################################

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

  sudo systemctl start postgresql
  sudo systemctl enable postgresql

  # sherwood
  if [[ -d "${SHERWOOD_DIR}" ]]; then
    git -C "${SHERWOOD_DIR}" pull
  else
    git clone "${SHERWOOD_REPO}" "${SHERWOOD_DIR}"
  fi

  python3 -m venv "${VENV_DIR}"
  "${PYTHON}" -m pip install "${SHERWOOD_DIR}" --no-cache-dir

  sudo cp "${SHERWOOD_DIR}"/service /etc/systemd/system/sherwood
  sudo systemctl daemon-reload
  sudo systemctl enable sherwood
  sudo systemctl start sherwood

  sudo rsync -a --delete /root/sherwood/ui/ /var/www/html/
  sudo chown -R www-data:www-data /var/www/html
  sudo chmod -R 755 /var/www/html

  sudo cp "${SHERWOOD_DIR}"/nginx.conf /etc/nginx/sites-available/sherwood
  [ -L /etc/nginx/sites-enabled/sherwood ] || sudo ln -s /etc/nginx/sites-available/sherwood /etc/nginx/sites-enabled/
  sudo nginx -t

  sudo systemctl restart nginx
  sudo systemctl restart sherwood

  sudo certbot --nginx -d writewell.tech -d www.writewell.tech --agree-tos --email=joepatmckenna@gmail.com --non-interactive 
  sudo certbot renew --dry-run

  # sudo ufw allow 80
  # sudo ufw allow 443
  # sudo ufw enable 
  
  sudo systemctl status postgresql
  sudo systemctl status sherwood  
  sudo systemctl status nginx  
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
  elif [ "${route}" = "/http/1" ]; then
    access_token_by_email["${email}"]=$(echo $res | jq -r .access_token)
  elif [ "${route}" = "/http/2" ]; then
    user_id_by_email["${email}"]=$(echo $res | jq -r .id)
  fi
}

integration_test() {
  email_1="integration-test-$((RANDOM * RANDOM))@web.com"
  email_2="integration-test-$((RANDOM * RANDOM))@web.com"

  PASSWORD='Abcd@1234'

  declare -A access_token_by_email
  declare -A user_id_by_email

  integration_test_case "${email_1}" POST /http/sign-up '{"email": "'"${email_1}"'", "password": "'"${PASSWORD}"'"}'
  integration_test_case "${email_1}" POST /http/sign-in '{"email": "'"${email_1}"'", "password": "'"${PASSWORD}"'"}'
  integration_test_case "${email_2}" POST /http/sign-up '{"email": "'"${email_2}"'", "password": "'"${PASSWORD}"'"}'
  integration_test_case "${email_2}" POST /http/sign-in '{"email": "'"${email_2}"'", "password": "'"${PASSWORD}"'"}'
  integration_test_case "${email_1}" GET /http/user
  integration_test_case "${email_2}" GET /http/user
  integration_test_case "${email_1}" POST /http/deposit '{"dollars": 1010}'
  integration_test_case "${email_1}" POST /http/withdraw '{"dollars": 10}'
  integration_test_case "${email_2}" POST /http/deposit '{"dollars": 1000}'
  integration_test_case "${email_1}" POST /http/buy '{"symbol": "TSLA", "dollars": 500}'
  integration_test_case "${email_1}" POST /http/sell '{"symbol": "TSLA", "dollars": 100}'
  integration_test_case "${email_2}" POST /http/invest '{"investee_portfolio_id": "'"${user_id_by_email[${email_1}]}"'", "dollars": 100}'
  integration_test_case "${email_2}" POST /http/divest '{"investee_portfolio_id": "'"${user_id_by_email[${email_1}]}"'", "dollars": 10}'

  for email in "${!access_token_by_email[@]}"; do
      echo
      echo email: "${email}"
      echo user id: "${user_id_by_email[$email]}"
      echo access token: "${access_token_by_email[$email]}"
      echo
  done

  sudo -u postgres psql -d db -c "DELETE FROM users WHERE email LIKE 'integration-test-%';"
}
