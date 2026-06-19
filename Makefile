.PHONY: lint lint-fix test

lint:
	ruff check .

lint-fix:
	ruff check --fix .

install:
	python -m pip install -e . -v --break-system-packages

test:
	.venv/bin/python -c "import sys; sys.path.insert(0, '.'); exec(open('test/bn/main.py').read())"