V := 0
AT_0 := @
AT_1 :=
AT = $(AT_$(V))

SHELL := "/bin/bash"

NOSE := $(shell which nosetests)
SOURCES := Makefile pdorclient.conf \
    $(shell find {pdorclient,tests} -type f \
    -and -not \( \
	  -name '.*.swp' -or \
	  -name '*.pyc' \
	\) \
)

all: test-stamp

coverage: test-stamp
	$(AT)coverage report -m

test: tests

tests: test-stamp

test-stamp: $(SOURCES)
	$(AT)coverage run $(NOSE) tests/test_config.py
	$(AT)coverage run -a $(NOSE) tests/test_zone.py
	$(AT)coverage run -a $(NOSE) tests/test_record.py
	$(AT)touch $@

.PHONY: all coverage test tests
