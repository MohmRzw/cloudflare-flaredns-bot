#!/usr/bin/env bash

# =======================================
#  Flare DNS - Cloudflare DNS TG Bot
#  Installer & Manager
# =======================================

# Current script directory (where install.sh is located)
BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$BASE_DIR/venv"
SCREEN_NAME="flaredns-bot"
CONFIG_FILE="$BASE_DIR/config.py"
REQUIREMENTS_FILE="$BASE_DIR/requirements.txt"

# ---------- Colors ----------
RED='\e[38;5;196m'
GREEN='\e[38;5;46m'
YELLOW='\e[38;5;226m'
CYAN='\e[38;5;51m'
PURPLE='\e[38;5;129m'
PINK='\e[38;5;213m'
BLUE='\e[38;5;33m'
WHITE='\e[97m'
BOLD='\e[1m'
UNDER='\e[4m'
RESET='\e[0m'

show_header() {
    clear
    echo -e "${PURPLE}┌──────────────────────────────────────────────────────────────┐${RESET}"
    echo -e "${PURPLE}│${RESET} ${PINK}${BOLD}🔥 FLARE DNS - Cloudflare DNS Telegram Bot 🔥${RESET}         ${PURPLE}│${RESET}"
    echo -e "${PURPLE}│${RESET} ${CYAN}Installer & Manager v2.0${RESET}                               ${PURPLE}│${RESET}"
    echo -e "${PURPLE}└──────────────────────────────────────────────────────────────┘${RESET}"
    echo
echo -e "${PURPLE}┌──────────────────────────────────────────────────┐${RESET}"
    echo -e "${PURPLE}│${CYAN}   ______ _                   _____  _   _  _____ ${PURPLE}│${RESET}"
    echo -e "${PURPLE}│${CYAN}   |  ____| |                 |  __ \| \ | |/ ____|${PURPLE}│${RESET}"
    echo -e "${PURPLE}│${CYAN}   | |__  | | __ _ _ __ ___   | |  | |  \| | (___  ${PURPLE}│${RESET}"
    echo -e "${PURPLE}│${CYAN}   |  __| | |/ _\` | '__/ _ \  | |  | | . \` |\___ \ ${PURPLE}│${RESET}"
    echo -e "${PURPLE}│${CYAN}   | |    | | (_| | | |  __/  | |__| | |\  |____) |${PURPLE}│${RESET}"
    echo -e "${PURPLE}│${CYAN}   |_|    |_|\__,_|_|  \___|  |_____/|_| \_|_____/ ${PURPLE}│${RESET}"
    echo -e "${PURPLE}│${PINK}                                                  ${PURPLE}│${RESET}"
    echo
    echo -e "${BLUE}   Created by${WHITE}:${RESET} @mohmrzw  ${WHITE}|${RESET}  ExploreTechIR"
    echo -e "${BLUE}   GitHub   ${WHITE}->${RESET} https://github.com/MohmRzw"
    echo -e "${BLUE}   YouTube  ${WHITE}->${RESET} https://youtube.com/@mohmrzw"
    echo -e "${BLUE}   Telegram ${WHITE}->${RESET} https://t.me/ExploreTechIR"
    echo
}

pause() {
    echo
    read -rp "Press Enter to go back to menu..." _
}

# ---------- Detect accounts file from config.py ----------
get_accounts_file() {
    local file="${BASE_DIR}/accounts.json"
    if [ -f "$CONFIG_FILE" ]; then
        local line
        line=$(grep -E '^ACCOUNTS_FILE\s*=' "$CONFIG_FILE" | head -n1)
        if [ -n "$line" ]; then
            local val
            val=$(echo "$line" | sed -E 's/^[^"]*"([^"]*)".*/\1/')
            if [ -n "$val" ]; then
                file="${BASE_DIR}/${val}"
            fi
        fi
    fi
    echo "$file"
}

# ---------- Dependencies ----------
install_dependencies() {
    echo -e "${CYAN}┌── Installing system dependencies (python3, venv, pip, screen)...${RESET}"
    if command -v apt-get &>/dev/null; then
        apt-get update -qq >/dev/null
        apt-get install -y python3 python3-venv python3-pip screen >/dev/null 2>&1
        echo -e "${GREEN}│ ✔ Python3, venv, pip, screen installed (or already present).${RESET}"
    else
        echo -e "${YELLOW}│ ⚠ apt-get not found. Please install Python 3 and screen manually.${RESET}"
    fi

    if [ ! -d "$VENV_DIR" ]; then
        echo -e "${YELLOW}│ Creating virtual environment at: ${VENV_DIR}${RESET}"
        python3 -m venv "$VENV_DIR"
        echo -e "${GREEN}│ ✔ Virtual environment created.${RESET}"
    else
        echo -e "${GREEN}│ ✔ Virtual environment already exists.${RESET}"
    fi

    echo -e "${YELLOW}│ Installing Python packages into venv...${RESET}"
    # shellcheck disable=SC1090
    source "$VENV_DIR/bin/activate"
    if [ -f "$REQUIREMENTS_FILE" ]; then
        pip install --upgrade pip >/dev/null 2>&1
        pip install -r "$REQUIREMENTS_FILE" >/dev/null 2>&1
    else
        pip install --upgrade pip >/dev/null 2>&1
        pip install aiogram aiohttp >/dev/null 2>&1
    fi
    deactivate
    echo -e "${GREEN}└── All Python dependencies installed successfully!${RESET}"
    echo
}

# ---------- Create / overwrite config.py ----------
create_config() {
    echo -e "${PURPLE}┌── Configuration Setup (config.py) ─────────────────────────────┐${RESET}"

    if [ -f "$CONFIG_FILE" ]; then
        echo -e "${YELLOW}│ config.py already exists at: ${CONFIG_FILE}${RESET}"
        read -rp "│ Do you want to overwrite it completely? (y/N): " overwrite
        overwrite=${overwrite,,}
        if [[ "$overwrite" != "y" ]]; then
            echo -e "${YELLOW}└── Skipping config.py overwrite.${RESET}"
            echo
            return
        fi
    fi

    DEFAULT_API_URL="https://api.cloudflare.com/client/v4"
    DEFAULT_ACCOUNTS_FILE="accounts.json"

    echo
    read -rp "🔑 Enter your Telegram BOT_TOKEN: " BOT_TOKEN
    while [[ -z "$BOT_TOKEN" ]]; do
        echo -e "${RED}   ✖ BOT_TOKEN cannot be empty.${RESET}"
        read -rp "🔑 Enter your Telegram BOT_TOKEN: " BOT_TOKEN
    done

    echo
    read -rp "👤 Enter your Telegram Admin ID (numeric): " ADMIN_ID
    while ! [[ "$ADMIN_ID" =~ ^[0-9]+$ ]]; do
        echo -e "${RED}   ✖ Admin ID must be numeric.${RESET}"
        read -rp "👤 Enter your Telegram Admin ID (numeric): " ADMIN_ID
    done

    echo
    read -rp "☁️  Cloudflare API URL [${DEFAULT_API_URL}]: " API_URL
    API_URL=${API_URL:-$DEFAULT_API_URL}

    echo
    read -rp "📁 Accounts file name [${DEFAULT_ACCOUNTS_FILE}]: " ACCOUNTS_FILE
    ACCOUNTS_FILE=${ACCOUNTS_FILE:-$DEFAULT_ACCOUNTS_FILE}

    echo
    echo -e "${CYAN}Preview of your config values (copy if you want):${RESET}"
    echo "  BOT_TOKEN      = ${BOT_TOKEN}"
    echo "  ADMIN_ID       = ${ADMIN_ID}"
    echo "  API_URL        = ${API_URL}"
    echo "  ACCOUNTS_FILE  = ${ACCOUNTS_FILE}"
    echo
    read -rp "Press Enter to save these values to config.py (Ctrl+C to cancel)..." _

    cat > "$CONFIG_FILE" <<EOF
# -*- coding: utf-8 -*-

# Telegram bot token
BOT_TOKEN = "${BOT_TOKEN}"

# Numeric Telegram user ID of admin
ADMIN_ID = ${ADMIN_ID}

# Cloudflare API base URL
API_URL = "${API_URL}"

# File where Cloudflare accounts (API tokens) are stored
ACCOUNTS_FILE = "${ACCOUNTS_FILE}"

# Icons used in the bot UI
ICONS = {
    # Main actions
    "ADD": "➕",
    "EDIT": "✏️",
    "DELETE": "🗑️",
    "BACK": "🔙",
    "REFRESH": "🔄",
    "CANCEL": "❌",
    "CONFIRM": "✅",

    # Main menu
    "ZONES": "🌐",
    "ACCOUNTS": "👤",
    "STATS": "📊",
    "HELP": "ℹ️",
    "LOGOUT": "🚪",

    # Status
    "ACTIVE": "✅",
    "PENDING": "⏳",
    "PROXIED": "☁️",  # CDN ON
    "DNS_ONLY": "➡️",  # CDN OFF
    "SUCCESS": "✅",
    "ERROR": "❌",
    "INFO": "ℹ️",
    "WARNING": "⚠️",

    # DNS record types
    "A": "🇦",
    "AAAA": "🇦",
    "CNAME": "🇨",
    "TXT": "🇹",
    "MX": "🇲",
    "NS": "🇳",

    # Other
    "DEFAULT": "🔹",
    "TARGET": "🎯",
    "NAME": "🏷️",
    "TYPE": "🔹",
    "TTL": "⏱️",
    "KEY": "🔑",
    "SPINNER": "⏳",
}
EOF

    echo -e "${GREEN}└── config.py created/updated successfully at ${CONFIG_FILE}.${RESET}"
    echo
}

# ---------- Manage Cloudflare tokens (accounts.json) ----------
manage_cloudflare_tokens() {
    local ACC_FILE
    ACC_FILE="$(get_accounts_file)"

    mkdir -p "$(dirname "$ACC_FILE")"
    if [ ! -f "$ACC_FILE" ]; then
        echo "{}" > "$ACC_FILE"
    fi

    while true; do
        show_header
        echo -e "${BOLD}Cloudflare account tokens (accounts.json)${RESET}"
        echo -e "${YELLOW}File: ${ACC_FILE}${RESET}"
        echo
        echo "1) View tokens"
        echo "2) Add / Update token"
        echo "3) Delete token"
        echo "0) Back to main menu"
        echo
        read -rp "Choose an option [0-3]: " ch

        case "$ch" in
            1)
                show_header
                echo -e "${CYAN}Current accounts.json content:${RESET}"
                if command -v jq &>/dev/null; then
                    jq . "$ACC_FILE" 2>/dev/null || cat "$ACC_FILE"
                else
                    if command -v python3 &>/dev/null; then
                        python3 - <<PYEOF
import json,sys
p="${ACC_FILE}"
try:
    data=json.load(open(p,"r",encoding="utf-8"))
    print(json.dumps(data,indent=2,ensure_ascii=False))
except Exception:
    print(open(p,encoding="utf-8").read())
PYEOF
                    else
                        cat "$ACC_FILE"
                    fi
                fi
                pause
                ;;
            2)
                show_header
                echo -e "${CYAN}Add / Update Cloudflare API token${RESET}"
                read -rp "Account name (key): " accname
                if [ -z "$accname" ]; then
                    echo -e "${YELLOW}Empty name, cancelled.${RESET}"
                    pause
                    continue
                fi
                read -rp "Token value: " acctoken
                if [ -z "$acctoken" ]; then
                    echo -e "${YELLOW}Empty token, cancelled.${RESET}"
                    pause
                    continue
                fi
                python3 - <<PYEOF
import json,os
path="${ACC_FILE}"
data={}
if os.path.exists(path):
    try:
        with open(path,"r",encoding="utf-8") as f:
            data=json.load(f)
    except Exception:
        data={}
data["${accname}"]="${acctoken}"
with open(path,"w",encoding="utf-8") as f:
    json.dump(data,f,ensure_ascii=False,indent=2)
PYEOF
                echo -e "${GREEN}✔ Token for '${accname}' saved to accounts file.${RESET}"
                pause
                ;;
            3)
                show_header
                echo -e "${CYAN}Delete Cloudflare account token${RESET}"
                read -rp "Account name to delete: " accname
                if [ -z "$accname" ]; then
                    echo -e "${YELLOW}Empty name, cancelled.${RESET}"
                    pause
                    continue
                fi
                python3 - <<PYEOF
import json,os
path="${ACC_FILE}"
if not os.path.exists(path):
    exit()
try:
    with open(path,"r",encoding="utf-8") as f:
        data=json.load(f)
except Exception:
    data={}
if "${accname}" in data:
    del data["${accname}"]
    with open(path,"w",encoding="utf-8") as f:
        json.dump(data,f,ensure_ascii=False,indent=2)
PYEOF
                echo -e "${GREEN}✔ If existed, '${accname}' was removed from accounts file.${RESET}"
                pause
                ;;
            0)
                break
                ;;
            *)
                echo -e "${RED}Invalid choice.${RESET}"
                sleep 1
                ;;
        esac
    done
}

# ---------- Edit config fields ----------
edit_config_field() {
    local field_name="$1"
    local prompt="$2"
    local is_string="$3"  # "yes" or "no"

    if [ ! -f "$CONFIG_FILE" ]; then
        echo -e "${RED}✖ config.py not found. Use install option first.${RESET}"
        return
    fi

    local current
    if [ "$is_string" = "yes" ]; then
        current=$(grep -E "^${field_name}\s*=" "$CONFIG_FILE" | sed -E 's/^[^"]*"([^"]*)".*/\1/')
    else
        current=$(grep -E "^${field_name}\s*=" "$CONFIG_FILE" | sed -E 's/^[^=]*=\s*([0-9]+).*/\1/')
    fi

    echo -e "${YELLOW}Current ${field_name}: ${current}${RESET}"
    read -rp "${prompt}: " newval
    if [ -z "$newval" ]; then
        echo -e "${YELLOW}Empty input, no changes applied.${RESET}"
        return
    fi

    if [ "$is_string" = "yes" ]; then
        sed -i "s|^${field_name}\s*=.*|${field_name} = \"${newval}\"|" "$CONFIG_FILE"
    else
        if ! [[ "$newval" =~ ^[0-9]+$ ]]; then
            echo -e "${RED}New value must be numeric.${RESET}"
            return
        fi
        sed -i "s|^${field_name}\s*=.*|${field_name} = ${newval}|" "$CONFIG_FILE"
    fi

    echo -e "${GREEN}✔ ${field_name} updated successfully.${RESET}"
}

# ---------- Full install ----------
install_bot() {
    show_header
    echo -e "${CYAN}${BOLD}⚙️  Install / Reinstall Flare DNS Bot${RESET}"
    echo
    install_dependencies
    create_config
    echo -e "${GREEN}✅ Installation finished.${RESET}"
    echo -e "You can now start the bot from the menu."
}

# ---------- Uninstall ----------
uninstall_bot() {
    show_header
    echo -e "${RED}${BOLD}🗑️  Uninstall Flare DNS Bot${RESET}"
    echo
    read -rp "Are you sure you want to remove the bot and its config? (y/N): " ans
    ans=${ans,,}
    if [[ "$ans" != "y" ]]; then
        echo -e "${YELLOW}Uninstall cancelled.${RESET}"
        return
    fi

    echo -e "${YELLOW}Stopping bot (normal & screen)...${RESET}"
    pkill -f "python.*bot.py" 2>/dev/null || true
    screen -S "$SCREEN_NAME" -X quit 2>/dev/null || true

    echo -e "${YELLOW}Removing virtualenv...${RESET}"
    rm -rf "$VENV_DIR"

    echo -e "${YELLOW}Removing config.py and accounts.json...${RESET}"
    rm -f "$CONFIG_FILE"
    rm -f "$BASE_DIR/accounts.json"

    echo -e "${GREEN}✅ Bot and configs removed. bot.py and install.sh are kept.${RESET}"
}

# ---------- Start/Stop (normal) ----------
start_bot_normal() {
    show_header
    echo -e "${CYAN}▶️  Starting bot in foreground (normal)...${RESET}"
    if [ ! -d "$VENV_DIR" ]; then
        echo -e "${RED}venv not found. Run install first.${RESET}"
        return
    fi
    if [ ! -f "$CONFIG_FILE" ]; then
        echo -e "${RED}config.py not found. Run install first.${RESET}"
        return
    fi

    echo -e "${YELLOW}Press Ctrl + C to stop the bot and return here.${RESET}"
    cd "$BASE_DIR" || exit 1
    # shellcheck disable=SC1090
    source "$VENV_DIR/bin/activate"
    python bot.py
    deactivate
}

stop_bot_normal() {
    show_header
    echo -e "${CYAN}⏹  Stopping bot (python bot.py processes)...${RESET}"
    pkill -f "python.*bot.py" 2>/dev/null && \
        echo -e "${GREEN}✔ Bot processes stopped.${RESET}" || \
        echo -e "${YELLOW}No active bot process found.${RESET}"
}

# ---------- Start/Stop with screen ----------
start_bot_screen() {
    show_header
    echo -e "${CYAN}📟 Starting bot in screen session (${SCREEN_NAME})...${RESET}"
    if [ ! -d "$VENV_DIR" ]; then
        echo -e "${RED}venv not found. Run install first.${RESET}"
        return
    fi
    if [ ! -f "$CONFIG_FILE" ]; then
        echo -e "${RED}config.py not found. Run install first.${RESET}"
        return
    fi

    if screen -list | grep -q "$SCREEN_NAME"; then
        echo -e "${YELLOW}A screen session named ${SCREEN_NAME} is already running.${RESET}"
        return
    fi

    cd "$BASE_DIR" || exit 1
    screen -dmS "$SCREEN_NAME" bash -c "source '$VENV_DIR/bin/activate' && python bot.py"
    echo -e "${GREEN}✅ Bot started in screen session: ${SCREEN_NAME}${RESET}"
    echo -e "Attach with: ${BOLD}screen -r ${SCREEN_NAME}${RESET}"
}

stop_bot_screen() {
    show_header
    echo -e "${CYAN}🛑 Stopping screen session (${SCREEN_NAME})...${RESET}"
    if screen -list | grep -q "$SCREEN_NAME"; then
        screen -S "$SCREEN_NAME" -X quit
        echo -e "${GREEN}✔ Screen session stopped.${RESET}"
    else
        echo -e "${YELLOW}No screen session named ${SCREEN_NAME} found.${RESET}"
    fi
}

# ---------- Main menu ----------
main_menu() {
    while true; do
        show_header
        echo -e "${BOLD}${UNDER}Main menu:${RESET}"
        echo
        echo -e "${CYAN} 1)${RESET} 🧩 Install / Reinstall Bot  ${YELLOW}(deps + venv + config.py)${RESET}"
        echo -e "${CYAN} 2)${RESET} 🗑️  Uninstall Bot ${RED}(remove venv & config)${RESET}"
        echo -e "${CYAN} 3)${RESET} 🔑 Edit Bot Token (config.py)"
        echo -e "${CYAN} 4)${RESET} 👤 Edit Admin ID (config.py)"
        echo -e "${CYAN} 5)${RESET} 🔐 Manage Cloudflare account tokens (accounts.json)"
        echo -e "${CYAN} 6)${RESET} ▶️  Start Bot (Foreground)"
        echo -e "${CYAN} 7)${RESET} ⏹  Stop Bot (Foreground)"
        echo -e "${CYAN} 8)${RESET} 📟 Start Bot in Screen  ${BOLD}(Recommended)${RESET}"
        echo -e "${CYAN} 9)${RESET} ❌ Stop Screen Session"
        echo -e "${CYAN} 0)${RESET} 🚪 Exit"
        echo
        echo -e "${PURPLE}┌──────────────────────────────────────────────────────────────┐${RESET}"
        echo -ne "${CYAN}Select option [0-9] -> ${RESET}"
        read -r choice
        echo -e "${PURPLE}└──────────────────────────────────────────────────────────────┘${RESET}"

        case "$choice" in
            1) install_bot; pause ;;
            2) uninstall_bot; pause ;;
            3) edit_config_field "BOT_TOKEN" "Enter new Bot Token" "yes"; pause ;;
            4) edit_config_field "ADMIN_ID" "Enter new Admin ID (numeric)" "no"; pause ;;
            5) manage_cloudflare_tokens ;;  # منوی داخلی خودش pause دارد
            6) start_bot_normal; pause ;;
            7) stop_bot_normal; pause ;;
            8) start_bot_screen; pause ;;
            9) stop_bot_screen; pause ;;
            0) echo -e "${GREEN}\nThanks for using Flare DNS Bot! ✨${RESET}\n"; exit 0 ;;
            *) echo -e "${RED}\nInvalid option! Try again.${RESET}"; sleep 1.5 ;;
        esac
    done
}

# ---------- Root warning ----------
if [[ "$EUID" -ne 0 ]]; then
    echo -e "${YELLOW}${BOLD}⚠  Warning:${RESET}${YELLOW} It is recommended to run this installer as root"
    echo -e "   (for apt, pkill, screen).${RESET}"
    read -rp "Continue without root? (y/N): " cont
    cont=${cont,,}
    if [[ "$cont" != "y" ]]; then
        exit 1
    fi
fi

main_menu
