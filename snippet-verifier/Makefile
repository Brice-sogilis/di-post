PY=python3

tests:
	$(PY) -m mypy snippet.py
	$(PY) -m unittest snippet.py

ci-setup:
	$(PY) -m pip install -r requirements.txt