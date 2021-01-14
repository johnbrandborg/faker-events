test:
	@pytest

lint:
	@flake8

patch:
	@NEWVERSION=`awk 'BEGIN{FS=".";OFS=".";}{$$3++;}END{print $$0}' VERSION` \
		&& echo $$NEWVERSION > VERSION \
		&& git commit -a -m 'Version $$NEWVERSION' \
		&& git tag v$$NEWVERSION \
		&& git push --tag

minor:
	@NEWVERSION=`awk 'BEGIN{FS=".";OFS=".";}{$$2++;}END{print $$0}' VERSION` \
		&& echo $$NEWVERSION > VERSION \
		&& git commit -a -m 'Version $$NEWVERSION' \
		&& git tag v$$NEWVERSION \
		&& git push --tag

major:
	@NEWVERSION=`awk 'BEGIN{FS=".";OFS=".";}{$$1++;}END{print $$0}' VERSION` \
		&& echo $$NEWVERSION > VERSION \
		&& git commit -a -m 'Version $$NEWVERSION' \
		&& git tag v$$NEWVERSION \
		&& git push --tag

dev:
	@pip install -e .[dev]

clean:
	@find . -name '__pycache__' | xargs rm -fr

help:
	@echo "\
Targets\n\
------------------------------------------------------------------------\n\
 test:		Perform unit testing on the source code\n\
 lint:		Perform quality checks on the source code\n\
 patch:		Creates a incremented Patch Tag\n\
 minor:		Creates a incremented Minor Tag\n\
 major:		Creates a incremented Major Tag verion\n\
 dev:		Installs all requirements and testing requirements\n\
 clean:		Removes built Python Packages and cached byte code\n\
 help:		Displays the help menu with all the targets\n";

.DEFAULT_GOAL := help
.PHONY: test lint patch minor major dev clean help
