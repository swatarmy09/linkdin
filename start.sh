#!/bin/bash
pip install -r requirements.txt
playwright install
playwright install-deps
python main.py
