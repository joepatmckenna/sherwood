#!/bin/bash

lsof -t -i :8000 | xargs kill -9
venv/bin/python -m pip install -e . --no-cache-dir
source .env
# extra_files=($( find sherwood -type f ))
venv/bin/python sherwood/main.py --bind="127.0.0.1:8000" --reload
# "${extra_files[@]/#/--reload-extra-file=}"

# Run `nginx -t` to get location of nginx config file
#   nginx: the configuration file /opt/homebrew/etc/nginx/nginx.conf syntax is ok
#   nginx: configuration file /opt/homebrew/etc/nginx/nginx.conf test is successful
# Add 'include /opt/homebrew/etc/nginx/sites-enabled/*;' under the http block in the config file
sudo mkdir -p /opt/homebrew/etc/nginx/sites-available
sudo mkdir -p /opt/homebrew/etc/nginx/sites-enabled
sudo cp ./nginx.conf.dev /opt/homebrew/etc/nginx/sites-available/sherwood
nginx -t
brew services restart nginx

sudo ln -s /opt/homebrew/etc/nginx/sites-available/sherwood /opt/homebrew/etc/nginx/sites-enabled/
sudo mkdir -p /var/www/html/sherwood
sudo rsync -a --delete ./ui/ /var/www/html/sherwood/
fswatch -o ./ui | while read; do
    sudo rsync -a --delete ./ui/ /var/www/html/sherwood/
done