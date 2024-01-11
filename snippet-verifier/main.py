import argparse
import sys
import snippet
from pathlib import Path


def main(args: list[str]):
    parser = argparse.ArgumentParser(prog="SnippetCheck",
                                     description="Verify source code snippets actually correspond to source files content")
    parser.add_argument("-s", "--sources_root")
    parser.add_argument("markdown_files", nargs='+')
    args = parser.parse_args(args)
    try:
        docs = args.markdown_files
        error_count = 0
        for doc in docs:
            snippets = snippet.extract_snippets(read_file_lines(doc))
            doc_errors = snippet.verify_snippets(snippets, system_file_accessor(args.sources_root))
            for e in doc_errors:
                error_count += 1
                print(f"{Path(doc).parts[-1]}: {e}", file=sys.stderr)
        if error_count > 0:
            exit(1)
    except Exception as e:
        print(f"Snippet validation failed with error: \"{e}\"", file=sys.stderr)
        exit(2)


def read_file_lines(filename: str | Path) -> list[str]:
    with open(filename, 'r', encoding='utf-8') as f:
        return f.readlines()


def system_file_accessor(root: str) -> snippet.file_accessor:
    def access(file_name: str) -> list[str] | None:
        file = Path(root) / file_name
        if file.exists():
            return read_file_lines(file.resolve())
        else:
            return None

    return access


if __name__ == '__main__':
    main(sys.argv[1:])