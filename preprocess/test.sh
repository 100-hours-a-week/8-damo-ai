#!/bin/bash

echo "1. 가상환경 의존성 테스트"
poetry run pytest tests/test_dependencies.py

echo "2. Playwright 브라우저 테스트"
poetry run pytest tests/test_playwright.py