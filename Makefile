test:
	@python3 -m pytest

lint:
	@python3 -m flake8

major:
	@NEWVERSION=`awk 'BEGIN{FS="."; OFS="."}{++$$1;}END{print $$1, 0, 0}' VERSION` \
		&& echo $$NEWVERSION > VERSION \
		&& git commit -a -m "Version $$NEWVERSION" \
		&& git tag $$NEWVERSION \
		&& git push --tag

minor:
	@NEWVERSION=`awk 'BEGIN{FS="."; OFS="."}{++$$2;}END{print $$1, $$2, 0}' VERSION` \
		&& echo $$NEWVERSION > VERSION \
		&& git commit -a -m "Version $$NEWVERSION" \
		&& git tag $$NEWVERSION \
		&& git push --tag

patch:
	@NEWVERSION=`awk 'BEGIN{FS="."; OFS="."}{++$$3;}END{print $$1, $$2, $$3}' VERSION` \
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
 test:		Perform unit testing on the source code\n\
 lint:		Perform quality checks on the source code\n\
 major:		Creates an incremented Major Tag\n\
 minor:		Creates an incremented Minor Tag\n\
 patch:		Creates an incremented Patch Tag\n\
 develop:	Installs all requirements and testing requirements\n\
 clean:		Removes built Python Packages and cached byte code\n\
 help:		Displays the help menu with all the targets\n";

.DEFAULT_GOAL := help
.PHONY: test lint patch dev clean help
