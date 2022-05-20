demo:
	@python3 -m faker_events

test:
	@python3 -m pytest -vv

lint:
	@python3 -m flake8

patch:
	@NEWVERSION=`awk 'BEGIN{FS="."; OFS="."}{++$$2;}END{print $$1, $$2, $$3}' VERSION` \
		&& echo $$NEWVERSION > VERSION \
		&& git commit -a -m "Version $$NEWVERSION" \
		&& git tag $$NEWVERSION \
		&& git push --tag

develop:
	@python3 -m pip install -e .[develop]

clean:
	@find . -name '__pycache__' | xargs rm -fr

help:
	@echo "\
Targets\n\
------------------------------------------------------------------------\n\
 demo:		Demonstrate the output created by Faker Events\n\
 test:		Perform unit testing on the source code\n\
 lint:		Perform quality checks on the source code\n\
 patch:		Creates an incremented Patch Tag\n\
 develop:	Installs all requirements and testing requirements\n\
 clean:		Removes built Python Packages and cached byte code\n\
 help:		Displays the help menu with all the targets\n";

.DEFAULT_GOAL := help
.PHONY: test lint patch dev clean help
