#!/bin/bash

psql -U $(whoami) -d postgres
CREATE ROLE postgres WITH LOGIN SUPERUSER PASSWORD 'password';
CREATE DATABASE db;
\q

PYTHON='venv/bin/python'
"${PYTHON}" -m pip install -e . --no-cache-dir
lsof -t -i :8000 | xargs kill
source .env.dev
"${PYTHON}" sherwood/main.py --bind="127.0.0.1:8000"

# nginx -t
# nginx: the configuration file /opt/homebrew/etc/nginx/nginx.conf syntax is ok
# nginx: configuration file /opt/homebrew/etc/nginx/nginx.conf test is successful
#
# Add 'include /opt/homebrew/etc/nginx/sites-enabled/*;' under the http block in /opt/homebrew/etc/nginx/nginx.conf

sudo mkdir -p /opt/homebrew/etc/nginx/sites-available
sudo mkdir -p /opt/homebrew/etc/nginx/sites-enabled
sudo cp ./nginx.conf /opt/homebrew/etc/nginx/sites-available/sherwood.local
sudo ln -s /opt/homebrew/etc/nginx/sites-available/sherwood.local /opt/homebrew/etc/nginx/sites-enabled/

sudo mkdir -p /var/www/html
sudo rsync -a --delete ./ui/ /var/www/html/
nginx -t
brew services restart nginx

# curl http://localhost:80/x/sign-up -X POST -H "Content-Type: application/json" -d '{"email": "user@web.com", "password": "Abcd@1234"}'
# curl http:/127.0.0.1:8000/sign-up -X POST -H "Content-Type: application/json" -d '{"email": "user@web.com", "password": "Abcd@1234"}'

fswatch -o ./ui | while read; do
    sudo rsync -a --delete ./ui/ /var/www/html/
done
