
# plugins, tables, editors and views should inherit from
# the appropriate classes

# TODO: how do we access tables should it be 
# plugins[plugin_name].tables[table_name], that's pretty long
# or access all tables like plugins.tables[table_name] and be able 
# to retrieve the module name from the table

# TODO: need to consider 
# first initialization so we know whether to add joins to table, this 
# might mean we have to keep a cache of what has been initialized and what
# hasn't, or possibly just create a .initialized file in the module 
# directory to indicate that the plugin has been intialized, though this 
# means we would have to have write permission to the plugin directory 
# which could be problematic, a file with a list of initialized plugins 
# would be best i reckon and then we can just grep the file for the plugin
# name

# TODO: what about tools, should they be separate or a plugin, i think
# a plugin should be fine, what differentiates a tool from a plugin
# other than the tools menu, as long as the plugin defines a tools
# list for what tools it provides then that should be enough, should
# also consider a tools_category so we cant create a rational menu
# layout for tools

# TODO: we could just have a provides=[] list instead of a different
# list for each of tables, editors, blah, blah, then we could just
# test the parent class of what it provides to know what to do with 
# it, this might be getting too abstract, and since we will want to
# access thing like plugins.tables[table_name] then stick with 
# module level list of tables may make more sense

# TODO: a plugin cannot change a table but can add joins to a table not
# in its plugin module  throught the sqlmeta.addJoin method

#accessions = MultipleJoin('Accessions', joinColumn='plantname_id')
#joins = {'accessions': (table.Plantname, table.Accession, 'plantname_id')}

# TODO: if a plugin is removed then a dialog should be popped
# up to ask if you want to remove the joins

import os, sys, traceback
import gtk
from sqlobject import SQLObject, sqlmeta
import bauble.utils as utils

plugins = {}
views = {}
tools = {}
editors = {}
tables = {}

            
def init_plugins():
    """
    initialized all the plugins in plugins
    """    
    for p in plugins.values():
        p.init()
    
    
def _register(plugin_class):
        
    # check dependencies
    plugin_name = plugin_class.__name__
    print "registering ", plugin_name
    for dependency in plugin_class.depends:            
        #print 'depends: ', dependency
        if dependency not in plugins:
            msg = "Can't load plugin %s. This plugin depends on %s but "\
                  "%s doesn't exist" %(plugin_name, dependency, dependency)
            utils.message_dialog(msg, gtk.MESSAGE_ERROR)
            return
    plugins[plugin_name] = plugin_class
    
    # add tables
    for t in plugin_class.tables:
        #print 'adding table: ', t.__name__            
        tables[t.__name__] = t
    
    # add editors
    for e in plugin_class.editors:
        editors[e.__name__] = e
    
    # add views
    for v in plugin_class.views:
        views[v.__name__] = v
    
    # add tools
    for t in plugin_class.tools:    
        tools[t.__name__] = t


def _find_plugins():
    modules = []
    path, name = os.path.split(__file__)
    if path.find("library.zip") != -1: # using py2exe
        pkg = "views"
        zipfiles = __import__(pkg, globals(), locals(), [pkg]).__loader__._files 
        x = [zipfiles[file][0] for file in zipfiles.keys() if pkg in file]
        s = '.+?' + os.sep + pkg + os.sep + '(.+?)' + os.sep + '__init__.py[oc]'
        rx = re.compile(s.encode('string_escape'))
        for filename in x:
            m = rx.match(filename)
            if m is not None:
                modules.append('%s.%s' % (pkg, m.group(1)))
    else:                
        for d in os.listdir(path):
            full = path + os.sep + d                
            if os.path.isdir(full) and os.path.exists(full + os.sep + "__init__.py"):
                #modules.append("plugins." + d)
                modules.append(d)
                
    # import the modules and test if they provide a plugin to make sure 
    # they are plugin modules
    plugins = []
    for m in modules:
        try:
            mod = __import__(m, globals(), locals(), ['plugins'])
        except Exception, e:
            t, v, tb = sys.exc_info()
            msg = "** Error: could not import module %s\n\n%s" % \
                (m, traceback.format_exc())
            utils.message_dialog(msg, gtk.MESSAGE_ERROR)
            continue
        if hasattr(mod, "plugin"):                 
            plugins.append(mod.plugin)
    return plugins

def load():
    # accumulate all the plugins in the module, call the register methods
    # once the plugins have been found
    found = _find_plugins()
    for p in found:        
        plugins[p.__name__] = p
    #print plugins
    for p in plugins.values():
        p.register()  


# TODO: use this as the metaclass for BaublePlugin to automatically make
# any methods called init() to be classmethods
class BaublePluginMeta(object):
    
    def __init__(self):
        """
        should use this as 
        """
        pass
        
        
class BaublePlugin(object):
    tables = []
    editors = []
    views = []
    tools = []
    depends = []

    def __init__(cls):
        pass
    __init__ = classmethod(__init__)
    
    def init(cls):
        pass
    init = classmethod(init)

    def register(cls):
        _register(cls)
    register = classmethod(register)
    
    # NOTE: maybe create_tables should be a plugin method or a method
    # global to this module that way we can create things in order depending
    # on the plugin dependencies
    def create_tables(cls):
        for t in cls.tables:
            print "creating table ", t.__name__
            t.dropTable(ifExists=True, cascade=True)            
            t.createTable()
    create_tables = classmethod(create_tables)
    

    def _post_create_tables(cls):
        """
        called after all the tables are created for all plugins, useful
        for doing things like installing joins
        """
        pass
    _post_create_tables = classmethod(_post_create_tables)
        
    

class BaubleTable(SQLObject):        
    sqlmeta.cacheValues = False
    
    def __init__(self, **kw):
        super(BaubleTable, self).__init__(**kw)
        self.values = {}

    
class BaubleEditor(object):
    pass

        
class BaubleView(gtk.Frame):
    
    def __init__(self, *args, **kwargs):
        super(BaubleView, self).__init__(self, *args, **kwargs)
        self.set_label('')
        self.set_shadow_type(gtk.SHADOW_NONE)


class BaubleTool(object):
    category = None
    label = None
    
    def start(cls):
        pass
    start = classmethod(start)
    
def init_module():
    load()
init_module()
#plugins()
#plugins.init()
    