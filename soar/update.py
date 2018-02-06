# Soar (Snakes on a Robot): A Python robotics framework.
# Copyright (C) 2017 Andrew Antonitis. Licensed under the LGPLv3.
#
# soar/update.py
""" Function to check for updates on PyPI, and return a message for the user. """
import re
from urllib import request

from soar import __version__


PYPI_URL = 'https://pypi.python.org/pypi/Soar'  # This may change in the future
INF = float('inf')  # Use older infinity so as not to require Python 3.5


def get_update_message():
    """ Fetch the HTML of Soar's PyPI page, check for a newer version, and return a notification string.

    Returns:
        str: An empty string if no update is available, a notification message if one is, and an error
    message if something went wrong.
    """
    # Try and determine if a newer version of Soar is available, and notify the user
    try:
        r = request.urlopen(PYPI_URL, data=None)
        assert(r.getcode() == 200)
        body = str(r.read(), encoding='utf-8')
        start = body.find('Soar')
        assert (start != -1)
        # Capture groups are Major, minor, patch, and optional .devN
        match_version = re.compile('(\d)\.(\d)\.(\d)(?:\.dev(\d))?')

        def version_parse(x):  # Parse version increment strings into integers
            if x is None:
                return INF  # Non-development releases have an effective development release value of infinity
            else:
                return int(x)

        pypi_version = list(map(version_parse, match_version.search(body, start).group(1, 2, 3, 4)))
        current_version = list(map(version_parse, match_version.search(__version__).group(1, 2, 3, 4)))
        need_update = False
        for pypi_inc, current_inc in zip(pypi_version, current_version):
            if pypi_inc > current_inc:  # If any PyPI version increment is greater, we need to update
                need_update = True
                break
            elif pypi_inc < current_inc:  # If any current version increment is greater, we do not need to update
                need_update = False
                break
        if need_update:
            if pypi_version[3] != INF:
                pypi_version[3] = 'dev' + str(pypi_version[3])
            else:
                pypi_version = pypi_version[:-1]  # Slice off the irrelevant infinite dev version
            version_string = '.'.join([str(x) for x in pypi_version])
            return 'A newer version of Soar is available: v' + version_string + '\nPlease update your installation.'
        else:
            return ''
    except Exception:  # If anything at all goes wrong, notify the user
        return 'Unable to check for updates.'
