"""Tests for epmcminer.utils.file_utils."""

from pathlib import Path

from epmcminer.utils.file_utils import (
    MAX_FILENAME_COMPONENT_LENGTH,
    build_pdf_filename,
    ensure_output_structure,
    sanitise_filename,
)


class TestSanitiseFilename:
    """Tests for sanitise_filename."""

    def test_valid_string_unchanged(self) -> None:
        """A string with no invalid characters is returned unchanged."""
        assert sanitise_filename("valid_filename") == "valid_filename"

    def test_forward_slash_replaced(self) -> None:
        """Forward slashes are replaced with underscores."""
        assert sanitise_filename("10.1234/test") == "10.1234_test"

    def test_colon_replaced(self) -> None:
        """Colons are replaced with underscores."""
        assert sanitise_filename("title: study") == "title__study"

    def test_whitespace_replaced_with_underscore(self) -> None:
        """Whitespace is replaced with underscores."""
        assert sanitise_filename("the title here") == "the_title_here"

    def test_multiple_spaces_become_single_underscore(self) -> None:
        """Multiple consecutive spaces become a single underscore."""
        assert sanitise_filename("a  b") == "a_b"

    def test_backslash_replaced(self) -> None:
        """Backslashes are replaced with underscores."""
        assert sanitise_filename("path\\file") == "path_file"

    def test_question_mark_replaced(self) -> None:
        """Question marks are replaced with underscores."""
        assert sanitise_filename("what?") == "what_"

    def test_asterisk_replaced(self) -> None:
        """Asterisks are replaced with underscores."""
        assert sanitise_filename("star*fish") == "star_fish"

    def test_pipe_replaced(self) -> None:
        """Pipe characters are replaced with underscores."""
        assert sanitise_filename("a|b") == "a_b"

    def test_angle_brackets_replaced(self) -> None:
        """Angle brackets are replaced with underscores."""
        assert sanitise_filename("<tag>") == "_tag_"

    def test_double_quote_replaced(self) -> None:
        """Double quotes are replaced with underscores."""
        assert sanitise_filename('say "hello"') == "say__hello_"

    def test_empty_string_returns_underscore(self) -> None:
        """An empty string returns a single underscore."""
        assert sanitise_filename("") == "_"

    def test_only_invalid_chars_returns_underscore(self) -> None:
        """A string of only invalid characters returns a single underscore."""
        assert sanitise_filename("///") == "_"

    def test_long_string_truncated(self) -> None:
        """Strings longer than MAX_FILENAME_COMPONENT_LENGTH are truncated."""
        long_str = "a" * (MAX_FILENAME_COMPONENT_LENGTH + 50)
        result = sanitise_filename(long_str)
        assert len(result) <= MAX_FILENAME_COMPONENT_LENGTH

    def test_string_at_max_length_not_truncated(self) -> None:
        """A string exactly at MAX_FILENAME_COMPONENT_LENGTH is not truncated."""
        exact = "a" * MAX_FILENAME_COMPONENT_LENGTH
        assert sanitise_filename(exact) == exact

    def test_doi_sanitised_correctly(self) -> None:
        """A DOI with slashes and dots is sanitised to a valid filename segment."""
        assert sanitise_filename("10.1016/j.jad.2022.01.001") == "10.1016_j.jad.2022.01.001"

    def test_unicode_preserved(self) -> None:
        """Unicode letters that are valid in filenames are preserved."""
        assert sanitise_filename("Ärger über") == "Ärger_über"

    def test_newline_replaced(self) -> None:
        """Newlines (control characters) are replaced with underscores."""
        assert sanitise_filename("line\nbreak") == "line_break"

    def test_tab_replaced_with_underscore(self) -> None:
        """Tab characters are treated as whitespace and replaced with a single underscore."""
        assert sanitise_filename("col\tcol") == "col_col"

    def test_custom_max_length_truncates(self) -> None:
        """Passing max_length truncates the result to that length."""
        assert sanitise_filename("abcdefgh", max_length=4) == "abcd"

    def test_custom_max_length_no_truncation_when_short(self) -> None:
        """max_length has no effect when the string is already shorter."""
        assert sanitise_filename("abc", max_length=10) == "abc"

    def test_max_length_one(self) -> None:
        """max_length=1 keeps only the first character."""
        assert sanitise_filename("hello", max_length=1) == "h"

    def test_max_length_zero_returns_underscore(self) -> None:
        """max_length=0 truncates to empty, which falls back to '_'."""
        assert sanitise_filename("hello", max_length=0) == "_"


# ---------------------------------------------------------------------------
# TestBuildPdfFilename
# ---------------------------------------------------------------------------


class TestBuildPdfFilename:
    """Tests for build_pdf_filename."""

    def test_result_ends_with_pdf(self) -> None:
        """The filename always ends with '.pdf'."""
        assert build_pdf_filename("10.1/a", "My Title").endswith(".pdf")

    def test_format_doi_underscore_title(self) -> None:
        """The filename format is '{doi_part}_{title_part}.pdf'."""
        result = build_pdf_filename("10.1234/test", "Sample Title")
        assert result == "10.1234_test_Sample_Title.pdf"

    def test_doi_slash_sanitised(self) -> None:
        """Slashes in the DOI are replaced with underscores."""
        result = build_pdf_filename("10.1016/j.jad.2022", "Title")
        assert "/" not in result

    def test_title_special_chars_sanitised(self) -> None:
        """Special characters in the title are replaced with underscores."""
        result = build_pdf_filename("10.1/a", "Title: A Study?")
        assert ":" not in result
        assert "?" not in result

    def test_empty_doi_uses_placeholder(self) -> None:
        """An empty DOI string produces 'no_doi' in the filename."""
        result = build_pdf_filename("", "Some Title")
        assert result.startswith("no_doi_")

    def test_empty_title_uses_placeholder(self) -> None:
        """An empty title string produces 'no_title' in the filename."""
        result = build_pdf_filename("10.1/a", "")
        assert "_no_title.pdf" in result

    def test_both_empty_uses_both_placeholders(self) -> None:
        """Both empty strings produce 'no_doi_no_title.pdf'."""
        assert build_pdf_filename("", "") == "no_doi_no_title.pdf"

    def test_long_inputs_are_truncated(self) -> None:
        """Very long DOI or title inputs do not produce an excessively long filename."""
        long_doi = "x" * 200
        long_title = "y" * 200
        result = build_pdf_filename(long_doi, long_title)
        assert len(result) <= 2 * MAX_FILENAME_COMPONENT_LENGTH + len("_.pdf")


# ---------------------------------------------------------------------------
# TestEnsureOutputStructure
# ---------------------------------------------------------------------------


class TestEnsureOutputStructure:
    """Tests for ensure_output_structure."""

    def test_creates_pdfs_subdirectory(self, tmp_path: Path) -> None:
        """ensure_output_structure creates the pdfs/ subdirectory."""
        folder = tmp_path / "output"
        folder.mkdir()
        ensure_output_structure(folder)
        assert (folder / "pdfs").is_dir()

    def test_creates_logs_subdirectory(self, tmp_path: Path) -> None:
        """ensure_output_structure creates the logs/ subdirectory."""
        folder = tmp_path / "output"
        folder.mkdir()
        ensure_output_structure(folder)
        assert (folder / "logs").is_dir()

    def test_is_idempotent(self, tmp_path: Path) -> None:
        """Calling ensure_output_structure twice does not raise."""
        folder = tmp_path / "output"
        folder.mkdir()
        ensure_output_structure(folder)
        ensure_output_structure(folder)

    def test_creates_output_folder_if_missing(self, tmp_path: Path) -> None:
        """ensure_output_structure creates nested directories when output_folder is absent."""
        folder = tmp_path / "new" / "nested"
        ensure_output_structure(folder)
        assert (folder / "pdfs").is_dir()
        assert (folder / "logs").is_dir()
