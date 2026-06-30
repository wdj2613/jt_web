#!/bin/sh
set -e

CONFIG_PATH="/app/config.json"

# Docker bind mount creates a directory when the source file doesn't exist.
# Remove it and create a proper JSON file with defaults instead.
if [ -d "$CONFIG_PATH" ]; then
    echo "WARNING: $CONFIG_PATH is a directory (bind-mount of a non-existent host file?). Removing and creating default config..."
    rm -rf "$CONFIG_PATH"
fi

if [ ! -f "$CONFIG_PATH" ]; then
    echo "No config.json found, creating default configuration..."
    cat > "$CONFIG_PATH" << 'EOF'
{
  "server": {
    "host": "0.0.0.0",
    "port": 5000,
    "debug": false
  },
  "cache": {
    "type": "SimpleCache",
    "default_timeout": 300,
    "key_prefix": "jt_web_",
    "news_list_timeout": 120,
    "article_detail_timeout": 600,
    "threshold": 500
  },
  "api": {
    "base_url": "http://appapi2.gamersky.com/v5/",
    "timeout": 30
  },
  "auth": {
    "enabled": false,
    "username": "admin",
    "password": "changeme",
    "secret_key": ""
  },
  "cors": {
    "origins": "*"
  },
  "logging": {
    "level": "INFO",
    "file": "logs/app.log"
  }
}
EOF
    echo "Default config.json created."
fi

exec "$@"
