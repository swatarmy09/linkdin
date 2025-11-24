#!/bin/bash
# Install playwright browsers if not present
if [ ! -d "/opt/render/.cache/ms-playwright/chromium_headless_shell-1194" ]; then
    echo "Installing Playwright browsers..."
    playwright install --with-deps chromium
fi
python main.py
