from urllib import request

from soar import __version__


def get_update_message():
    # Try and determine if a newer version of Soar is available, and notify the user
    try:
        r = request.urlopen('https://pypi.python.org/pypi/Soar', data=None)
        assert(r.getcode() == 200)
        body = str(r.read(), encoding='utf-8')
        start = body.find('Soar')
        assert(start != -1)
        end = body.find(':', start)
        assert(end != -1)
        version_string = body[start+5:end-1]
        version = [int(s) for s in version_string.split('.')]
        current_version = [int(s) for s in __version__.split('.')]
        assert(len(version) == len(current_version) == 3)
        need_update = False
        for new_inc, inc in zip(version, current_version):
            if new_inc > inc:
                need_update = True
                break
        if need_update:
            return 'A newer version of Soar is available: v' + version_string + '\nPlease update your installation.'
        else:
            return ''
    except Exception:  # If anything at all goes wrong, silently fail
        return ''
