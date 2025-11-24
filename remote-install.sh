#!/usr/bin/env bash
set -e

cd /root
rm -rf cloudflare-flaredns-bot
git clone https://github.com/MohmRzw/cloudflare-flaredns-bot.git
cd cloudflare-flaredns-bot
chmod +x install.sh
sudo ./install.sh
