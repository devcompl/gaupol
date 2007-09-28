# Copyright (C) 2007 Osmo Salomaa
#
# This file is part of Gaupol.
#
# Gaupol is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# Gaupol is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# Gaupol.  If not, see <http://www.gnu.org/licenses/>.

"""Automatic correcting of texts."""

import gaupol
import re
import sys
_ = gaupol.i18n._


class TextAgent(gaupol.Delegate):

    """Automatic correcting of texts."""

    # pylint: disable-msg=E0203,W0201

    __metaclass__ = gaupol.Contractual
    _re_capitalizable = re.compile(r"^\W*(?<!\.\.\.)\w", re.UNICODE)

    def _capitalize_position(self, parser, pos):
        """Capitalize the first alphanumeric character from position."""

        match = self._re_capitalizable.search(parser.text[pos:])
        if match is not None:
            a = pos + match.start()
            prefix = parser.text[:a]
            text = parser.text[a:a + 1].capitalize()
            suffix = parser.text[a + 1:]
            parser.text = prefix + text + suffix
        return match is not None

    def _capitalize_text(self, parser, pattern, cap_next):
        """Capitalize all matches of pattern in parser's text.

        Return True if the text of the next subtitle should be capitalized.
        """
        try:
            a, z = parser.next()
        except StopIteration:
            return cap_next
        if pattern.get_field("Capitalize") == "Start":
            self._capitalize_position(parser, a)
        elif pattern.get_field("Capitalize") == "After":
            cap_next = not self._capitalize_position(parser, z)
        return self._capitalize_text(parser, pattern, cap_next)

    def _get_subtitutions(self, patterns):
        """Get a list of tuples of pattern, flags, replacement."""

        re_patterns = []
        for pattern in (x for x in patterns if x.enabled):
            string = pattern.get_field("Pattern")
            flags = pattern.get_flags()
            replacement = pattern.get_field("Replacement")
            re_patterns.append((string, flags, replacement))
        return re_patterns

    def _remove_leftover_spaces(self, texts, parser):
        """Remove excess whitespace in texts."""

        def substitute(pattern, replacement):
            parser.set_regex(pattern)
            parser.replacement = replacement
            parser.replace_all()

        texts = texts[:]
        for i, text in enumerate(texts):
            parser.set_text(text)
            substitute(r"(^\s+|\s+$)", "")
            substitute(r" {2,}", " ")
            substitute(r"^\W*$", "")
            substitute(r"(^\n|\n$)", "")
            substitute(r"^-(\S)", r"- \1")
            substitute(r"^- (.*?^[^-])", r"\1")
            substitute(r"\A- ([^\n]*)\Z", r"\1")
            texts[i] = parser.get_text()
        return texts

    def break_lines_require(self, indexes, *args, **kwargs):
        for index in (indexes or []):
            assert 0 <= index < len(self.subtitles)

    @gaupol.util.revertable
    @gaupol.util.asserted_return
    def break_lines(self, indexes, doc, patterns, length_func, max_length,
        max_lines, max_deviation, skip=False, max_skip_length=sys.maxint,
        max_skip_lines=sys.maxint, register=-1):
        """Break lines to fit defined maximum line length and count.

        indexes can be None to process all subtitles.
        length_func should return the length of a string argument.
        max_lines may be violated to avoid violating max_length.
        max_deviation is a funky number between 0 and 1.
        If skip is True, subtitles that do not violate or manage to reduce
        max_skip_length and max_skip_lines are skipped.
        Raise re.error if bad pattern or replacement.
        """
        new_indexes = []
        new_texts = []
        patterns = self._get_subtitutions(patterns)
        patterns = [(re.compile(x, y), z) for x, y, z in patterns]
        liner = self.get_liner(doc)
        liner.break_points = patterns
        liner.max_deviation = max_deviation
        liner.max_length = max_length
        liner.max_lines = max_lines
        liner.set_length_func(length_func)
        re_tag = self.get_tag_regex(doc)
        indexes = indexes or range(len(self.subtitles))
        for index in indexes:
            subtitle = self.subtitles[index]
            liner.set_text(subtitle.get_text(doc))
            tagless_text = subtitle.get_text(doc)
            if re_tag is not None:
                tagless_text = re_tag.sub("", tagless_text)
            lines = tagless_text.split("\n")
            length = max(length_func(x) for x in lines)
            line_count = len(lines)
            if (length <= max_skip_length):
                if (line_count <= max_skip_lines):
                    # Skip subtitles that do not violate
                    # any of the defined skip conditions.
                    if skip: continue
            text = liner.break_lines()
            if re_tag is not None:
                tagless_text = re_tag.sub("", text)
            lines = tagless_text.split("\n")
            length_down = max(length_func(x) for x in lines) < length
            lines_down = len(lines) < line_count
            length_fixed = (length > max_skip_length) and length_down
            lines_fixed = (line_count > max_skip_lines) and lines_down
            if (not length_fixed) and (not lines_fixed):
                # Implicitly require reduction of violator
                # if only lines in violation are to be broken.
                if skip: continue
            if text != subtitle.get_text(doc):
                new_indexes.append(index)
                new_texts.append(text)
        assert new_indexes
        self.replace_texts(new_indexes, doc, new_texts, register=register)
        self.set_action_description(register, _("Breaking lines"))

    def capitalize_require(self, indexes, doc, pattern, register=-1):
        for index in (indexes or []):
            assert 0 <= index < len(self.subtitles)

    @gaupol.util.revertable
    @gaupol.util.asserted_return
    def capitalize(self, indexes, doc, patterns, register=-1):
        """Capitalize texts as defined by patterns.

        indexes can be None to process all subtitles.
        Raise re.error if bad pattern or replacement.
        """
        new_indexes = []
        new_texts = []
        parser = self.get_parser(doc)
        indexes = indexes or range(len(self.subtitles))
        for indexes in gaupol.util.get_ranges(indexes):
            cap_next = False
            for index in indexes:
                subtitle = self.subtitles[index]
                parser.set_text(subtitle.get_text(doc))
                if cap_next or (index == 0):
                    self._capitalize_position(parser, 0)
                    cap_next = False
                for pattern in (x for x in patterns if x.enabled):
                    string = pattern.get_field("Pattern")
                    flags = pattern.get_flags()
                    parser.set_regex(string, flags, 0)
                    parser.pos = 0
                    args = (parser, pattern, cap_next)
                    cap_next = self._capitalize_text(*args)
                text = parser.get_text()
                if text != subtitle.get_text(doc):
                    new_indexes.append(index)
                    new_texts.append(text)
        assert new_indexes
        self.replace_texts(new_indexes, doc, new_texts, register=register)
        description = _("Capitalizing texts")
        self.set_action_description(register, description)

    def correct_common_errors_require(self, indexes, *args, **kwargs):
        for index in (indexes or []):
            assert 0 <= index < len(self.subtitles)

    @gaupol.util.revertable
    @gaupol.util.asserted_return
    def correct_common_errors(self, indexes, doc, patterns, register=-1):
        """Correct common human and OCR errors  in texts.

        indexes can be None to process all subtitles.
        Raise re.error if bad pattern or replacement.
        """
        new_indexes = []
        new_texts = []
        parser = self.get_parser(doc)
        re_patterns = self._get_subtitutions(patterns)
        repeats = [x.get_field_boolean("Repeat") for x in patterns]
        indexes = indexes or range(len(self.subtitles))
        for index in indexes:
            subtitle = self.subtitles[index]
            parser.set_text(subtitle.get_text(doc))
            for i, (string, flags, replacement) in enumerate(re_patterns):
                parser.set_regex(string, flags, 0)
                parser.replacement = replacement
                count = parser.replace_all()
                while repeats[i] and count:
                    count = parser.replace_all()
            text = parser.get_text()
            if text != subtitle.get_text(doc):
                new_indexes.append(index)
                new_texts.append(text)
        assert new_indexes
        self.replace_texts(new_indexes, doc, new_texts, register=register)
        description = _("Correcting common errors")
        self.set_action_description(register, description)

    def remove_hearing_impaired_require(self, indexes, *args, **kwargs):
        for index in (indexes or []):
            assert 0 <= index < len(self.subtitles)

    @gaupol.util.revertable
    @gaupol.util.asserted_return
    def remove_hearing_impaired(self, indexes, doc, patterns, register=-1):
        """Remove hearing impaired parts from subtitles.

        indexes can be None to process all subtitles.
        Raise re.error if bad pattern or replacement.
        """
        new_indexes = []
        new_texts = []
        parser = self.get_parser(doc)
        re_patterns = self._get_subtitutions(patterns)
        indexes = indexes or range(len(self.subtitles))
        for index in indexes:
            subtitle = self.subtitles[index]
            parser.set_text(subtitle.get_text(doc))
            for string, flags, replacement in re_patterns:
                parser.set_regex(string, flags, 0)
                parser.replacement = replacement
                parser.replace_all()
            text = parser.get_text()
            if text != subtitle.get_text(doc):
                new_indexes.append(index)
                new_texts.append(text)
        new_texts = self._remove_leftover_spaces(new_texts, parser)
        assert new_indexes
        self.replace_texts(new_indexes, doc, new_texts, register=register)
        description = _("Removing hearing impaired texts")
        self.set_action_description(register, description)
        remove_indexes = []
        for i, text in (x for x in enumerate(new_texts) if not x[1]):
            remove_indexes.append(new_indexes[i])
        assert remove_indexes
        self.remove_subtitles(remove_indexes, register=register)
        self.group_actions(register, 2, description)
