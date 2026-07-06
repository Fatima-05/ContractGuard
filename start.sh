#!/bin/bash
set -e

# Start FastAPI backend on internal port 8000
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --log-level warning &

# Wait for backend
sleep 3

# Start Streamlit frontend on the HF Spaces port
streamlit run frontend/app.py \
    --server.port 7860 \
    --server.address 0.0.0.0 \
    --server.headless true \
    --server.enableCORS false
