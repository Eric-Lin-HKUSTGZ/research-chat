#!/bin/bash
# Research Chat Backend - Development Start Script
# FastAPI + Uvicorn

APP_ENV=dev uvicorn asgi:app --host 0.0.0.0 --port 4200 --reload --log-level info
