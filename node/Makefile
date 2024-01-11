tests: out/example.js
	npm test

fmt-check: example.ts package.json tsconfig.json
	npm run fmt-check

fmt: example.ts package.json tsconfig.json
	npm run fmt

ci-setup:
	npm install

out/example.js: example.ts
	npm run compile
