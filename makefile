
help:
	@echo "jsonpatch"
	@echo "Makefile targets"
	@echo " - test: run tests"
	@echo " - coverage: run tests with coverage"
	@echo
	@echo "To install jsonpatch, type"
	@echo "  python setup.py install"
	@echo

test:
	python tests.py

coverage:
	coverage run --source=jsonpatch tests.py
	coverage report -m
