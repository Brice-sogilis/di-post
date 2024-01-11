example-tests:
	$(MAKE) -C java tests
	$(MAKE) -C node tests
	$(MAKE) -C zig tests

checks:
	$(MAKE) -C node fmt-check
	$(MAKE) -C zig fmt-check

ci-setup:
	$(MAKE) -C node ci-setup
