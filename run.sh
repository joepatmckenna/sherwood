#!/bin/bash
sudo apt update && sudo apt upgrade -y

sudo apt install -y python3-venv python3-pip

python3 -m venv venv

source venv/bin/activate

git clone https://github.com/joepatmckenna/sherwood.git

cd sherwood

python -m pip install .

python sherwood/main.py --bind="0.0.0.0:8000" --reload &

sudo apt install -y nginx

mv nginx /etc/nginx/sites-available/sherwood

sudo ln -s /etc/nginx/sites-available/sherwood /etc/nginx/sites-enabled/

sudo systemctl restart nginx

sudo ufw allow 'Nginx Full'

sudo apt install -y certbot python3-certbot-nginx

sudo certbot --nginx -d writewell.tech

# curl -v http://www.writewell.tech/sign_up \
#   -w "%{http_code}\n" \
#   -H "Content-Type: application/json" \
#   -d '{"email": "user@web.com", "password": "Abcd@1234"}'  
