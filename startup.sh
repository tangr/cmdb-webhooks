#!/bin/bash

export PYTHONDONTWRITEBYTECODE=1

uvicorn app.main:app --reload
# or
fastapi dev app/main.py
