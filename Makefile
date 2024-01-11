example-tests:
	$(MAKE) -C java
	$(MAKE) -C node

checks:
	$(MAKE) -C node fmt-check