#!/bin/bash
streamlit run src/app/main.py --server.port 8580 &
python src/app/server.py