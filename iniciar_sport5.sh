#!/bin/bash
(sleep 1 && xdg-open http://localhost:8000 2>/dev/null || open http://localhost:8000 2>/dev/null) &
python3 server.py
