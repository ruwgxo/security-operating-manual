.PHONY: demo test book check
demo:
	python -m lab --simulate-approved
test:
	python -m unittest discover -s tests -v
book:
	python tools/publication.py --pdf
check: test book
