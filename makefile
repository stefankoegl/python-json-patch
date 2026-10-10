
help:
	@echo "jsonpatch"
	@echo "Makefile targets"
	@echo " - test: run tests"
	@echo " - coverage: run tests with coverage"
	@echo
	@echo "To install jsonpatch, type"
	@echo "  pip install ."
	@echo

test:
	python -Wd -m coverage run --branch --source=jsonpatch tests.py
	python -Wd -m coverage run --append --branch --source=jsonpatch property_tests.py
	coverage report --show-missing

coverage:
	coverage run --source=jsonpatch tests.py
	coverage run --append --source=jsonpatch property_tests.py
	coverage report -m
