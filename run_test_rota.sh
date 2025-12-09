#!/bin/bash
# Helper script to run ROTA command tests locally

cd "$(dirname "$0")"
source venv/bin/activate
PYTHONPATH=$(pwd):$PYTHONPATH python tests/test_rota_command.py




