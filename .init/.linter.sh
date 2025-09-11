#!/bin/bash
cd /home/kavia/workspace/code-generation/healthcheckv2-1142-1191/healthcheckv2
source venv/bin/activate
flake8 .
LINT_EXIT_CODE=$?
if [ $LINT_EXIT_CODE -ne 0 ]; then
  exit 1
fi

