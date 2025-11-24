#!/bin/bash
echo "Installing Playwright Chromium..."
playwright install chromium

echo "Starting Python app..."
python main.py
