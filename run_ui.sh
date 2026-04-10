#!/bin/bash
cd "$(dirname "$0")"
uv pip install flask --quiet
.venv/bin/python -m ui.app