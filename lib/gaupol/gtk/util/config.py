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
# along with Gaupol; if falset, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA


"""
Application settings.

Other modules can get and set variables through the container classes by
directly accessing their attributes.

ConfigParser is used for reading and writing the ini-style configuration file.
The configuration file is an .ini-style file in ~/.gaupol/gaupol.gtk.conf.
Values "true" or "false" are used for boolean fields and pipe-separated strings
for lists. All stored values are strings.
"""


try:
    from psyco.classes import *
except ImportError:
    pass

import ConfigParser
import logging
import os
import sys

from gaupol.constants        import *
from gaupol.gtk.colconstants import *
from gaupol                  import __version__


logger = logging.getLogger()


# Configuration file constants
CONFIG_DIR    = os.path.join(os.path.expanduser('~'), '.gaupol')
CONFIG_PATH   = os.path.join(CONFIG_DIR, 'gaupol.gtk.conf')
CONFIG_HEADER = \
'''# Gaupol GTK user interface configuration file
#
# This file is rewritten on each successful application exit. Entered values
# are checked for correct type, but not for correct value. To return to
# default settings, delete the corresponding lines or this entire file.

'''


class Type(object):

    """Types of configuration variables."""

    STRING        = 0
    INTEGER       = 1
    BOOLEAN       = 2
    CONSTANT      = 3

    STRING_LIST   = 4
    INTEGER_LIST  = 5
    BOOLEAN_LIST  = 6
    CONSTANT_LIST = 7

    @staticmethod
    def is_list(typ):
        """Return True if typ is a list type."""

        return typ in (4, 5, 6, 7)


sections = [
    'application_window',
    'editor',
    'encoding_dialog',
    'file',
    'general',
    'subtitle_insert',
    'spell_check',
    'spell_check_dialog',
]


class application_window(object):

    maximized      = False
    position       = [0, 0]
    show_statusbar = True
    show_toolbar   = True
    size           = [600, 400]

    types = {
        'maximized'     : Type.BOOLEAN,
        'position'      : Type.INTEGER_LIST,
        'show_statusbar': Type.BOOLEAN,
        'show_toolbar'  : Type.BOOLEAN,
        'size'          : Type.INTEGER_LIST,
    }

class editor(object):

    font             = None
    framerate        = Framerate.FR_23_976
    limit_undo       = True
    mode             = Mode.TIME
    undo_levels      = 50
    use_default_font = True
    visible_columns  = [NO, SHOW, HIDE, DURN, MTXT]

    types = {
        'font'            : Type.STRING,
        'framerate'       : Type.CONSTANT,
        'limit_undo'      : Type.BOOLEAN,
        'mode'            : Type.CONSTANT,
        'undo_levels'     : Type.INTEGER,
        'use_default_font': Type.BOOLEAN,
        'visible_columns' : Type.CONSTANT_LIST,
    }

    classes = {
        'framerate'      : Framerate,
        'mode'           : Mode,
        'visible_columns': Column,
    }


class encoding_dialog(object):

    size = [400, 400]

    types = {
        'size': Type.INTEGER_LIST,
    }

class file(object):

    directory            = os.path.expanduser('~')
    encoding             = None
    fallback_encodings   = ['utf_8', 'cp1252']
    format               = Format.SUBRIP
    maximum_recent_files = 5
    newlines             = Newlines.UNIX
    recent_files         = []
    try_locale_encoding  = True
    visible_encodings    = ['utf_8', 'cp1252']

    types = {
        'directory'           : Type.STRING,
        'encoding'            : Type.STRING,
        'fallback_encodings'  : Type.STRING_LIST,
        'format'              : Type.CONSTANT,
        'maximum_recent_files': Type.INTEGER,
        'newlines'            : Type.CONSTANT,
        'recent_files'        : Type.STRING_LIST,
        'try_locale_encoding' : Type.BOOLEAN,
        'visible_encodings'   : Type.STRING_LIST
    }

    classes = {
        'format'  : Format,
        'newlines': Newlines,
    }

class general(object):

    editor  = 'gvim'
    version = __version__

    types = {
        'editor' : Type.STRING,
        'version': Type.STRING,
    }

class subtitle_insert(object):

    amount   = 1
    position = Position.BELOW

    types = {
        'amount'  : Type.INTEGER,
        'position': Type.CONSTANT,
    }

    classes = {
        'position': Position,
    }

class spell_check(object):

    check_all_projects   = False
    check_text           = True
    check_translation    = False
    text_language        = None
    translation_language = None

    types = {
        'check_all_projects'  : Type.BOOLEAN,
        'check_text'          : Type.BOOLEAN,
        'check_translation'   : Type.BOOLEAN,
        'text_language'       : Type.STRING,
        'translation_language': Type.STRING,
    }

class spell_check_dialog(object):

    size = [460, 410]

    types = {
        'size': Type.INTEGER_LIST,
    }


def _get_boolean(arg):
    """
    Get boolean from string or string from boolean.

    Raise ValueError if arg not convertable.
    """
    booleans = [ True ,  False ]
    strings  = ['true', 'false']

    if isinstance(arg, basestring):
        return booleans[strings.index(arg)]
    elif isinstance(arg, bool):
        return strings[booleans.index(arg)]
    else:
        raise ValueError('Wrong argument type: %s.' % type(arg))

def _get_constant(section, option, arg):
    """
    Get constant from string or string from constant.

    Raise AttributeError if some attribute not found.
    Raise ValueError if arg not convertable.
    """
    constant_class = eval(section).classes[option]

    if isinstance(arg, basestring):
        return constant_class.id_names.index(arg)
    elif isinstance(arg, int):
        return constant_class.id_names[arg]
    else:
        raise ValueError('Wrong argument type: %s.' % type(arg))

def get_options(section):
    """Get a list of all options in section."""

    options = []

    for name in dir(eval(section)):
        if not name.startswith('_') and not name in ('types', 'classes'):
            options.append(name)

    return options

def get_sections():
    """Get a list of sections."""

    return sections

def read():
    """Read and parse settings from file."""

    parser = ConfigParser.RawConfigParser()

    # Read from file.
    result = parser.read([CONFIG_PATH])
    if not result:
        msg  = 'Failed to read settings from file "%s".' % CONFIG_PATH
        msg += ' Using default settings.'
        logger.info(msg)

    # Set config options.
    sections = parser.sections()
    for section in sections:

        options = parser.options(section)
        for option in options:

            try:
                _set_config_option(parser, section, option)
            except Exception:
                path = section, option
                msg = 'Failed to load setting %s.%s.' % path
                logger.error(msg)

    # Set version to current version.
    general.version = __version__

def _set_config_option(parser, section, option):
    """
    Set value of config option from parser string.

    Raise Exception if something goes wrong.
    """
    string = parser.get(section, option)
    typ    = eval(section).types[option]

    # Convert string to proper data type.
    if string == '':
        if Type.is_list(typ):
            value = []
        else:
            value = None

    elif typ == Type.STRING:
        value = string

    elif typ == Type.INTEGER:
        value = int(string)

    elif typ == Type.BOOLEAN:
        value = _get_boolean(string)

    elif typ == Type.CONSTANT:
        value = _get_constant(section, option, string)

    elif typ == Type.STRING_LIST:
        value = string.split('|')

    elif typ == Type.INTEGER_LIST:
        str_list = string.split('|')
        value = [int(entry) for entry in str_list]

    elif typ == Type.BOOLEAN_LIST:
        str_list = string.split('|')
        value = [_get_boolean(entry) for entry in str_list]

    elif typ == Type.CONSTANT_LIST:
        str_list = string.split('|')
        value = [_get_constant(section, option, entry) for entry in str_list]

    setattr(eval(section), option, value)

def _set_parser_option(parser, section, option):
    """
    Set value of parser string from config option.

    Raise Exception if something goes wrong.
    """
    value = eval('%s.%s' % (section, option))
    typ   = eval(section).types[option]

    # Convert data type to string.
    if value == None:
        string = ''

    elif typ == Type.STRING:
        string = value

    elif typ == Type.INTEGER:
        string = str(value)

    elif typ == Type.BOOLEAN:
        string = _get_boolean(value)

    elif typ == Type.CONSTANT:
        string = _get_constant(section, option, value)

    elif typ == Type.STRING_LIST:
        string = '|'.join(value)

    elif typ == Type.INTEGER_LIST:
        str_list = [str(entry) for entry in value]
        string = '|'.join(str_list)

    elif typ == Type.BOOLEAN_LIST:
        str_list = [_get_boolean(entry) for entry in value]
        string = '|'.join(str_list)

    elif typ == Type.CONSTANT_LIST:
        str_list = [_get_constant(section, option, entry) for entry in value]
        string = '|'.join(str_list)

    # Set value.
    parser.set(section, option, string)

def write():
    """Assemble and write settings to file."""

    parser = ConfigParser.RawConfigParser()

    # Set parser options.
    sections = get_sections()
    for section in sections:
        parser.add_section(section)

        options = get_options(section)
        for option in options:

            try:
                _set_parser_option(parser, section, option)
            except Exception:
                path = section, option
                msg = 'Failed to write setting %s.%s.' % path
                logger.error(msg)

    # Create directory ~/.gaupol if it doesn't exist.
    if not os.path.isdir(CONFIG_DIR):
        try:
            os.makedirs(CONFIG_DIR)
        except OSError, detail:
            info = CONFIG_DIR, detail
            msg = 'Failed to create profile directory "%s": %s.' % info
            logger.error(msg)

    try:

        # Write header.
        config_file = open(CONFIG_PATH, 'w')
        try:
            config_file.write(CONFIG_HEADER)
        finally:
            config_file.close()

        # Write settings.
        config_file = open(CONFIG_PATH, 'a')
        try:
            parser.write(config_file)
        finally:
            config_file.close()

    except IOError, (errno, detail):
        info = CONFIG_PATH, detail
        msg = 'Failed to write settings to file "%s": %s.' % info
        logger.error(msg)
