#
# pluginmgr.py
#

"""
Manage plugin registry, loading, initialization and installation.  The plugin manager should be started in the following order:

1. load the plugins: search the plugin directory for plugins,
populates the plugins dict (happens in load())

2. install the plugins if not in the registry, add properly
installed plugins in to the registry (happens in load())

3. initialize the plugins (happens in init())
"""

import types
import os
import re
import sys
import traceback

import gtk
from sqlalchemy import *
from sqlalchemy.orm import *
import sqlalchemy.orm.exc as orm_exc

import bauble
import bauble.db as db
from bauble.error import BaubleError
import bauble.paths as paths
import bauble.utils as utils
from bauble.utils.log import debug, warning, error

# TODO: should make plugins and ordered dict that is sorted by
# dependency, maybe use odict from
# http://www.voidspace.org.uk/python/odict.html...or we could just
# have function called dependency_sort or something that returns the
# plugins sorted by dependency

plugins = {}
commands = {}


def register_command(handler):
    """
    Register command handlers.  If a command is a duplicate then it
    will overwrite the old command of the same name.

    :param handler:  A class which extends pluginmgr.CommandHandler
    """
    global commands
    if isinstance(handler.command, str):
        #if handler.command in commands:
        #    raise ValueError(_('%s already registered' % handler.command))
        commands[handler.command] = handler
    else:
        for cmd in handler.command:
            #if cmd in commands:
            #    raise ValueError(_('%s already registered' % cmd))
            commands[cmd] = handler


def _check_dependencies(plugin):
    '''
    Check the dependencies of plugin
    '''


def _create_dependency_pairs(plugs):
    """
    Returns a tuple.  The first item in the tuple is the dependency
    pairs that can be passed to topological sort.  The second item is
    a dictionary whose keys are plugin names and value are a list of
    unmet dependencies.
    """
    depends = []
    unmet = {}
    for p in plugs:
        for dep in p.depends:
            try:
                depends.append((plugins[dep], p))
            except KeyError:
                debug('no dependency %s for %s' % (dep, p.__name__))
                u = unmet.setdefault(p.__name__, [])
                u.append(dep)
    return depends, unmet


def load(path=None):
    """
    Search the plugin path for modules that provide a plugin. If path
    is a directory then search the directory for plugins. If path is
    None then use the default plugins path, bauble.plugins.

    This method populates the pluginmgr.plugins dict and imports the
    plugins but doesn't do any plugin initialization.

    :param path: the path where to look for the plugins
    :type path: str
    """
    if path is None:
        if bauble.main_is_frozen():
            #path = os.path.join(paths.lib_dir(), 'library.zip')
            path = os.path.join(paths.main_dir(), 'library.zip')
        else:
            path = os.path.join(paths.lib_dir(), 'plugins')
    found, errors = _find_plugins(path)

    # show error dialog for plugins that couldn't be loaded...we only
    # give details for the first error and assume the others are the
    # same...and if not then it doesn't really help anyways
    if errors:
        name = ', '.join(sorted(errors.keys()))
        exc_info = errors.values()[0]
        exc_str = utils.xml_safe_utf8(exc_info[1])
        tb_str = ''.join(traceback.format_tb(exc_info[2]))
        utils.message_details_dialog('Could not load plugin: '
                                     '\n\n<i>%s</i>\n\n%s' \
                                         % (name, exc_str),
                                     tb_str, type=gtk.MESSAGE_ERROR)

    if len(found) == 0:
        debug('No plugins found at path: %s' % path)

    for plugin in found:
        # TODO: should we include the module name of the plugin to allow
        # for plugin namespaces or just assume that the plugin class
        # name is unique
        plugins[plugin.__class__.__name__] = plugin



def init(force=False):
    """
    Initialize the plugin manager.

    1. Check for and install any plugins in the plugins dict that
    aren't in the registry.
    2. Call each init() for each plugin the registry in order of dependency
    3. Register the command handlers in the plugin's commands[]

    NOTE: This should be called after after Bauble has established a
    connection to a database with db.open()
    """
    #debug('bauble.pluginmgr.init()')
    # ******
    # NOTE: Be careful not to keep any references to
    # PluginRegistry open here as it will cause a deadlock if you try
    # to create a new database. For example, don't query the
    # PluginRegistry with a session without closing the session.
    # ******

    # search for plugins that are in the plugins dict but not in the registry
    registered = plugins.values()
    try:
        # try to access the plugin registry, if the tables does not
        # exists then it might mean that we are opening a pre 0.9
        # database, in this case we just assume all the plugins have
        # been installed and registered, this might be the right thing
        # to do but it least it allows you to connect to a pre bauble 0.9
        # database and use it to upgrade to a >=0.9 database
        registered_names = PluginRegistry.names()
        not_installed = [p for n,p in plugins.iteritems() \
                             if n not in registered_names]
        if len(not_installed) > 0:
            msg = _('The following plugins were not found in the plugin '\
                        'registry:\n\n<b>%s</b>\n\n'\
                        '<i>Would you like to install them now?</i>' \
                        % ', '.join([p.__class__.__name__ for p in not_installed]))
            if force or utils.yes_no_dialog(msg):
                install([p for p in not_installed])

        # sort plugins in the registry by their dependencies
        not_registered = []
        for name in PluginRegistry.names():
            try:
                registered.append(plugins[name])
            except KeyError, e:
                not_registered.append(utils.utf8(name))

        if not_registered:
            msg = _('The following plugins are in the registry but '
                    'could not be loaded:\n\n%(plugins)s' % \
                    {'plugins': utils.utf8(', '.join(sorted(not_registered)))})
            utils.message_dialog(utils.xml_safe(msg), type=gtk.MESSAGE_WARNING)

    except Exception, e:
        raise

    if not registered:
        # no plugins to initialize
        return

    deps, unmet = _create_dependency_pairs(registered)
    ordered = utils.topological_sort(registered, deps)
    if not ordered:
        raise BaubleError(_('The plugins contain a dependency loop. This '\
                                'can happen if two plugins directly or '\
                                'indirectly rely on each other'))

    # call init() for each ofthe plugins
    for plugin in ordered:
        #debug('init: %s' % plugin)
        try:
            plugin.init()
        except KeyError, e:
            # don't remove the plugin from the registry because if we
            # find it again the user might decide to reinstall it
            # which could overwrite data
            ordered.remove(plugin)
            msg = _("The %(plugin_name)s plugin is listed in the registry "\
                    "but isn't wasn't found in the plugin directory") \
                    % dict(plugin_name=plugin.__class__.__name__)
            warning(msg)
        except Exception, e:
            #error(e)
            ordered.remove(plugin)
            error(traceback.print_exc())
            safe = utils.xml_safe_utf8
            values = dict(entry_name=plugin.__class__.__name__, exception=safe(e))
            utils.message_details_dialog(_("Error: Couldn't initialize "\
                                           "%(entry_name)s\n\n" \
                                           "%(exception)s." % values),
                                         traceback.format_exc(),
                                         gtk.MESSAGE_ERROR)


    # register the plugin commands seperately from the plugin initialization
    for plugin in ordered:
        if plugin.commands in (None, []):
            continue
        for cmd in plugin.commands:
            try:
                register_command(cmd)
            except Exception, e:
                msg = 'Error: Could not register command handler.\n\n%s' % \
                      utils.xml_safe(str(e))
                utils.message_dialog(msg, gtk.MESSAGE_ERROR)

    # don't build the tools menu if we're running from the tests and
    # we don't have a gui
    if bauble.gui:
        bauble.gui.build_tools_menu()



def install(plugins_to_install, import_defaults=True, force=False):
    """
    :param plugins_to_install: A list of plugins to install. If the
        string "all" is passed then install all plugins listed in the
        bauble.pluginmgr.plugins dict that aren't already listed in
        the plugin registry.

    :param import_defaults: Flag passed to the plugin's install()
        method to indicate whether it should import its default data.
    :type import_defaults: bool

    :param force:  Force, don't ask questions.
    :type force: book
    """
    #debug('pluginmgr.install(%s)' % plugins_to_install)
    if plugins_to_install is 'all':
        to_install = plugins.values()
    else:
        to_install = plugins_to_install

    if len(to_install) == 0:
        # no plugins to install
        return

    # sort the plugins by their dependency
    depends, unmet = _create_dependency_pairs(to_install)
    if unmet != {}:
        debug(unmet)
        raise BaubleError('unmet dependencies')
    to_install = utils.topological_sort(to_install, depends)
    if not to_install:
        raise BaubleError(_('The plugins contain a dependency loop. This '\
                            'can happend if two plugins directly or '\
                            'indirectly rely on each other'))

#         msg = _('The %(plugin)s plugin depends on the %(other_plugin)s '\
#                 'plugin but the %(other_plugin)s plugin wasn\'t found.') \
#                 % {'plugin': e.plugin.__name__, 'other_plugin': e.not_found}
#         utils.message_dialog(msg, gtk.MESSAGE_WARNING)

#         to_install = topological_sort(to_install, depends)
#     except DependencyError, e:
#         msg = _('The %(plugin)s plugin depends on the %(other_plugin)s '\
#                 'plugin but the %(other_plugin)s plugin wasn\'t found.') \
#                 % {'plugin': e.plugin.__name__, 'other_plugin': e.not_found}
#         utils.message_dialog(msg, gtk.MESSAGE_WARNING)
#         raise
#     except DependencyError, e:
#         error(utils.utf8(e))

    try:
        for p in to_install:
            #debug('install: %s' % p.__name__)
            p.install(import_defaults=import_defaults)
            # TODO: here we make sure we don't add the plugin to the
            # registry twice but we should really update the version
            # number in the future when we accept versioned plugins
            # (if ever)
            if not PluginRegistry.exists(p):
                PluginRegistry.add(p)
        #session.commit()
    except Exception, e:
        warning('bauble.pluginmgr.install(): %s' % utils.utf8(e))
        raise
#         msg = _('Error installing plugins: %s' % p)
#         debug(e)
#         #safe = utils.xml_safe_utf8
#         #utils.message_details_dialog(safe(msg),
#         #                             safe(traceback.format_exc()),
#         #                             gtk.MESSAGE_ERROR)
#         debug(traceback.format_exc())



class PluginRegistry(db.Base):
    """
    The PluginRegistry contains a list of plugins that have been installed
    in a particular instance of a Bauble database.  At the moment it only
    includes the name and version of the plugin but this is likely to change
    in future versions.
    """
    __tablename__ = 'plugin'
    name = Column(Unicode(64), unique=True)
    version = Column(Unicode(12))

    @staticmethod
    def add(plugin):
        """
        Add a plugin to the registry.

        Warning: Adding a plugin to the registry does not install it.  It
        should be installed before adding.
        """
        p = PluginRegistry(name=utils.utf8(plugin.__class__.__name__),
                           version=utils.utf8(plugin.version))
        session = db.Session()
        session.add(p)
        session.commit()
        session.close()


    @staticmethod
    def remove(plugin):
        """
        Remove a plugin from the registry by name.
        """
        #debug('PluginRegistry.remove()')
        session = db.Session()
        p = session.query(PluginRegistry).\
            filter_by(name=utils.utf8(plugin.__class__.__name__)).one()
        session.delete(p)
        session.commit()
        session.close()


    @staticmethod
    def all(session):
        close_session = False
        if not session:
            close_session = True
            session = db.Session()
        q = session.query(PluginRegistry)
        results = list(q)
        if close_session:
            session.close()
        return results


    @staticmethod
    def names(bind=None):
        t = PluginRegistry.__table__
        results = select([t.c.name], bind=bind).execute(bind=bind)
        names = [n[0] for n in results]
        results.close()
        return names


    @staticmethod
    def exists(plugin):
        """
        Check if plugin exists in the plugin registry.
        """
        if isinstance(plugin, basestring):
            name = plugin
            version = None
        else:
            name = plugin.__class__.__name__
            version = plugin.version
        session = db.Session()
        try:
            session.query(PluginRegistry).\
                filter_by(name=utils.utf8(name)).one()
            return True
        except orm_exc.NoResultFound, e:
            return False
        finally:
            session.close()



class Plugin(object):
    """
    tools:
      a list of BaubleTool classes that this plugin provides, the
      tools' category and label will be used in Bauble's "Tool" menu
    depends:
      a list of names classes that inherit from BaublePlugin that this
      plugin depends on
    cmds:
      a map of commands this plugin handled with callbacks,
      e.g dict('cmd', lambda x: handler)
    description:
      a short description of the plugin
    """
    commands = []
    tools = []
    depends = []
    description = ''
    version = '0.0'

    @classmethod
    def __init__(cls):
        pass

    @classmethod
    def init(cls):
        '''
        init() is run when Bauble is first started
        '''
        pass

    @classmethod
    def install(cls, import_defaults=True):
        '''
        install() is run when a new plugin is installed, it is usually
        only run once for the lifetime of the plugin
        '''
        pass



class EditorPlugin(Plugin):
    '''
    a plugin that provides one or more editors, the editors should
    implement the Editor interface
    '''
    editors = []


class Tool(object):
    category = None
    label = None
    enabled = True
    @classmethod
    def start(cls):
        pass


class View(gtk.VBox):

    def __init__(self, *args, **kwargs):
        """
        If a class extends this View and provides it's own __init__ it *must*
        call it's parent (this) __init__
        """
        super(View, self).__init__(*args, **kwargs)


class CommandHandler(object):

    command = None

    def get_view(self):
        '''
        return the  view for this command handler
        '''
        return None

    def __call__(self, cmd, arg):
        '''
        do what this command handler does

        :param arg:
        '''
        raise NotImplementedError


def _find_module_names(path):
    '''
    :param path: where to look for modules
    '''
    modules = []
    if path.find("library.zip") != -1: # using py2exe
        from zipfile import ZipFile
        z = ZipFile(path)
        filenames = z.namelist()
        rx = re.compile('(.+)\\__init__.py[oc]')
        for f in filenames:
            m = rx.match(f)
            if m is not None:
                modules.append(m.group(1).replace('/', '.')[:-1])
        z.close()
    else:
        for dir, subdir, files in os.walk(path):
            if dir != path and '__init__.py' in files:
                modules.append(dir[len(path)+1:].replace(os.sep,'.'))
    return modules


def _find_plugins(path):
    """
    Return the plugins at path.
    """
    plugins = []
    import bauble.plugins
    plugin_module = bauble.plugins
    errors = {}

    if path.find('library.zip') != -1:
        plugin_names = [m for m in _find_module_names(path) \
                        if m.startswith('bauble.plugins')]
    else:
        plugin_names =['bauble.plugins.%s'%m for m in _find_module_names(path)]

    for name in plugin_names:
        mod = None
        # Fast path: see if the module has already been imported.

        if name in sys.modules:
            mod = sys.modules[name]
        else:
            try:
                mod = __import__(name, globals(), locals(), [name], -1)
            except Exception, e:
                msg = _('Could not import the %(module)s module.\n\n'\
                        '%(error)s' % {'module': name, 'error': e})
                debug(msg)
                errors[name] = sys.exc_info()
        if not hasattr(mod, "plugin"):
            continue

        # if mod.plugin is a function it should return a plugin or list of
        # plugins
        try:
            mod_plugin = mod.plugin()
        except:
            mod_plugin = mod.plugin

        is_plugin = lambda p: isinstance(p, (type, types.ClassType)) and issubclass(p, Plugin)
        if isinstance(mod_plugin, (list, tuple)):
            for p in mod_plugin:
                if is_plugin(p) or True:
                    plugins.append(p)
        elif is_plugin(mod_plugin) or True:
            plugins.append(mod_plugin)
        else:
            warning(_('%s.plugin is not an instance of pluginmgr.Plugin'\
                      % mod.__name__))
    return plugins, errors
