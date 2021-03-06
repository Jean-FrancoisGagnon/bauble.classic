#
# provide paths that bauble will need
#
"""
Access to standard paths used by Bauble.
"""
import os
import sys

# TODO: we could just have setup or whatever create a file in the lib
# directory that tells us where all the other directories are but this
# would make the program non-relocatable whereas this approach allows
# us to be more dynamic about it...except that where it doesn't work,
# e.g. if the locale files are installed anywhere except
# /usr/share/locale...the other side of the coin is just make this the
# packagers problem, i.e make the packagers patch this file although
# this kinds sucks b/c it just pushes the problem onto someone else,
# it also doesn't really solve things like virtualenv installs

def main_is_frozen():
    """
    Returns True/False if Bauble is being run from a py2exe
    executable.  This method duplicates bauble.main_is_frozen in order
    to make paths.py not depend on any other Bauble modules.
    """
    import imp
    return (hasattr(sys, "frozen") or # new py2exe
            hasattr(sys, "importers") or # old py2exe
            imp.is_frozen("__main__")) # tools/freeze


def main_dir():
    """
    Returns the path of the bauble executable.
    """
    if main_is_frozen():
        d = os.path.dirname(sys.executable)
    else:
        d = os.path.dirname(sys.argv[0])
    if d == "":
        d = os.curdir
    return os.path.abspath(d)


def lib_dir():
    """
    Returns the path of the bauble module.
    """
    if main_is_frozen():
        d = os.path.join(main_dir(), 'bauble')
    else:
        d = os.path.dirname(__file__)
    return os.path.abspath(d)


# def data_dir():
#     """
#     Return the data directory.  The data directory should contain any
#     files required by Bauble or its plugins but aren't code.
#     e.g. image, pixmaps

#     Windows = main_dir()
#     Linux = /usr/share/bauble

#     images = data_dir()/images
#     glade = data_dir()/glade
#     """
#     if sys.platform == 'linux2':
#         base = os.path.dirname(os.path.dirname(main_dir()))
#         return os.path.join(base, 'share', 'bauble')
#     elif sys.platform == 'win32':
#         return os.path.join(main_dir(), 'share')
#     else:
#         raise NotImplementedError('Unknown platform: %s' % sys.platform)


def locale_dir():
    """
    Returns the root path of the locale files
    """
    if sys.platform == 'linux2':
        # TODO: how do we get the locale directory for linux?
        d = os.path.join('/usr', 'share', 'locale')
    elif sys.platform == 'win32':
        d = os.path.join(main_dir(), 'share', 'locale')
    else:
        raise NotImplementedError('This platform does not support '\
                                  'translations: %s' % sys.platform)
    return os.path.abspath(d)


def user_dir():
    """
    Returns the path to where Bauble settings should be saved.
    """
    if sys.platform == "win32":
        if 'APPDATA' in os.environ:
            d = os.path.join(os.environ["APPDATA"], "Bauble")
        elif 'USERPROFILE' in os.environ:
            d = os.path.join(os.environ['USERPROFILE'], 'Application Data',
                               'Bauble')
        else:
            raise Exception(_('Could not get path for user settings: no ' \
                              'APPDATA or USERPROFILE variable'))
    elif sys.platform == "linux2":
        # using os.expanduser is more reliable than os.environ['HOME']
        # because if the user runs bauble with sudo then it will
        # return the path of the user that used sudo instead of ~root
        try:
            d = os.path.join(os.path.expanduser('~%s' % os.environ['USER']),
                             '.bauble')
        except Exception:
            raise Exception(_('Could not get path for user settings: '\
                              'could not expand $HOME for user %(username)s' %\
                              dict(username=os.environ['USER'])))
    else:
        raise Exception(_('Could not get path for user settings: '\
                          'unsupported platform'))
    return os.path.abspath(d)


if __name__ == '__main__':
    print 'main: %s' % main_dir()
    print 'lib: %s' % lib_dir()
    print 'locale: %s' % locale_dir()
    print 'user: %s' % user_dir()
