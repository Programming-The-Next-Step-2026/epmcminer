"""Tests for epmcminer.utils.file_utils."""


from epmcminer.utils.file_utils import MAX_FILENAME_COMPONENT_LENGTH, sanitise_filename


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
