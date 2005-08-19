# Copyright (C) 2005 Osmo Salomaa
#
# This file is part of Gaupol.
#
# Gaupol is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Gaupol is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Gaupol; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA


"""MPL2 file."""

# Documentation:
# http://napisy.ussbrowarek.org/mpl2-eng.html


import codecs
import re

try:
    from psyco.classes import *
except ImportError:
    pass

from gaupol.constants import EXTENSION, FORMAT, MODE
from gaupol.lib.files.subfile import SubtitleFile
from gaupol.lib.timing.calc import TimeFrameCalculator


RE_LINE = re.compile(r'^\[(\d+)\]\[(\d+)\](.*?)$')


class MPL2(SubtitleFile):
    
    """
    MPL2 file.
    
    MPL2 format quick reference:
    [182][221]And that completes my final report|until we reach touchdown.
    [222][260]We're now on full automatic,|in the hands of the computers.
    """
    
    def __init__(self, *args):

        SubtitleFile.__init__(self, *args)
        
        self.FORMAT    = FORMAT.MPL2
        self.EXTENSION = EXTENSION.MPL2
        self.MODE      = MODE.TIME
    
    def read(self):
        """
        Read MPL2 file.

        Raise IOError if reading fails.
        Raise UnicodeError if decoding fails.
        Return: show times, hide times, texts
        """
        lines = self._read_lines()
        
        shows = []
        hides = []
        texts = []

        # Split lines list to components.
        for line in lines:
        
            match = RE_LINE.match(line)
            
            if match is not None:
                shows.append(match.group(1))
                hides.append(match.group(2))
                texts.append(match.group(3))

        calc = TimeFrameCalculator()

        # Convert timings from decaseconds to seconds and finally times.
        for entry in [shows, hides]:
            for i in range(len(entry)):
                deca_string = entry[i]
                seconds = float(deca_string[:-1] + '.' + deca_string[-1])
                entry[i] = calc.seconds_to_time(seconds)

        # Replace pipes in texts with Python internal newline characters.
        for i in range(len(texts)):
            texts[i] = texts[i].replace('|', '\n')

        return shows, hides, texts

    def write(self, shows, hides, texts):
        """
        Write MPL2 file.

        Raise IOError if writing fails.
        Raise UnicodeError if encoding fails.
        """
        newline_character = self._get_newline_character()

        calc = TimeFrameCalculator()

        # Convert timings from times to seconds and finally decaseconds.
        for entry in [shows, hides]:
            for i in range(len(entry)):
                decaseconds = calc.time_to_seconds(entry[i]) * 10
                entry[i] = '%.0f' % decaseconds

        # Replace Python internal newline characters in text with pipes.
        texts = [text.replace('\n', '|') for text in texts]

        subtitle_file = codecs.open(self.path, 'w', self.encoding)

        try:
            for i in range(len(shows)):
                subtitle_file.write('[%s][%s]%s%s' % (
                    shows[i], hides[i], texts[i], newline_character
                ))
        finally:
            subtitle_file.close()
