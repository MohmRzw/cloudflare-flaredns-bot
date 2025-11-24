#!/usr/bin/env bash
set -e

REPO_URL="https://github.com/MohmRzw/cloudflare-flaredns-bot.git"
INSTALL_DIR="$HOME/cloudflare-flaredns-bot"

echo ">>> Flare DNS remote installer"
echo "    Target directory: $INSTALL_DIR"
echo

if [ -d "$INSTALL_DIR/.git" ]; then
    echo "✔ Repository already exists at: $INSTALL_DIR"
    cd "$INSTALL_DIR"

    read -rp "Do you want to update to latest version from GitHub? (y/N): " upd
    upd=${upd,,}
    if [[ "$upd" == "y" ]]; then
        echo ">>> Pulling latest changes..."
        git pull --ff-only
        echo "✔ Repository updated."
    else
        echo "↪ Skipping git pull (using existing code)."
    fi
else
    echo ">>> Cloning repository into: $INSTALL_DIR"
    rm -rf "$INSTALL_DIR"
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
    echo "✔ Repository cloned."
fi

chmod +x install.sh

echo
echo ">>> Running local installer..."
sudo ./install.sh
