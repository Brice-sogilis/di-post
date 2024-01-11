import unittest
from typing import Callable
from dataclasses import dataclass


@dataclass
class LineRange:
    """
    Inclusive line range, starting from 1
    """
    start: int
    end: int

    def get(self, lines: list[str]):
        return lines[self.start - 1: self.end]


@dataclass
class SnippetError:
    doc_line_range: LineRange
    message: str

    def __str__(self):
        return f"Snippet {self.doc_line_range.start}-{self.doc_line_range.end}: {self.message}"


@dataclass
class Snippet:
    source: str
    source_line_range: LineRange
    doc_line_range: LineRange
    content: list[str]

    def mismatch(self, source_content: list[str]) -> bool:
        content_in_range = self.source_line_range.get(source_content)
        if len(content_in_range) != len(self.content):
            return True
        for source_line, content_line in zip(content_in_range, self.content):
            if source_line.lstrip() != content_line.lstrip():
                return True
        return False


file_accessor = Callable[[str], list[str] | None]


def verify_snippets(snippets: list[Snippet], file_access: file_accessor) -> list[SnippetError]:
    res = []
    for s in snippets:
        source_content = file_access(s.source)
        if source_content is None:
            res.append(SnippetError(doc_line_range=s.doc_line_range, message=f"Missing source file {s.source}"))
        elif s.mismatch(source_content):
            res.append(SnippetError(doc_line_range=s.doc_line_range, message=f"Source file content mismatch in {s.source}"))
    return res


@dataclass
class SourcedSnippetParams:
    source: str
    source_line_range: LineRange

    def to_snippet(self, doc_line_range: LineRange, content: list[str]) -> Snippet:
        return Snippet(source=self.source, doc_line_range=doc_line_range, source_line_range=self.source_line_range,
                       content=content)

    @staticmethod
    def parse(line: str) -> "SourcedSnippetParams | None":
        """
        :param line:
        :returns: the parsed configuration if any or None if no sourced snippet configuration was found
        :raises Exception: if the line represents an invalid configuration
        """
        source: str | None = None
        source_lines_range: LineRange | None = None
        for param in line.rsplit():
            source_param = SourcedSnippetParams.parse_param("source", param)
            source_line_param = SourcedSnippetParams.parse_param("lines", param)

            if source_param is not None:
                source = source_param
                if len(source) == 0:
                    raise Exception("Source file name cannot be empty")

            if source_line_param is not None:
                source_lines_range_split = source_line_param.split("-")
                if len(source_lines_range_split) < 2:
                    raise Exception("Invalid source line range")
                source_lines_range = LineRange(int(source_lines_range_split[0]), int(source_lines_range_split[1]))

        if source is None and source_lines_range is None:
            # Not a sourced snippet
            return None
        elif source is not None and source_lines_range is not None:
            # Valid parameters
            return SourcedSnippetParams(source, source_lines_range)
        else:
            # Missing parameter
            raise Exception("Both source and lines are required")

    @staticmethod
    def parse_param(param_name: str, candidate: str) -> str | None:
        split = candidate.split(f"{param_name}=")
        if len(split) > 1:
            return split[1]
        else:
            return None


@dataclass
class OngoingSourcedSnippet:
    params: SourcedSnippetParams
    marker: str


@dataclass
class OngoingStandardSnippet:
    marker: str


class NoOngoingSnippet:
    pass


SnippetParsingStatus = OngoingSourcedSnippet | OngoingStandardSnippet | NoOngoingSnippet


def extract_snippets(lines: list[str]) -> list[Snippet]:
    snippet_parsing_status: SnippetParsingStatus = NoOngoingSnippet()
    start = 0
    res = []
    for line_index, line in enumerate(lines):
        if line.startswith("```"):
            match snippet_parsing_status:
                case NoOngoingSnippet():
                    start = line_index
                    snippet_parsing_status = start_snippet_parsing(line)

                case OngoingSourcedSnippet(params=params, marker=marker):
                    if marker_from_line(line) == marker:
                        res.append(params.to_snippet(doc_line_range=LineRange(start + 1, line_index + 1),
                                                     content=lines[start + 1:line_index]))
                        snippet_parsing_status = NoOngoingSnippet()

                case OngoingStandardSnippet(marker=marker):
                    if marker_from_line(line) == marker:
                        snippet_parsing_status = NoOngoingSnippet()
                case _:
                    raise Exception("Unreachable state")
    return res


def start_snippet_parsing(line: str) -> SnippetParsingStatus:
    marker = marker_from_line(line)
    params = SourcedSnippetParams.parse(line)
    if params is None:
        return OngoingStandardSnippet(marker)
    else:
        return OngoingSourcedSnippet(params, marker)


def marker_from_line(line: str):
    end = 0
    while len(line) > end and line[end] == '`':
        end += 1
    return line[0:end]


class Tests(unittest.TestCase):
    def test_no_snippet_no_error(self):
        no_snippets = extract_snippets([
            "# Some header",
            "Some documentation",
        ])
        errors = verify_snippets(no_snippets, no_files)
        self.assertListEqual(errors, [])

    def test_error_source_not_found(self):
        snippets = extract_snippets([
            "# Some header",
            "```java source=A.java lines=1-1",
            "// Comment",
            "```",
        ])
        errors = verify_snippets(snippets, no_files)
        self.assertListEqual(errors,
                             [SnippetError(doc_line_range=LineRange(2, 4), message="Missing source file A.java")])

    def test_error_content_mismatch(self):
        snippets = extract_snippets([
            "```java source=A.java lines=1-1",
            "// Single line",
            "```",
        ])
        source_content_mismatching = one_file_with_content("A.java", ["// Not the same line"])
        errors = verify_snippets(snippets, source_content_mismatching)
        self.assertListEqual(errors, [
            SnippetError(doc_line_range=LineRange(1, 3), message="Source file content mismatch in A.java")])

    def test_no_error_content_match(self):
        snippets = extract_snippets([
            "```java source=A.java  lines=1-1",
            "// Single line",
            "```",
        ])
        source_content_matching = one_file_with_content("A.java", ["// Single line"])
        errors = verify_snippets(snippets, source_content_matching)
        self.assertListEqual(errors, [])

    def test_error_wrong_lines(self):
        snippet_spanning_two_lines = extract_snippets([
            "```java source=A.java  lines=1-2",
            "// Line 2",
            "// Line 3",
            "```",
        ])
        source = [
            "// Line 1",
            "// Line 2",
            "// Line 3",
        ]
        source_content_mismatching = one_file_with_content("A.java", source)
        errors = verify_snippets(snippet_spanning_two_lines, source_content_mismatching)
        self.assertListEqual(errors, [
            SnippetError(doc_line_range=LineRange(1, 4), message="Source file content mismatch in A.java")])

    def test_error_too_many_lines(self):
        snippet_spanning_four_lines = extract_snippets([
            "```java source=A.java  lines=1-4",
            "// Line 1",
            "// Line 2",
            "// Line 3",
            "// Line 4",
            "```",
        ])
        two_lines_source = [
            "// Line 1",
            "// Line 2",
        ]
        source_content_mismatching = one_file_with_content("A.java", two_lines_source)
        errors = verify_snippets(snippet_spanning_four_lines, source_content_mismatching)
        self.assertListEqual(errors, [
            SnippetError(doc_line_range=LineRange(1, 6), message="Source file content mismatch in A.java")])

    def test_ignore_leading_indent(self):
        snippet_without_indentation = extract_snippets([
            "```kotlin source=K.kt lines=2-5",
            "val a = listOf(1,2,3).map { n ->",
            "  // Add one, return is implicit for last expression",
            "  n + 1",
            "}",
            "```",
        ])

        source_lines_with_indentation = [
            "fun test() {",
            "    val a = listOf(1,2,3).map { n ->",
            "    // Add one, return is implicit for last expression",
            "        n + 1",
            "    }",
            "    println(a)",
            "}"
        ]

        errors = verify_snippets(snippet_without_indentation,
                                 one_file_with_content("K.kt", source_lines_with_indentation))
        self.assertListEqual(errors, [])

    def test_extract_snippets(self):
        markdown = [
            "# Some header",
            "```java source=A.java  lines=1-1",
            "// Comment",
            "```",
        ]
        snippets = extract_snippets(markdown)
        self.assertListEqual(snippets, [
            Snippet(source="A.java", doc_line_range=LineRange(2, 4), source_line_range=LineRange(1, 1),
                    content=["// Comment"])])

    def test_ignore_nested_snippet_source(self):
        markdown = [
            "# Some header",
            "````md",
            "Here is the syntax for sourced java code snippet in markdown",
            "```java source=B.java  lines=1-1",
            "// Comment",
            "```",
            "````",
        ]
        snippets = extract_snippets(markdown)
        self.assertListEqual(snippets, [])

    def test_extract_snippet_unclosed_is_no_snippet(self):
        markdown = [
            "# Some header",
            "```java source=A.java  lines=1-1",
            "// Comment",
        ]
        snippets = extract_snippets(markdown)
        self.assertListEqual(snippets, [])

    def test_keep_nested_snippet_content(self):
        markdown = [
            "# Some header",
            "````md source=A.md  lines=1-4",
            "Here is the syntax for sourced java code snippet in markdown",
            "```java source=B.java  lines=1-1",
            "// Comment",
            "```",
            "````",
        ]
        snippets = extract_snippets(markdown)
        self.assertListEqual(snippets,
                             [Snippet(source="A.md", doc_line_range=LineRange(2, 7), source_line_range=LineRange(1, 4),
                                      content=[
                                          "Here is the syntax for sourced java code snippet in markdown",
                                          "```java source=B.java  lines=1-1",
                                          "// Comment",
                                          "```",
                                      ])])

    def test_extract_snippet_missing_source_raises(self):
        markdown = [
            "# Some header",
            "```java source=",
            "// Comment",
            "```",
        ]
        self.assertRaisesRegex(Exception, "Source file name cannot be empty", extract_snippets, markdown)


def no_files(_) -> str | None:
    return None


def one_file_with_content(filename: str, content: list[str]) -> file_accessor:
    def file_access(f: str) -> list[str] | None:
        if f == filename:
            return content
        else:
            return None

    return file_access