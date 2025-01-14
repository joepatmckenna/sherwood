#!/bin/bash

SHERWOOD_REPO='https://github.com/joepatmckenna/sherwood.git'
SHERWOOD_DIR='/root/sherwood'

source "${SHERWOOD_DIR}/.env"
# POSTGRESQL_DATABASE_PASSWORD=...

check_postgresql_service() {
  if systemctl is-active --quiet postgresql; then
    echo "PostgreSQL service is running."
    if pg_isready > /dev/null 2>&1; then
      echo "PostgreSQL is ready to accept connections."
      return 0
    else
      echo "PostgreSQL service is running but not ready to accept connections."
      return 1
    fi
  else
    echo "PostgreSQL service is NOT running."
    return 1
  fi
}

run_psql() {
  sudo -u postgres psql -tAc "${1}"
}

setup_postgresql() {
  sudo apt install -y postgresql certbot
  sudo systemctl start postgresql
  sudo systemctl enable postgresql

  check_postgresql_service()
  if [ $? -eq 1 ]; then
    return 1
  fi

  pg_conf='/etc/postgresql/16/main/postgresql.conf'
  pg_hba_conf='/etc/postgresql/16/main/pg_hba.conf'

  database=sherwood

  database_exists=$(run_psql "SELECT 1 FROM pg_database WHERE datname = '${database}';")
  [ "${database_exists}" == "1" ] || sudo_psql "CREATE DATABASE ${database};"

  user_exists=$(run_psql "SELECT 1 FROM pg_roles WHERE rolname = '${database}';")
  if [ "${user_exists}" != "1" ]; then
    sudo_psql "CREATE USER ${database} WITH PASSWORD '${POSTGRESQL_DATABASE_PASSWORD}';"
    sudo_psql "GRANT ALL PRIVILEGES ON DATABASE ${database} TO ${database};"
    sudo_psql "ALTER USER ${database} WITH NOSUPERUSER NOCREATEDB NOCREATEROLE;"
  fi

  sudo sed -i "/^listen_addresses =/d" "${pg_conf}"
  echo "listen_addresses = '*'" | sudo tee -a "${pg_conf}"

  rule="hostssl ${database} ${database} 0.0.0.0/0 scram-sha-256"
  if ! grep -Fxq "${rule}" "${pg_hba_conf}"; then
    echo "${rule}" | sudo tee -a "${pg_hba_conf}"
  fi

  sudo certbot \
    certonly \
    -d sql.joemckenna.xyz \
    --standalone \
    --agree-tos \
    --non-interactive \
    --email=joepatmckenna@gmail.com

  postgres_ssl_dir='/var/lib/postgresql/ssl'

  sudo mkdir -p "${postgres_ssl_dir}"
  sudo chown postgres:postgres "${postgres_ssl_dir}"
  sudo chmod 700 "${postgres_ssl_dir}"

  sudo cp \
    /etc/letsencrypt/live/sql.joemckenna.xyz/fullchain.pem \
    /etc/letsencrypt/live/sql.joemckenna.xyz/privkey.pem \
    "${postgres_ssl_dir}/"

  sudo chown postgres:postgres "${postgres_ssl_dir}/fullchain.pem" "${postgres_ssl_dir}/privkey.pem"
  sudo chmod 600 "${postgres_ssl_dir}/fullchain.pem" "${postgres_ssl_dir}/privkey.pem"

  sudo sed -i "/^ssl =/d" "${pg_conf}"
  sudo sed -i "/^ssl_cert_file =/d" "${pg_conf}"
  sudo sed -i "/^ssl_key_file =/d" "${pg_conf}"

  echo "ssl = on" | sudo tee -a "${pg_conf}"
  echo "ssl_cert_file = '/var/lib/postgresql/ssl/fullchain.pem'" | sudo tee -a "${pg_conf}"
  echo "ssl_key_file = '/var/lib/postgresql/ssl/privkey.pem'" | sudo tee -a "${pg_conf}"

  sudo systemctl restart postgresql

  # psql -h sql.joemckenna.xyz -U sherwood -d sherwood --set=sslmode=require -W
}


VENV_DIR='/root/venv'
PYTHON="${VENV_DIR}/bin/python"

setup_sherwood() {
  sudo apt install -y git python3 python3-pip python3-venv
  python3 -m venv "${VENV_DIR}"

  if [[ -d "${SHERWOOD_DIR}" ]]; then
    git -C "${SHERWOOD_DIR}" pull
  else
    git clone "${SHERWOOD_REPO}" "${SHERWOOD_DIR}"
  fi

  "${PYTHON}" -m pip install "${SHERWOOD_DIR}" --no-cache-dir

  sudo cp "${SHERWOOD_DIR}"/service /etc/systemd/system/sherwood

  sudo mkdir -p /var/www/html/sherwood
  sudo rsync -a --delete /root/sherwood/ui /var/www/html/sherwood

  sudo systemctl start sherwood
  sudo systemctl enable sherwood
}

setup_nginx() {
  sudo apt install -y nginx python3-certbot-nginx certbot

  local config="${SHERWOOD_DIR}"/nginx.conf
  local available="/etc/nginx/sites-available/sherwood"
  local enabled="/etc/nginx/sites-enabled/sherwood"

  if [ ! -f "${config}" ]; then
    echo "Error: ${config} does not exist."
    return 1
  fi

  sudo cp "${config}" "${available}"

  if [ -L "${enabled}" ]; then
    local target=$(readlink -f "${enabled}")
    if [ "${target}" != "${available}" ]; then
      sudo ln -sf "${available}" "${enabled}"
    fi
  elif [ -e "${enabled}" ]; then
    rm "${enabled}"
    sudo ln -s "${available}" "${enabled}"
  else
    sudo ln -s "${available}" "${enabled}"
  fi

  sudo certbot \
    certonly \
    -d joemckenna.xyz,www.joemckenna.xyz \
    --nginx \
    --agree-tos \
    --non-interactive \
    --email=joepatmckenna@gmail.com

  sudo chown -R www-data:www-data /var/www/html
  sudo chmod -R 755 /var/www/html

  sudo nginx -s reload
  # sudo systemctl restart nginx

  sudo nginx -t
  return $?
}

main() {
  sudo apt update && sudo apt upgrade -y
}

# : <<'USAGE'
# SHERWOOD_REPO='https://github.com/joepatmckenna/sherwood.git'
# SHERWOOD_DIR='/root/sherwood'
# if [[ -d "${SHERWOOD_DIR}" ]]; then
#   git -C "${SHERWOOD_DIR}" pull
# else
#   git clone "${SHERWOOD_REPO}" "${SHERWOOD_DIR}"
# fi

# sudo systemctl restart sherwood

# sudo rsync -a --delete /root/sherwood/ui/ /var/www/html/

# sudo systemctl status sherwood  
# sudo systemctl status nginx  
# USAGE

# ########################################

# : <<'USAGE'
# source /root/shwerwood/main.sh
# main
# integration_test
# USAGE

# ########################################

# : <<'LOGS'
# sudo journalctl -u postgres
# sudo journalctl -u sherwood
# sudo journalctl -u nginx
# LOGS

# ########################################

# : <<'POSTGRES_CMDS'
# sudo -u postgres psql -c "ALTER USER postgres WITH PASSWORD 'password';"
# POSTGRES_CMDS

# : <<'POSTGRES_MODS'
# /etc/postgresql/16/main/pg_hba.conf
# - local   all             postgres                                peer
# + local   all             postgres                                scram-sha-256
# + host    all             all            <LOCAL_IP_ADDR>/32       scram-sha-256
# /etc/postgresql/16/main/postgresql.conf
# + listen_addresses = '*'`
# + port = 5432
# sudo ufw allow 5432/tcp
# POSTGRES_MODS

# ########################################

# # sudo cp /usr/share/postgresql/16/postgresql.conf.sample /etc/postgresql/16/main/postgresql.conf
# # sudo cp /usr/share/postgresql/16/pg_hba.conf.sample /etc/postgresql/16/main/pg_hba.conf


# setup_nginx() {
#   # Certificate: /etc/letsencrypt/live/writewell.tech/fullchain.pem
#   # Private Key: /etc/letsencrypt/live/writewell.tech/privkey.pem
#   # /etc/letsencrypt/renewal/writewell.tech.conf
#   sudo apt install -y nginx certbot
#   local src="${SHERWOOD_DIR}"/nginx.conf
#   # dst=$(nginx -V 2>&1 | grep -oP '(?<=--conf-path=)[^\s]+') 
#   dst='/etc/nginx/nginx.conf'
#   sudo mv "${dst}" "${dst}.bak"
#   sudo cp "${src}" "${dst}"
#   sudo certbot certonly \
#     --nginx \
#     -d writewell.tech,www.writewell.tech \
#     --agree-tos \
#     --non-interactive
#   sudo certbot renew --dry-run
#   sudo nginx -s reload # soft
#   # sudo systemctl restart nginx # hard
# }

# # setup_nginx() {
# #   sudo apt install -y nginx

# #   local config="${SHERWOOD_DIR}"/nginx.conf
# #   local available="/etc/nginx/sites-available/sherwood"
# #   local enabled="/etc/nginx/sites-enabled/sherwood"

# #   if [ ! -f "${config}" ]; then
# #     echo "error: ${config} does not exist."
# #     return 1
# #   fi

# #   sudo cp "${config}" "${available}"

# #   if [ -L "${enabled}" ]; then
# #     local target=$(readlink -f "${enabled}")
# #     if [ "${target}" != "${available}" ]; then
# #       sudo ln -sf "${available}" "${enabled}"
# #     fi
# #   elif [ -e "$ENABLED_PATH" ]; then
# #     echo "error: ${enabled} exists but is not a symbolic link."
# #     return 1
# #   else
# #     sudo ln -s "${available}" "${enabled}"
# #   fi
  
# #   sudo nginx -t
# #   return $? 
# # } 

# set -e

# main() {
#   sudo apt update && sudo apt upgrade -y

#   setup_nginx()
#   # nginx -s reload

#   sudo apt install -y \
#     certbot \
#     git \
#     nginx \
#     postgresql \
#     python3 \
#     python3-certbot-nginx \
#     python3-pip \
#     python3-venv

#   sudo systemctl start postgresql
#   sudo systemctl enable postgresql

#   # sherwood
#   if [[ -d "${SHERWOOD_DIR}" ]]; then
#     git -C "${SHERWOOD_DIR}" pull
#   else
#     git clone "${SHERWOOD_REPO}" "${SHERWOOD_DIR}"
#   fi

#   python3 -m venv "${VENV_DIR}"
#   "${PYTHON}" -m pip install "${SHERWOOD_DIR}" --no-cache-dir

#   sudo cp "${SHERWOOD_DIR}"/service /etc/systemd/system/sherwood
#   sudo systemctl daemon-reload
#   sudo systemctl enable sherwood
#   sudo systemctl start sherwood

#   sudo rsync -a --delete /root/sherwood/ui/ /var/www/html/
#   sudo chown -R www-data:www-data /var/www/html
#   sudo chmod -R 755 /var/www/html

#   sudo cp "${SHERWOOD_DIR}"/nginx.conf /etc/nginx/sites-available/sherwood
#   [ -L /etc/nginx/sites-enabled/sherwood ] && rm /etc/nginx/sites-enabled/sherwood
#   sudo ln -s /etc/nginx/sites-available/sherwood /etc/nginx/sites-enabled/
#   sudo nginx -t

#   sudo systemctl restart nginx
#   sudo systemctl restart sherwood

#   sudo certbot --nginx -d writewell.tech -d www.writewell.tech --agree-tos --email=joepatmckenna@gmail.com --non-interactive 
#   sudo certbot renew --dry-run

#   # sudo ufw allow 80
#   # sudo ufw allow 443
#   # sudo ufw enable 
  
#   sudo systemctl status postgresql
#   sudo systemctl status sherwood  
#   sudo systemctl status nginx  
# }

# ########################################

# integration_test_case() {
#   email="${1}"
#   method="${2}"
#   route="${3}"
#   data="${4:-}"

#   DOMAIN='https://writewell.tech'

#   tmp_res=$(mktemp)

#   cmd=(curl -s -o "${tmp_res}" -w "%{http_code}" -X "${method}" "${DOMAIN}${route}")
#   if [ -n "${data}" ]; then
#     cmd+=(-d "${data}" -H "Content-Type: application/json")
#   fi
#   access_token="${access_token_by_email[${email}]}"
#   if [ -n "${access_token}" ]; then
#     cmd+=(-H "X-Sherwood-Authorization: Bearer ${access_token}")
#   fi

#   status_code=$("${cmd[@]}")

#   res=$(cat "$tmp_res")
#   rm "$tmp_res"

#   echo "${status_code}" "${email}" "${method}" "${route}"

#   if [ "${status_code}" -ne 200 ]; then
#     echo "${cmd[@]}"
#     echo "$res"
#   elif [ "${route}" = "/http/sign-in" ]; then
#     access_token_by_email["${email}"]=$(echo $res | jq -r .access_token)
#   elif [ "${route}" = "/http/user" ]; then
#     user_id_by_email["${email}"]=$(echo $res | jq -r .id)
#   fi
# }

# integration_test() {
#   email_1="integration-test-$((RANDOM * RANDOM))@web.com"
#   email_2="integration-test-$((RANDOM * RANDOM))@web.com"

#   PASSWORD='Abcd@1234'

#   declare -A access_token_by_email
#   declare -A user_id_by_email

#   integration_test_case "${email_1}" POST /http/sign-up '{"email": "'"${email_1}"'", "password": "'"${PASSWORD}"'"}'
#   integration_test_case "${email_1}" POST /http/sign-in '{"email": "'"${email_1}"'", "password": "'"${PASSWORD}"'"}'
#   integration_test_case "${email_2}" POST /http/sign-up '{"email": "'"${email_2}"'", "password": "'"${PASSWORD}"'"}'
#   integration_test_case "${email_2}" POST /http/sign-in '{"email": "'"${email_2}"'", "password": "'"${PASSWORD}"'"}'
#   integration_test_case "${email_1}" GET /http/user
#   integration_test_case "${email_2}" GET /http/user
#   integration_test_case "${email_1}" POST /http/deposit '{"dollars": 1010}'
#   integration_test_case "${email_1}" POST /http/withdraw '{"dollars": 10}'
#   integration_test_case "${email_2}" POST /http/deposit '{"dollars": 1000}'
#   integration_test_case "${email_1}" POST /http/buy '{"symbol": "TSLA", "dollars": 500}'
#   integration_test_case "${email_1}" POST /http/sell '{"symbol": "TSLA", "dollars": 100}'
#   integration_test_case "${email_2}" POST /http/invest '{"investee_portfolio_id": "'"${user_id_by_email[${email_1}]}"'", "dollars": 100}'
#   integration_test_case "${email_2}" POST /http/divest '{"investee_portfolio_id": "'"${user_id_by_email[${email_1}]}"'", "dollars": 10}'

#   for email in "${!access_token_by_email[@]}"; do
#       echo
#       echo email: "${email}"
#       echo user id: "${user_id_by_email[$email]}"
#       echo access token: "${access_token_by_email[$email]}"
#       echo
#   done

#   sudo -u postgres psql -d db -c "DELETE FROM users WHERE email LIKE 'integration-test-%';"
# }
