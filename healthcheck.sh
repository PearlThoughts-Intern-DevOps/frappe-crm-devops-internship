#!/bin/bash
curl -fs http://localhost:8000/api/method/ping > /dev/null || exit 1
