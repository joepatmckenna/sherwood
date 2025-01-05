#!/bin/bash
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

git clone https://github.com/joepatmckenna/sherwood.git
cd sherwood

python3 -m venv venv
source venv/bin/activate

python -m pip install .

sudo systemctl start postgresql
sudo systemctl enable postgresql
sudo -i -u postgres psql <<EOF
CREATE DATABASE sherwood_db;
CREATE USER sherwood WITH PASSWORD 'password';
GRANT ALL PRIVILEGES ON DATABASE sherwood_db TO sherwood;
EOF

cp sherwood.service /etc/systemd/system/sherwood.service
sudo systemctl daemon-reload
sudo systemctl enable sherwood
sudo systemctl start sherwood

cp sherwood.nginx /etc/nginx/sites-available/sherwood
# sudo rm /etc/nginx/sites-enabled/sherwood
sudo ln -s /etc/nginx/sites-available/sherwood /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

sudo certbot --nginx -d writewell.tech -d www.writewell.tech
sudo certbot renew --dry-run

sudo ufw allow 'Nginx Full'

# python sherwood/main.py --bind="127.0.0.1:8000" --reload &

# sudo systemctl restart postgresql
# sudo systemctl restart sherwood
# sudo systemctl status postgresql
# sudo systemctl status sherwood


# sudo journalctl -u sherwood -f
# sudo tail -f /var/log/nginx/access.log /var/log/nginx/error.log
# sudo tail -f /var/log/postgresql/postgresql-16-main.log

# cat /etc/postgresql/16/main/pg_hba.conf
# cat /etc/postgresql/16/main/postgresql.conf

# curl https://writewell.tech

# curl https://www.writewell.tech

# curl -X POST https://www.writewell.tech/sign_up \
#      -H "Content-Type: application/json" \
#      -d '{"email": "user@web.com", "password": "Abcd@1234"}'