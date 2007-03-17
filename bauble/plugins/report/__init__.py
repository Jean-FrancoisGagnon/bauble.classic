#
# report module
#

# TODO: all these  names are getting confusing, we should probably 
# rename the top level module to 'report' or something and report plugins
# could then be called 'formatters'

# TODO: need to make it so formatter plugins work if they are zipped up

import os, sys, traceback, re
import gtk
from sqlalchemy import *
import lxml.etree as etree
import lxml._elementpath # put this here sp py2exe picks it up
import bauble
from bauble.i18n import *
import bauble.utils as utils
import bauble.paths as paths
from bauble.prefs import prefs
import bauble.pluginmgr as pluginmgr
from bauble.utils.log import log, debug

# name: formatter_class, formatter_kwargs
config_list_pref = 'report.configs'

#report_modules_pref = 'report.modules'

# the default report generator to select on start
default_config_pref = 'report.default' 
formatter_settings_expanded_pref = 'report.settings.expanded'


def get_all_plants(objs, acc_status=('Living accession',None)):
    from bauble.plugins.garden.plant import Plant, plant_table
    all_plants = {}
    session = create_session()
    plant_query = session.query(Plant)
    
    def add_plants(plants):
        for p in plants:
            if id not in all_plants and p.acc_status in acc_status:
                all_plants[p.id] = p
    
    def add_plants_from_accessions(accessions):
        '''
        add all plants from all accessions
        '''
#        genus_ids = select([genus_table.c.id], genus_table.c.genus.like('%s%%' % text))
#        sql = species_table.select(species_table.c.genus_id.in_(genus_ids))
#        return self.session.query(Species).select(sql) 
        if False:
            # TODO: i don't know why this doesn't work, tried with SA 2.8
#            debug(accessions)
            acc_ids = [acc.id for acc in accessions]
#            debug(acc_ids)
            #plants = plant_query.select(Plant.c.id.in_(acc_ids))
#            debug(plant_table.c.id.in_(acc_ids))
            stmt = plant_table.select(plant_table.c.id.in_(acc_ids))
            plants = plant_query.select(stmt)
#            debug(plants)
            add_plants(p)
        else:            
            for p in [acc.plants for acc in accessions]:        
                add_plants(p)

    # append the objects from the tag
    try:
        from bauble.plugins.tag import Tag
        
        for obj in objs:        
            if isinstance(obj, Tag):
                objs.extend(obj.objects)
    except ImportError:
        pass
##        if isinstance(obj, global_metadata.tables['Tag']):        
##           objs.extend(obj.objects)

    # TODO: it would be better if getting the plants from the different
    # types wasn't hardcoded in here, it would be better if we could
    # just register a type and how to get that types children similar to the
    # view meta or at least something along those lines
    from bauble.plugins.plants import Family, Genus, Species
    from bauble.plugins.garden import Accession, Plant, Location
    for obj in objs:        
        # extract the plants from the search results
        # TODO: need to speed this up using custom queries, see the 
        # family and genera infoboxes
        debug('obj: %s' % obj)
        if isinstance(obj, Family):
            for gen in obj.genera:
                for sp in gen.species:
                    add_plants_from_accessions(sp.accessions)
        elif isinstance(obj, Genus):
            for sp in obj.species:
                add_plants_from_accessions(sp.accessions)
        elif isinstance(obj, Species):
            add_plants_from_accessions(obj.accessions)            
        elif isinstance(obj, Accession):
#            debug(obj.plants)
            add_plants(obj.plants)
        elif isinstance(obj, Plant):
            add_plants([obj])
        elif isinstance(obj, Location):
            add_plants(obj.plants)
        
    return all_plants.values()



## def _find_formatter_plugins():
##     # TODO: the library.zip part doesn't work
##     names = []
##     path, name = os.path.split(__file__)
##     if path.find("library.zip") != -1: # using py2exe
##         pkg = "bauble.plugins.formatter"
##         zipfiles = __import__(pkg, globals(), locals(), [pkg]).__loader__._files 
##         x = [zipfiles[file][0] for file in zipfiles.keys() if "bauble\\plugins\\formatter" in file]
##         s = '.+?' + os.sep + pkg + os.sep + '(.+?)' + os.sep + '__init__.py[oc]'
##         rx = re.compile(s.encode('string_escape'))
##         for filename in x:
##             m = rx.match(filename)
##             if m is not None:
##                 names.append('%s.%s' % (pkg, m.group(1)))
##     else:
##         for d in os.listdir(path):
##             full = path + os.sep + d
##             if os.path.isdir(full) and os.path.exists(full + os.sep + "__init__.py"):
##                 names.append(d)
                
##     plugins = []
##     for name in names:
##         try:
##             mod = __import__(name, globals(), locals(), ['formatter'])
##         except Exception, e:
##             msg = "Could not import the %s module." % name
##             utils.message_details_dialog(msg, str(traceback.format_exc()), 
##                      gtk.MESSAGE_ERROR)
##             raise
##         if hasattr(mod, "formatter"):
##             plugins.append(mod.formatter)    
                
##     return plugins 
    


class SettingsBox(gtk.VBox):
    """
    the interface to use for the settings box, formatters should
    implement this interface and return it from the formatters's get_settings
    method
    """
    def __init__(self):
        super(SettingsBox, self).__init__()
    
    def get_settings(self):
        raise NotImplementerError
    
    def update(self, settings={}):
        raise NotImplementerError



class FormatterPlugin(pluginmgr.Plugin):
    '''
    an interface class that a plugin should implement if it wants to generate
    reports with the ReportToolPlugin

    NOTE: the title class attribute must be a unique string
    '''    
        
    title = ''
    
    @staticmethod
    def get_settings_box():
        '''
        return a class the implement gtk.Box that should hold the gui for
        the formatter
        '''
        raise NotImplementedError
    
    @staticmethod
    def format(selfobjs, **kwargs):
        '''
        called when the use clicks on OK, this is the worker
        '''
        raise NotImplementedError
    


class ReportToolDialogView(object):
    
    def __init__(self):
        self.widgets = utils.GladeWidgets(os.path.join(paths.lib_dir(),  
                                   "plugins", "report", 'report.glade'))
        self.dialog = self.widgets.report_dialog
        self.dialog.set_transient_for(bauble.gui.window)
        
        
    def start(self):
        return self.dialog.run()
        
        
        
class ReportToolDialogPresenter(object):    
    
    formatter_class_map = {} # title->class map
    
    def __init__(self, view):    
        self.view = view
        self.init_names_combo()
        self.init_formatter_combo()

        self.view.widgets.new_button.connect('clicked',
                                             self.on_new_button_clicked)
        self.view.widgets.remove_button.connect('clicked',
                                                self.on_remove_button_clicked)
        self.view.widgets.names_combo.connect('changed',
                                              self.on_names_combo_changed)
        self.view.widgets.formatter_combo.connect('changed',
                                               self.on_formatter_combo_changed)
        self.view.widgets.ok_button.set_sensitive(False)
        
        # set the names combo to the default, on_names_combo_changes should 
        # do the rest of the work
        combo = self.view.widgets.names_combo
        default = prefs[default_config_pref]
        try:
            self.set_names_combo(default)
        except Exception, e:
            debug('init: %s' % e)
            self.set_names_combo(0)


    def set_names_combo(self, val):
        """
        set the names combo to val and emit the 'changed' signal,
        @param val: either an integer index or a string value in the combo

        if the model on the combo is None then this method will return
        and not emit the changed signal
        """
        debug('set_names_combo(%s)' %  val)
        combo = self.view.widgets.names_combo
        if combo.get_model() is None:
            debug('--None')
            self.view.widgets.details_box.set_sensitive(False)
            return
        if isinstance(val, int):
            combo.set_active(val)    
        else:
            utils.combo_set_active_text(combo, val)
        combo.emit('changed')        
        
        
    def set_formatter_combo(self, val):
        """
        set the formatter combo to val and emit the 'changed' signal,
        @param val: either an integer index or a string value in the combo
        combo = self.view.widgets.formatter_combo
        """
        combo = self.view.widgets.formatter_combo
        if isinstance(val, int):
            combo.set_active(val)
        else:
            utils.combo_set_active_text(combo, val)            
        combo.emit('changed')
        
        
    def set_prefs_for(self, name, formatter_title, settings):
        '''
        this will overwrite any other report settings with name
        '''
#        debug('set_prefs_for(%s, %s, %s)' % (name, formatter_title, settings))
        formatters = prefs[config_list_pref]
        if formatters is None:
            formatters = {}
        formatters[name] = formatter_title, settings
        prefs[config_list_pref] = formatters
#        debug(prefs[config_list_pref])        
    
                
    def on_new_button_clicked(self, *args):
        # TODO: don't set the OK button as sensitive in the name dialog
        # if the name already exists
        # TOD0: make "Enter" in the entry fire the default response
        d = gtk.Dialog('', self.view.dialog,
                       gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
                       buttons=((gtk.STOCK_OK, gtk.RESPONSE_ACCEPT,
                      gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT)))    
        d.vbox.set_spacing(10)
        label = gtk.Label('Enter a name for the new formatter')
        label.set_padding(10, 10)
        d.vbox.pack_start(label)    
        entry = gtk.Entry()
        d.vbox.pack_start(entry)    
        d.show_all()
        names_model = self.view.widgets.names_combo.get_model()
        while True:
            if d.run() == gtk.RESPONSE_ACCEPT:
                name = entry.get_text()
                if name == '':
                    continue
                elif names_model is not None \
                         and utils.tree_model_has(names_model, name):
                    utils.message_dialog('%s already exists' % name)
                    continue
                else:
                    self.set_prefs_for(entry.get_text(), None, {})
                    self.populate_names_combo()
                    utils.combo_set_active_text(self.view.widgets.names_combo,
                                                name)
                    break                
            else:
                break                        
        d.destroy()
                    
    
    def on_remove_button_clicked(self, *args):
        formatters = prefs[config_list_pref]
        names_combo = self.view.widgets.names_combo
        name = names_combo.get_active_text()
        formatters.pop(name)
        prefs[formatters_list_pref] = formatters
        self.populate_names_combo()
        names_combo.set_active(0)

    
    def on_names_combo_changed(self, combo, *args):
        debug('on_names_combo.changed()')
        if combo.get_model() is None:
            print ' -- model = None'
            self.view.widgets.details_box.set_sensitive(False)
            return
        
        name = combo.get_active_text()
        debug('--- on_names_combo_changed(%s)' % name)
        formatters = prefs[config_list_pref]        
        self.view.widgets.details_box.set_sensitive(name is not None)
        prefs[default_config_pref] = name # set the default to the new name
        try:
            title, settings = formatters[name]
#            debug('%s, %s' % (title, settings))
        except (KeyError, TypeError), e:
            #debug(e)
            return
        
        try:
            self.set_formatter_combo(title)
        except Exception, e:
#            debug(e)
            self.set_formatter_combo(-1)
        self.view.widgets.details_box.set_sensitive(True)
            
#        debug('--- leaving on_names_combo_changed()')
            
            
    def on_formatter_combo_changed(self, combo, *args):
        '''
        formatter_combo changed signal handler
        '''
        title = combo.get_active_text()                
#        debug('**** on_formatter_combo_changed(%s)' % title)
        name = self.view.widgets.names_combo.get_active_text()        
        try:
            saved_title, settings = prefs[config_list_pref][name]            
            if saved_title != title:
                settings = {}                
#            debug('settings: %s' % settings)
#            # set the new formatter value in the preferences
#            set_prefs_for(name, self.formatter_class_map[title])
#            #prefs[config_list_pref][name] = title, settings
        except KeyError, e:
            debug(e)
            return
        
        expander = self.view.widgets.settings_expander
        child = expander.get_child()
        if child is not None:
            expander.remove(child)
            
        #self.widgets.ok_button.set_sensitive(title is not None)
        self.view.widgets.ok_button.set_sensitive(title is not None)
        if title is None:
            return                    
        
        cls = self.formatter_class_map[title]
        box = cls.get_settings_box()
        if box is not None:
            box.update(settings)
            expander.add(box)
            box.show_all()            
        expander.set_sensitive(box is not None)     
        # TODO: should probably remember expanded state, 
        # see formatter_settings_expander_pref
        expander.set_expanded(box is not None)
        title = combo.get_active_text()        
        self.set_prefs_for(name, title, settings)
#        debug('**** leaving on_formatter_combo_changed')
            
    
    def init_formatter_combo(self):        
        plugins = []
        for p in pluginmgr.plugins:
            if issubclass(p, FormatterPlugin):
                plugins.append(p)
        
        # we should always have at least the default formatter
        model = gtk.ListStore(str)
        #assert len(plugins) is not 0, 'No formatter plugins defined.'
        if len(plugins) == 0:
            utils.message_dialog('No formatter plugins defined',
                                 gtk.MESSAGE_WARNING)
            return
            
        for item in plugins:
            title = item.title
            self.formatter_class_map[title] = item            
            model.append([item.title])
        self.view.widgets.formatter_combo.set_model(model)        
        
        
    def populate_names_combo(self):
        '''
        populates the combo with the list of configuration names
        from the prefs
        '''
        configs = prefs[config_list_pref]
        combo = self.view.widgets.names_combo
        if configs is None:
            debug('configs is None')
            self.view.widgets.details_box.set_sensitive(False)
            combo.set_model(None)
            return        
        try:
            model = gtk.ListStore(str)
            for cfg in configs.keys():
                debug('cfg: %s' % cfg)
                model.append([cfg])
            combo.set_model(model)
        except AttributeError, e:
            # no formatters
            debug(e)
            pass
        
        
    def init_names_combo(self):      
##         formatters = prefs[config_list_pref]  
##         if formatters is None or len(formatters) == 0:
##             #msg = 'No formatters found. To create a new formatter click the '\
##             #      '"New" button.'
##             #utils.message_dialog(msg, parent=self.view.dialog)
##             debug('names_combo.model=None')
##             self.view.widgets.names_combo.set_model(None)
#        self.view.widgets.names_combo.set_model(None)
        self.populate_names_combo()
        

    def save_formatter_settings(self):
        name = self.view.widgets.names_combo.get_active_text()        
        title, dummy =  prefs[config_list_pref][name]
        box = self.view.widgets.settings_expander.get_child()
        formatters = prefs[config_list_pref]
#        debug('save_formatter_settings: %s: %s, %s' % (name, title, box.get_settings()))
        formatters[name] = title, box.get_settings()
        prefs[config_list_pref] = formatters
#        debug(prefs[config_list_pref][name])
        
        
    def start(self):
        formatter = None
        settings = None
        while True:
            response = self.view.start()
            if response == gtk.RESPONSE_OK:
                # get format method
                # save default
                prefs[default_config_pref] = \
                             self.view.widgets.names_combo.get_active_text()
                self.save_formatter_settings()
                name = self.view.widgets.names_combo.get_active_text()        
                title, settings =  prefs[config_list_pref][name]
                formatter = self.formatter_class_map[title]
                break
            else:
                break
        self.view.dialog.destroy()
        return formatter, settings
        
    
     
class ReportToolDialog(object):
    
    def __init__(self):        
        self.view = ReportToolDialogView()
        self.presenter = ReportToolDialogPresenter(self.view)


    def start(self):
        return self.presenter.start()
    
    
    
class ReportTool(pluginmgr.Tool):    
    
    label = "Report"
    
    @classmethod
    def start(self):        
        '''
        '''    
        # get the select results from the search view
        from bauble.view import SearchView
        view = bauble.gui.get_view()
        if not isinstance(view, SearchView):
            utils.message_dialog(_('Search for something first.'))
            return
            
        model = view.results_view.get_model()
        if model is None:
            utils.message_dialog(_('Search for something first.'))
            return
        
        bauble.set_busy(True)
        # extract the plants from the search results
        # TODO: need to speed this up using custom queries, see the 
        # family and genera infoboxes            
        ok = False
        try:            
            while True:
                dialog = ReportToolDialog()
                formatter, settings = dialog.start()
                if formatter is None:
                    break
                ok = formatter.format([row[0] for row in model], **settings)
                if ok:
                    break
                        
        except AssertionError, e:
            debug(e)
            utils.message_dialog(str(e), gtk.MESSAGE_ERROR,
                                 parent=self.view.dialog)            
        except Exception:
            debug(traceback.format_exc())
            utils.message_details_dialog('Formatting Error', 
                                     traceback.format_exc(), gtk.MESSAGE_ERROR)
        bauble.set_busy(False)       
        return



class ReportToolPlugin(pluginmgr.Plugin):
    '''
    '''
    tools = [ReportTool]

    

def plugin():
    from bauble.plugins.report.default import DefaultFormatterPlugin    
    return [ReportToolPlugin, DefaultFormatterPlugin]
#plugin = [ReportToolPlugin]

