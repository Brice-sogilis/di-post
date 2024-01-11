example-tests:
	$(MAKE) -C java
	$(MAKE) -C node
	$(MAKE) -C zig

checks:
	$(MAKE) -C node fmt-check
	$(MAKE) -C zig fmt-check