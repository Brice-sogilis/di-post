ZIG=zig

tests: build.zig example.zig
	$(ZIG) build test

fmt-check: build.zig example.zig
	$(ZIG) fmt --check build.zig
	$(ZIG) fmt --check example.zig

fmt: build.zig example.zig
	$(ZIG) fmt build.zig
	$(ZIG) fmt example.zig