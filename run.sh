#!/bin/bash
sudo apt update

sudo apt upgrade -y

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

# change
# local postgres peer
# local postgres sha-..
# in
# /etc/postgresql/16/main/pg_hba.conf

python3 -m venv venv

git clone https://github.com/joepatmckenna/sherwood.git

venv/bin/python -m pip install ./sherwood

sudo cp sherwood/sherwood.service /etc/systemd/system/sherwood.service
sudo systemctl daemon-reload
sudo systemctl enable sherwood
sudo systemctl start sherwood

sudo cp sherwood/sherwood.nginx /etc/nginx/sites-available/sherwood
sudo ln -s /etc/nginx/sites-available/sherwood /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

sudo certbot --nginx -d writewell.tech -d www.writewell.tech
sudo certbot renew --dry-run

##################################################################
##################################################################
##################################################################

git -C /root/sherwood pull
/root/venv/bin/python -m pip install /root/sherwood
sudo systemctl restart sherwood
sudo journalctl -u sherwood -f

##################################################################
##################################################################
##################################################################

curl -s -o /dev/null -w "%{http_code}" https://writewell.tech
curl -s -o /dev/null -w "%{http_code}" https://www.writewell.tech

EMAIL='heytherebear@web.com'
PASSWORD='Abcd@1234'

curl -s -o /dev/null -w "%{http_code}" \
-X POST https://www.writewell.tech/sign-up \
-H "Content-Type: application/json" \
-d "{\"email\": \"${EMAIL}\", \"password\": \"${PASSWORD}\"}"

token=$(curl -X POST https://www.writewell.tech/sign-in \
-H "Content-Type: application/json" \
-d "{\"email\": \"${EMAIL}\", \"password\": \"${PASSWORD}\"}")

token_type=$(echo $token | jq -r .token_type)
access_token=$(echo $token | jq -r .access_token)

curl https://www.writewell.tech/user \
-H "Content-Type: application/json" \
-H "X-Sherwood-Authorization: ${token_type} ${access_token}" 

curl -X POST https://www.writewell.tech/deposit \
-H "Content-Type: application/json" \
-H "X-Sherwood-Authorization: ${token_type} ${access_token}" \
-d "{\"dollars\": "100"}"

##################################################################
##################################################################
##################################################################
