PY=python3
VERIFY_SNIPPETS=$(PY) snippet-verifier/main.py --sources_root=.

example-tests:
	$(MAKE) -C c tests
	$(MAKE) -C java tests
	$(MAKE) -C node tests
	$(MAKE) -C zig tests

checks:
	$(MAKE) -C node fmt-check
	$(MAKE) -C zig fmt-check
	$(MAKE) -C snippet-verifier tests
	$(VERIFY_SNIPPETS) Post.md 
	$(VERIFY_SNIPPETS) Post_fr.md

ci-setup:
	$(MAKE) -C node ci-setup
	$(MAKE) -C snippet-verifier ci-setup
