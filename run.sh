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

python3 -m venv venv

git clone https://github.com/joepatmckenna/sherwood.git

venv/bin/python -m pip install ./sherwood

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

curl https://writewell.tech

curl https://www.writewell.tech

curl -X POST https://www.writewell.tech/sign_up \
     -H "Content-Type: application/json" \
     -d '{"email": "user18@web.com", "password": "Abcd@1234"}'

curl -X POST https://www.writewell.tech/sign_in \
     -H "Content-Type: application/json" \
     -d '{"email": "user111@web.com", "password": "Abcd@1234"}'

##################################################################
##################################################################
##################################################################

# sudo nano /etc/postgresql/16/main/pg_hba.conf

# sudo ufw allow 'Nginx Full'

# python sherwood/sherwood/main.py --bind="127.0.0.1:8000" --reload &

# sudo systemctl restart postgresql
# sudo systemctl restart sherwood
# sudo systemctl restart nginx

# sudo systemctl status postgresql
# sudo systemctl status sherwood
# sudo systemctl status nginx

# ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO sherwood;
# ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO sherwood;

# sudo tail -f /var/log/nginx/access.log /var/log/nginx/error.log
# sudo tail -f /var/log/postgresql/postgresql-16-main.log

# cat /etc/postgresql/16/main/pg_hba.conf
# cat /etc/postgresql/16/main/postgresql.conf

# sudo systemctl restart sherwood
# sudo journalctl -u sherwood -f

# sudo journalctl -u postgresql

# sudo rm /etc/nginx/sites-enabled/sherwood
