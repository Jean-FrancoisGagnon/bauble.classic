#
# editors module
#

import os, sys, re, copy, traceback
import gtk
from sqlobject.sqlbuilder import *
from sqlobject import *
from sqlobject.joins import SOSingleJoin
import bauble
from bauble.plugins import BaubleEditor, BaubleTable, tables
from bauble.prefs import prefs
import bauble.utils as utils

from bauble.utils.log import log, debug

# TODO: if the last column is made smaller from draggin the rightmost part
# of the header then automagically reduce the size of  the dialog so that the 
# there isn't the extra junk past the, and i guess do the same to the leftmost
# side of the the first column

# TODO: need some type of smart dialog resizing like when columns are added
# change the size of the dialog to fit unless you get bigger than the screen
# then turn on the scroll bar, and something similar for adding rows 

# FIXME: everytime you open and close a TreeViewEditorDialog the dialog
# get a little bigger, i think the last column is creeping
    
# TODO: if you edit a row that has it's own editor then it doesn't call
# set_dirty

# TODO: create a contextual helps so that pressing ctrl-space on a cell
# gives a tooltip or dialog giving you more information about the current
# cell you are editing
    
    
class CellRendererButton(gtk.GenericCellRenderer):
    
    def __init__(self, *args, **kwargs):
        super(CellRendererButton, self).__init__(*args, **kwargs)
        
    def on_get_size(self, widget, cell_area):
        pass
    
    def on_render(self, window, widget, background_area, cell_area, 
                  expose_area, flags):
        pass
    
    def on_activate(self, event, widget, path, background_area, cell_area, 
                    flags):
        pass
    
    def on_start_editing(self, event, widget, path, background_area, cell_area, 
                         flags):
        pass


class GenericViewColumn(gtk.TreeViewColumn):
    
    def __init__(self, tree_view_editor, header, renderer, so_col=None, so_join=None):
        super(GenericViewColumn, self).__init__(header, renderer)
       
        if not isinstance(tree_view_editor, TreeViewEditorDialog):
            raise ValueError('tree_view_editor must be an isntance of '\
                             'TreeViewEditorDialog')
#        assert so_col is not None
#        if view is None:
#            raise ValueError('view is None')
#            
#        if so_col is None:
#            raise ValueError('so_col is None')        
        self.dirty = False

        if so_col is not None and so_join is not None:
            raise ValueError('cannot specify both so_col and join')
        self.table_editor = tree_view_editor
        self.renderer = renderer
        self.set_cell_data_func(renderer, self.cell_data_func)
                
        self.meta = GenericViewColumn.Meta()
        self.meta.so_join = so_join
        self.meta.so_col = so_col  
        if so_col is not None and so_col._default == NoDefault:
            self.meta.required = True
            self.meta.default = so_col._default
            self.set_visible(True)
            
        self.set_property('visible', self.meta.required)
        self.set_min_width(50)
        self.set_clickable(True)
        self.set_resizable(True)
        self.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        self.set_reorderable(True)
        
        #column.set_cell_data_func(r, self.toggle_cell_data_func, name)
        #    if meta.editor is None: # the editor will set the value
        #        
    
    def _set_view_model_value(self, path, value):
        model = self.table_editor.view.get_model()
        i = model.get_iter(path)
        row = model.get_value(i, 0)
        row[self.name] = value
    
    #
    # name property
    #
    def __get_name(self):
        if self.meta.so_join is not None:
            return self.meta.so_join.joinMethodName
        elif self.meta.so_col is not None:
            return self.meta.so_col.name
        
        raise ValueError("meta.so_col is None")
        #return self.meta.so_col.name
    name = property(__get_name)
    
    class Meta:

        # the SQLObject column this ViewColumn represents
        so_col = None
        
        #
        # the method to call to get this list of completions for this
        # column is the column is a text entry, 
        # method signature: get_completions(complete_for_str)
        # TODO: how would i add this field to the class Meta 
        # inside TextColumn so that this field is only relevant 
        # to TextColumn
        #
        get_completions = None
        
        # the column provides its own editor
        editor = None
        
        # is self.required is True then you can't hide this column
        # from the view
        required = False
        
        # if self.getter is set then use this method to return the values
        # for the row, e.g. self.meta[colname].getter(row)
        getter = None
 
        # a method to validate the data in the column before it is set
        validate = lambda x: x
        
        
    def cell_data_func(self, col, cell, model, iter, view):
        raise NotImplementedError, "%s.cell_data_func not implemented" % \
            self.__class__.__name__


#class EditableColumn(GenericViewColumn):
#    
#    def __init__(self, view, header, so_col=None):
#        super(EditableColumn, self).__init__(view, header)
#        
#        

# TODO: create a seperate column class that doesn't act like a normal text
# entry column so that there is a consisten way to show the user they
# need to press Enter or something to open the editor
class ExternalEditorColumn(GenericViewColumn):
    
    def __init__(self, view, header, so_col=None, so_join=None):
        super(ExternalEditorColumn, self).__init__(view, header, 
                                                   CellRendererButton,
                                                   so_col, so_join)
        
        
    def on_editing_started(self, cell, entry, path, view):
        # connect to on insert, see TextColumn
        pass

    
class ToggleColumn(GenericViewColumn):
    
    def __init__(self, view, header, so_col=None):        
        super(ToggleColumn, self).__init__(view, header, 
                                           gtk.CellRendererToggle(),
                                           so_col)
        self.renderer.connect("toggled", self.on_toggled)
        self.set_resizable(False)
        self.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
            
            
    def on_toggled(self, renderer, path, data=None):
        self.dirty = True
        active = not renderer.get_active()
        self._set_view_model_value(path, active)    
        
        
#    def on_renderer_toggled(self, widget, path, data=None):
#        active = widget.get_active()
#        model = self.plants_view.get_model()
#        it = model.get_iter(path)
#        model.set_value(it, 0, not active)
        
    def cell_data_func(self, col, cell, model, iter, data=None):
        row = model.get_value(iter, 0)
        value = row[self.name]
        #debug(iter)
        if value is None:
            # this should really get the default value from the table
            #debug('inconsistent')
            cell.set_property('inconsistent', False) 
        else:
            #debug('active: ' + str(value))
            cell.set_property('active', value)
                                           
        

class TextColumn(GenericViewColumn):
    
    def __init__(self, view, header, renderer=None, so_col=None, so_join=None):        
        if renderer is None:
            renderer = gtk.CellRendererText()            
        super(TextColumn, self).__init__(view, header, renderer, so_col, 
                                         so_join)
        self.renderer.set_property("editable", True)
        self.renderer.connect("editing_started", self.on_editing_started, view)
        self.renderer.connect('edited', self.on_edited)
    
    
    def cell_data_func(self, column, renderer, model, iter, data=None):
        row = model.get_value(iter, 0)
        #if colname not in row: return # this should never happen
        value = row[self.name]
        
        if value is None: # no value in model
            renderer.set_property('text', None)
        elif type(value) == list: 
            # if a list then value[0] should be the string displayed while
            # row[1] is the value we want to put in the model, used mostly
            # for completions
            renderer.set_property('text', value[1])
        else: 
            # just plain text in model column or something convertible 
            # to string like a table row
            renderer.set_property('text', str(value))
            

    def on_edited(self, renderer, path, new_text, set_in_model=True):
        debug('on_edited')
        debug(str(renderer))
        debug(str(path))
        debug(new_text)
        debug(type(new_text))
        # means that the value is set by the on_match_completed function,
        # there should be a way to set either on_edited or on_completion
        # but not both
        # TODO: what happens when you type something into the column
        # that has a completion but what you type isn't a completion
        # we should either query for the value or don't allow it to 
        # be set
        #debug('on_edited')        
        # don't allow empty strings in the model, this usually means a null
        # value in the cell
        debug('new_text: %s' % new_text)
        if new_text == "":
            debug('new_text')
            return
        else:
            debug('not new text')
        self.dirty = True        
        if self.meta.get_completions is not None:
            return        
        if set_in_model:
            self._set_view_model_value(path, new_text)
        
                                           
    def on_editing_started(self, cell, entry, path, view):
        # if the cell has it's own editor we shouldn't be here
        if self.meta.editor is not None: 
            entry.connect('key-press-event', self.on_key_press, path)
            entry.set_property('editable', False)
                
        #entry.connect("key-press-event", self.on_cell_key_press, 
#                         path, colname)
# TODO: set up a validator on the col depending on the sqlobj.column type
        
        if isinstance(self.meta.so_col, SOForeignKey) and \
          not self.meta.get_completions:
              msg  = "%s is a foreign key but there are no completions" % self.name
              utils.message_dialog(msg, gtk.MESSAGE_ERROR)
              entry.set_property('editable', False)
              return

        entry.connect("insert-text", self.on_insert_text, path)
        #entry.connect("editing-done", self.on_editing_done)
        #self.current_entry = editable        
        # if not a foreign key then validate, foreign keys can only
        # be entered from existing values and so don't need to
        # be validated
        #if not self.column_meta[colname].foreign:
        #    if self.column_meta[colname].  
      

    def on_completion_match_selected(self, completion, model, iter, 
                                     view_model_path):
        """
        all foreign keys should use entry completion so you can't type in
        values that don't already exists in the database, therefore, allthough
        i don't like it the view.model.row is set here for foreign key columns
        and in self.on_edited for other column types                
        """        
        # we assume on a successfull completion that 0 is the value
        # that we matched on and 1 is the value we want in the model
        debug("TextColumn.on_completion_match_selected(%s)" % self.name)
        self.dirty = True
        value = model.get_value(iter, 1)        
        self._set_view_model_value(view_model_path, value)
        
        
    def on_insert_text(self, entry, text, length, position, path):
        """
        handle text filtering/validation and completions
        """
        # TODO: the problem is only validates on letter at a time
        # we need to have a format string which is inserted
        # in the entry before typeing starts and fills in the gap
        # as the user types
#        try:
#            self.column_meta[colname].validate(text)
#        except ValueError:
#            entry.stop_emission("insert_text")
        
        # there are no completions, disconnect from signal
        # TODO: we should really be disconnecting with the signal with
        # this signal id so we don't stop all insert_text signals
        #debug('on_insert_text: ' + text)        
        if self.meta.get_completions is None:
            #debug("no completions")
            #debug(self.name)
            #debug('stop emmiting insert text')
            #entry.stop_emission("insert_text") 
            return
            
        full_text = entry.get_text() + text
        entry_completion = entry.get_completion()
        if entry_completion is None:
            entry_completion = gtk.EntryCompletion()
            entry_completion.set_minimum_key_length(2)
            entry_completion.set_text_column(0)
            entry_completion.connect("match-selected", 
                                     self.on_completion_match_selected, 
                                     path)
            entry.set_completion(entry_completion)
            
        if len(full_text) == 2:
            # this could take too long if there are alot of completions
            model = self.meta.get_completions(full_text)
            entry_completion.set_model(model)


    def on_key_press(self, widget, event, path):
        """
        if the column has an editor, invoke it
        """
        keyname = gtk.gdk.keyval_name(event.keyval)
        if keyname == 'Return':
            # start the editor for the cell if there is one
            if self.meta.editor is not None:
                model = self.table_editor.view.get_model()
                it = model.get_iter(path)
                row = model.get_value(it,0)
                e = self.meta.editor(select=row[self.name])
                response = e.start()
                debug('response: %s - %s - %s' % (response, 
                       gtk.RESPONSE_ACCEPT,
                       gtk.RESPONSE_OK))
                if response == gtk.RESPONSE_ACCEPT or \
                   response == gtk.RESPONSE_OK:
                    debug('response OK')
                    so_obj = e.commit_changes(transaction=self.table_editor.transaction)
                    self._set_view_model_value(path, so_obj)                    
                    self.dirty = True
                    self.renderer.emit('edited', path, so_obj, False)


class ComboColumn(TextColumn):
    
    def __init__(self, view, header, so_col):
        """
        we allow a renderer to be passed here so the user can attach
        custom models to the combo instead of doing it in 
        on_editing_started
        """
        super(ComboColumn, self).__init__(view, header, gtk.CellRendererCombo(), 
                                          so_col)
        # which column from the combo model to display
        self.renderer.set_property("text-column", 0)


    def cell_data_func(self, col, cell, model, iter, data=None):
        # assumes the text column is 0 but the value we want 
        # to store in the model column 1
        row = model.get_value(iter, 0)
        if row is not None:
            v = row[self.name]
            cell.set_property('text', v)
                    
        
    def __get_model(self):
        return self.renderer.get_property('model')            
    def __set_model(self, model):
        self.renderer.set_property('model', model)        
    model = property(__get_model, __set_model)    
                                               
                                           
    def on_editing_started(self, cell, editable, path, view):                
        debug('on_editing_started')



def set_dict_value_from_widget(dic, dict_key, glade_xml, widget_name, model_col=0, validator=lambda x: x):
    w = glade_xml.get_widget(widget_name)
    v = get_widget_value(glade_xml, widget_name, model_col)
    
    if v == "": 
        v = None
    elif isinstance(v, BaubleTable):
        v = v.id
        
    if v is not None:
        v = validator(v)
        dic[dict_key] = v
        

def get_widget_value(glade_xml, widget_name, column=0):
    """
    column is the column to use if the widget's value is a TreeModel
    """
    w = glade_xml.get_widget(widget_name)
    if isinstance(w, gtk.Entry):
        return w.get_text()
    elif isinstance(w, gtk.TextView):
        buffer = w.get_buffer()
        start = buffer.get_start_iter()
        end = buffer.get_end_iter()
        return buffer.get_text(start, end)
    elif isinstance(w, gtk.ComboBoxEntry) or isinstance(w, gtk.ComboBox):
        v = None
        i = w.get_active_iter()
        if i is not None:
            v = w.get_model().get_value(i, column)
        return v
    elif isinstance(w, gtk.CheckButton):
        return w.get_active()
    elif isinstance(w, gtk.Label):
        return w.get_text()
    raise ValueError("%s -- set_dict_value_from_widget: " \
                     " ** unknown widget type: %s " % (__file__,str(type(w))))
    

def set_widget_value(glade_xml, widget_name, value):
    print 'set_widget_value: ' + widget_name
    if value is None: return
    w = glade_xml.get_widget(widget_name)
    if w is None:
        raise ValueError("set_widget_value: no widget by the name "+\
                         widget_name)
    print type(value)
    if type(value) == ForeignKey:
        pass
    elif isinstance(w, gtk.Entry):
        w.set_text(value)



class TableMeta:
    """
    hold information about the table we will be editing with the table editor
    """
    def __init__(self):
        self.foreign_keys = []
        self.joins = []
    

## TODO: finish this and get rid of ModelRowDict, to make this as useful
# as ModelRowDict it would have to have some knowledge of the tables
#class ListStoreDict(gtk.ListStore):
#    """
#    can be uses the same as a tree store but the row can be accessed
#    by a key other than int
#    """
#    # {id: int}
#    def __init__(self, **kwargs):
#        types = []
#        self.name_map = {}
#        i = 0
#        for name, t in kwargs.iteritems():
#            name_map[name] = i
#            types.append(t)
#            i += 1
#        super(ListStoreDict(), self).__init__(*types)
#   
#   
#    def get_value(self, iter, name):
#        return super(ListStoreDict, self).get_value(iter, name_map[name])()
#   
#   
#    def append(self, **kwargs):
#        values = []
#        for name, index in self.name_map.iteritems():
#            values[index] = kwargs[name]
#        super(ListStoreDict, self).append()           
       
               
class ModelRowDict(dict):
    """
    a dictionary representation of an SQLObject used for storing table
    rows in a gtk.TreeModel
    dictionary values are only stored in self if they are accessed, this
    saves on database queries lookups (i think, should test). this also
    means that when we retrieve the dictionary to commit the values then
    we only get those values that have been accessed
    """
    def __init__(self, row, columns, defaults={}):
        # if row is an instance of BaubleTable then get the values
        # from the instance else check that the items are valid table
        # attributes and don't let the editors set attributes that 
        # aren't valid
        
        # if row is not an instance then make sure
        self.isinstance = False
        if isinstance(row, BaubleTable):
            self.isinstance = True
            self['id'] = row.id # always keep the id
        elif not issubclass(row, BaubleTable):
            msg = 'row should be either an instance or class of BaubleTable'
            raise ValueError('ModelRowDict.__init__: ' + msg)
            
        #if row is not None and not isinstance(row, BaubleTable):
        #    raise ValueError('ModelRowDict.__init__: row is not an instance')
        
        self.row = row # either None or an instance of BaubleTable
        self.defaults = defaults or {}
        
        # getters are a way that a column can provide a custom function
        # on what it wants to return from a row, this is pretty much
        # a bad idea but we need it in some cases
        # FIXME: this is inefficient to do this everytime a row is added
        self.getters = {}
        for c in columns.values():
            if c.meta.getter is not None:
                self.getters[c.name] = c.meta.getter
            

    def __contains__(self, item):
        """
        this causes the 'in' operator and has_key to behave differently,
        e.g. 'in' will tell you if it exists in either the dictionary
        or the table while has_key will only tell you if it exists in the 
        dictionary, this is a very important difference
        """
        if self.has_key(item):
            return True
        elif self.row is not None:             
            return hasattr(self.row, item)
        else: 
            return False
        #if self.row is not None:
        #    return hasattr(self.row, item)
        #else: self.has_key(item)


    def __getitem__(self, item):
        """
        get items from the dict
        if the item does not exist then we create the item in the dictionary
        and set its value from the default or to None
        """
        # TODO: this method could use alot of love
        if self.has_key(item): # use has_key to avoid __contains__
            return self.get(item)

        # else if row is an instance then get it from the table
        v = None        
        if self.isinstance:
#            if self.meta[item].getter is not None:
#                v = self.meta[item].getter(self.row)
            if item in self.getters:
                v = self.getters[item](self.row)
            else: # we want this to fail if item doesn't exist in row
                v = getattr(self.row, item)
                
            if v is None and item in self.defaults:
                v = self.defaults[item]
            
            #if item in self.row.sqlmeta.columns: # is a column
            #    column = self.row.sqlmeta.columns[item]            
            #else:
            #    column = self.row.sqlmeta.joins[item]
            if item in self.row.sqlmeta.columns:
                column = self.row.sqlmeta.columns[item]            
                if v is not None and isinstance(column, SOForeignKey):                
                    table_name = column.foreignKey                    
                    v = tables[table_name].get(v)                
        else:
            # else not an instance so at least make sure that the item
            # is an attribute in the row, should probably validate the type
            # depending on the type of the attribute in row
            if not hasattr(self.row, item):
                msg = '%s has not attribute %s' % (self.row.__class__, item)
                raise KeyError('ModelRowDict.__getitem__: ' + msg)
            if item in self.defaults:
                v = self.defaults[item]
            else:
                v = None
                    
        
        #debug("%s: %s" % (item, column))
        # if the column is a foreign key then return the object rather
        # than the ID

            #debug('foriegn key: %s, %s' % (table_name, str(v)))
        self[item] = v
        return v
       
       

#
# editor interface
#
class TableEditor(BaubleEditor):

    standalone = True
    
    def __init__(self, table, select=None, defaults={}):
        super(TableEditor, self).__init__()
        self.defaults = copy.copy(defaults)
        self.table = table
        self.select = select        
        self.transaction = sqlhub.processConnection.transaction()
        
        
    def start(self): 
        raise NotImplementedError

        
    def commit_changes(self):
        raise NotImplementedError



#
# editor interface that opens a dialog
#
class TableEditorDialog(TableEditor, gtk.Dialog):
    

    def __init__(self, table, title="Table Editor", parent=None, select=None, defaults={}):
        #
        # how do i use super() with multiple inheritance
        #
        #super(TableEditorDialog, self).__init__()
        TableEditor.__init__(self, table, select, defaults)
        gtk.Dialog.__init__(self, title, parent, 
                            gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, 
                            (gtk.STOCK_OK, gtk.RESPONSE_OK, 
                             gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))

                          
    def start(self):
        self.run()
            
    

#
# TreeViewEditorDialog
# a spreadsheet style editor
#
# TODO:
# (2) ability to attach some sort of validator on the column
# which will always ensure that whatever is entered is of the correct format
# and would possible even complete some things for you like the "." in the
# middle of an accessions
# (3) should somehow check which columns have default values and which
# don't and treat them as required columns, so you can't change the visibility
# and can go to the next row having with out editing them
# (4) should have a label at the top which give information about what's
# being edited and what could be wrong ala eclipse
class TreeViewEditorDialog(TableEditorDialog):
    """the model for the view in this class only has a single column which
    is a Table class which is really just a dict. each value in the dict
    relates to a column in the tree but
    this allows us to refer to the columns by name rather than by column
    number    
    """    
    visible_columns_pref = None
    column_width_pref = None
    default_visible_list = []

    class ColumnDict(dict):
        """
        hold a dictionary of columns by their names
        """
        def __init__(self):
            self.joins = [] # populate in start_tree_view
            
        def __set_titles(self, titles):
            for name, title in titles.iteritems():
                self[name].set_property('title', title)
        
        titles = property(fset=__set_titles)
        

    def __init__(self, table, title="Table Editor", parent=None, select=None, defaults={}):
        super(TreeViewEditorDialog, self).__init__(table, title, parent, select, defaults)
        self.__view = None        
        self.dirty = False
        self.table_meta = TableMeta()        
        self.init_gui()
        
        # this is used to indicate that the last row is a valid row
        # or it is one that was added automatically but never used
        self.dummy_row = False
        
        #self.connect('response', self.on_response)
        
        
    def start(self):
        # this ensures that the visibility is set properly in the meta before
        # before everything is created
        if self.visible_columns_pref is not None:
            if not self.visible_columns_pref in prefs:
                prefs[self.visible_columns_pref] = self.default_visible_list
            self.set_visible_columns_from_prefs(self.visible_columns_pref)
        self.start_gui()

        while True:
            msg = 'Are you sure you want to lose your changes?'
            if self.run() == gtk.RESPONSE_OK:
                if self.commit_changes():
#                    debug("committed changes")
                    break
            elif self.dirty and utils.yes_no_dialog(msg):
                break      
            else:
                break               

        self.store_column_widths()
        self.store_visible_columns()
        self.destroy()

    
    def init_gui(self):
        self.init_tree_view()
        
    
    def start_gui(self):
        vbox = gtk.VBox(False)
        self.start_tree_view()
        self.create_toolbar()                
        vbox.pack_start(self.toolbar, fill=False, expand=False)
        
        sw = gtk.ScrolledWindow()        
        sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        sw.add(self.view)
        vbox.pack_start(sw)
        
        self.vbox.pack_start(vbox)
        
        self.set_default_size(-1, 300) # an arbitrary size
                
        # set ok button insensitive
        ok_button = self.action_area.get_children()[1]
        ok_button.set_sensitive(False)        
        
        self.show_all()        
                
    def init_tree_view(self):
        """
        create the main tree view
        """
        # have to create the view before the column
        self.__view = gtk.TreeView(gtk.ListStore(object))
        
        # create the columns from the meta data
        self.columns = self.create_view_columns()                                        
        self.view.set_headers_clickable(False)

    def __get_view(self):
        return self.__view
    view = property(__get_view)
  
    
    def start_tree_view(self):
        
        # remove join columns if they don't have an editor associated
        column_names = self.columns.keys()
        for join in self.table.sqlmeta.joins:
            # we create columns for the joins here but we remove the column
            # once the view is created if there isn't an external editor, this
            # allows classes that extend this editor class to setup the editor
            # in their constructor like they would do with normal column
            #debug(join)
            #debug(join.joinMethodName)
            name = join.joinMethodName
            #debug('%s: %s' % (name, self.columns[name].meta.editor))            
            #debug(self.columns.keys())
            if name in column_names:
                if self.columns[name].meta.editor is None:
                    debug('removing %s' % name)
                    self.columns.pop(name)
                else:
                    debug('adding %s to self.columns.joins' % name)
                    self.columns.joins.append(name)
            
                
            
        # create the model from the tree view and add rows if a
        # selectresult is passed
        if self.select is not None:
            for row in self.select:
                self.add_new_row(row)
        else:
            self.add_new_row()
            
        # enter the columns from the visible list, the column visibility
        # should already have been set before creation from the prefs,
        # here we just have to add them in order
        visible_list = ()
        if self.visible_columns_pref != None and \
           self.visible_columns_pref in prefs:
            visible_list = list(prefs[self.visible_columns_pref][:])
            visible_list.reverse()
            for name in visible_list:
                if name in self.columns:
                    self.view.insert_column(self.columns[name], 0)
        
        # append the rest of the column to the end and set all the widths        
        width_dict = self.get_column_widths_from_prefs()            
        for name, column in self.columns.iteritems():
            if name not in visible_list:
                self.view.append_column(self.columns[name])
            if name in width_dict and width_dict[name] > 0:
                column.set_fixed_width(width_dict[name])

        # now that all the columns are here, let us know if anything 
        # changes
        self.view.connect("columns-changed", self.on_column_changed)
        self.view.connect("move-cursor", self.on_view_move_cursor)
        self.view.connect("cursor-changed", self.on_cursor_changed)
        self.view.connect("button-release-event", self.on_view_button_release)
        
    
    def create_toolbar(self):
        """
        TODO: should make those columns that can't be null and don't
        have a default value, i.e. required columns show in the menu
        but they should be greyed out so you can't turn them off
        """
        self.toolbar = gtk.Toolbar()
        col_button = gtk.MenuToolButton(None, label="Columns")
        menu = gtk.Menu()
        # TODO: would rather sort case insensitive
        for name, col in sorted(self.columns.iteritems()):
            #if meta.join and not meta.type == SOSingleJoin and not meta.editor:
            #    continue            
            title = col.get_property('title').replace('_', '__') # no mnemonics
            item = gtk.CheckMenuItem(title)            
            if col.meta.required:
                item.set_sensitive(False)                
            item.set_active(col.get_visible())
            item.connect("toggled", self.on_column_menu_toggle, name)
            menu.append(item)
            item.show()
        col_button.set_menu(menu)
        self.toolbar.insert(col_button, -1)  
        
            
    def foreign_does_not_exist(self, name, value):
        """
        this is intended to be overridden in a subclass to do something
        interesting if the foreign key doesn't exist
        """
        msg = "%s does not exist in %s" % (value, name)
        utils.message_dialog(msg, gtk.MESSAGE_ERROR)
        
        
    def set_ok_sensitive(self, sensitive):
        ok_button = self.action_area.get_children()[1]
        ok_button.set_sensitive(sensitive)
        
    
    def set_dirty(self, dirty=True):
        self.dirty = dirty
        self.set_ok_sensitive(dirty)
                    
                    
    # attache to mouse clicks
    def on_view_button_release(self, view, event, data=None):
        """
        popup a context menu on the selected row
        """
        if event.button != 3: 
            return # if not right click then leave
        sel = view.get_selection()
        model, i = sel.get_selected()
        if model == None:
            return # nothing to pop up a context menu on
        value = model.get_value(i, 0) 
        
        # can't remove the last row
        if len(model) == 1:
            return
            
        menu = gtk.Menu()
        remove_item = gtk.MenuItem("Remove") # remove the row from the editor
        remove_item.connect("activate", lambda x: model.remove(i))
        menu.add(remove_item)        
        menu.show_all()
        menu.popup(None, None, None, event.button, event.time)
            
        
    def on_column_menu_toggle(self, item, colname=None):
        debug('on_column_menu_toggle: %s' % colname)
        visible = item.get_active()
        debug(str(visible))
        debug(self.columns[colname])
        self.columns[colname].set_visible(visible)
        
        # could do this with a property notify signal
        self.view.resize_children()


    def on_column_changed(self, treeview, data=None):
        """
        keep up with the order of the columns to make key navigation
        easier
        NOTE: i'm not sure what i'm talking about here, i think this may be
        an old function i don't need anymore
        """
        #debug("on_column_changed")
#        self.resize_children()
#        self.view.resize_children()
#        self.view.queue_resize()
#        self.queue_resize()
        pass
         
        
    def get_values_from_view(self):
        """
        used by commit_changes to get the values from a table so they
        can be commited to the database, this version of the function
        removes the values with None as the value from the row, i thought
        this was necessary but now i don't, in fact it may be better in
        case you want to explicitly set things null
        """
        # TODO: this method needs some love, there should be a more obvious
        # way or at least simpler way of return lists of values
        model = self.view.get_model()
        values = []
        for item in model:
            # copy it so we dont change the data in the model
            # TODO: is it really necessary to copy here
            temp_row = copy.copy(item[0]) 
            for name, value in item[0].iteritems():                
                # del the value if they are none, have to do this b/c 
                # we don't want to store None in a row without a default
                #debug("%s: %s, %s" % (name, value, str(type(value))))
                if value is None:
                    del temp_row[name]
                elif type(value) == list and type(value[0]) == int:
                    debug('id name pair -- i thought we could del this but i guess we cant')
                    temp_row[name] = value[0] # is an id, name pair                
                elif isinstance(value, BaubleTable):
#                    debug('is table')
#                    debug("%s: %s" % (value, type(value)))                    
                    temp_row[name] = value.id                  
                    #else: # it is a list but we assume the [0] is 
                    # a table and [1] is a dict of value to commit, 
                    # we assume this is here because we need to set the 
                    # foreign key in the subtable to the id of the current
                    # row after it is commited and then commit the subtable
                    # there has to be a better way than this
            debug(temp_row)
            values.append(temp_row)
            
        if self.dummy_row:
            del values[len(model)-1] # the last one should always be empty
        return values      
        
        
    # TODO: this should replace the commit logic in self.commit_changes to 
    # allow an editor that extends this class for fine grained control over
    # commits without having to rewrite all of commit_changes
    # right now it's not ready
    def commit(self, values):        
        try:
            if 'id' in v:# updating row
                t = self.table.get(values["id"])
                del values["id"]
                t.set(**values)
            else: # adding row
                t = self.table(**values)
        except:
            raise

    # pre commit hook
    def test_values_before_commit(self, values):
        return True
    
    
    def commit_changes(self):
        """
        commit any change made in the table editor
        """        
#        debug("entered commit_changes")
        # TODO: do a map through the values returned from get_tables_values
        # and check if any of them are lists in the (table, values) format
        # if they are then we need pop the list from the values and commit
        # the current table, set the foreign key of the sub table and commit 
        # it
        # TODO: if i don't set the connection parameter when i create the
        # table then is it really using the transaction, it might be if 
        # sqlhub.threadConnection is set to the transaction
        values = self.get_values_from_view()
        for v in values:
            # make sure it's ok to commit these values            
            if not self.test_values_before_commit(v):                
                continue                
            # first pop out columns in table_meta.foreign_keys so we can
            # set their foreign key id later                
            foreigners = {}
            join_values = {}
            for col, col_attr in self.table_meta.foreign_keys:
                # use has_key to check the dict and not the table, 
                # see ModelRowDict.__contains__
                if v.has_key(col): 
                    foreigners[col] = v.pop(col)
            
            # remove the join values from v so we can set them with the 
            # row id later
            for name in self.columns.joins:
                debug('popping join: %s' % name)
                if name in v:                                        
                    join_values[name]= v.pop(name)
                
            # update or set the row depending on where there is an 'id' key
            # in the v dict
            try:                
                if 'id' in v:# updating row
                    t = self.table.get(v["id"], connection=self.transaction)
                    del v["id"]
                    t.set(**v)
                else: # adding row
                    debug('adding row: ' + str(v))
                    t = self.table(connection=self.transaction, **v)
                #print 'foreign: ' + str(foriegners)
                
                # temporarily disable
                #trans.commit()
                
                # set the foreign keys id of the foreigners
                for col, col_attr in self.table_meta.foreign_keys:
                    if col in foreigners:
                        c = foreigners[col]
                        debug(c)
                        foreign_table = \
                            c.__class__.get(c.id, connection=self.transaction)
                        foreign_table.set(**{col_attr: t.id})
                        # temporary disable
                        #trans.commit()
                        #c.set(**{col_attr: t.id})                
                debug('committing joins')    
                for join_name, jv in join_values.iteritems():
                    debug(jv)
                    join_column = self.columns[join_name].meta.so_join.joinColumn
                    # remove the _id from the end and set the table id                
                    # TODO: i don't think the name of the join is enough
                    # here, i think we need to get the name of the joinColumn
                    # from the join
                    join_attr = getattr(t, join_name)
                    jv.set(**{join_attr.joinColumn: t.id})
                    
                    # temporary disable
                    #trans.commit()
                        
            except Exception, e:                
                debug('rolling back changes')
                self.transaction.rollback()
                #sqlhub.threadConnection = old_conn
                #sqlhub.processConnection = old_conn
                msg = "Could not commit changes.\n" + str(e)
                utils.message_details_dialog(msg, traceback.format_exc(), 
                                              gtk.MESSAGE_ERROR)
                return False      
            else:
                self.transaction.commit()
        
#    def commit_changes2(self):
#        """
#        commit any change made in the table editor
#        """        
##        debug("entered commit_changes")
#        # TODO: do a map through the values returned from get_tables_values
#        # and check if any of them are lists in the (table, values) format
#        # if they are then we need pop the list from the values and commit
#        # the current table, set the foreign key of the sub table and commit 
#        # it
#        # TODO: if i don't set the connection parameter when i create the
#        # table then is it really using the transaction, it might be if 
#        # sqlhub.threadConnection is set to the transaction
#        values = self.get_values_from_view()
#        old_conn = sqlhub.getConnection()
#        trans = old_conn.transaction()
#        sqlhub.processConnection = trans
#        for v in values:
#            # make sure it's ok to commit these values            
#            if not self.test_values_before_commit(v):                
#                continue                
#            # first pop out columns in table_meta.foreign_keys so we can
#            # set their foreign key id later                
#            foreigners = {}
#            join_values = {}
#            for col, col_attr in self.table_meta.foreign_keys:
#                # use has_key to check the dict and not the table, 
#                # see ModelRowDict.__contains__
#                if v.has_key(col): 
#                    foreigners[col] = v.pop(col)
#            
#            # remove the join values from v so we can set them with the 
#            # row id later
#            for name in self.columns.joins:
#                debug('popping join: %s' % name)
#                if name in v:                                        
#                    join_values[name]= v.pop(name)
#                
#            # update or set the row depending on where there is an 'id' key
#            # in the v dict
#            try:                
#                if 'id' in v:# updating row
#                    t = self.table.get(v["id"], connection=trans)
#                    del v["id"]
#                    t.set(**v)
#                else: # adding row
#                    debug('adding row: ' + str(v))
#                    t = self.table(connection=trans, **v)
#                #print 'foreign: ' + str(foriegners)
#                
#                # temporarily disable
#                #trans.commit()
#                
#                # set the foreign keys id of the foreigners
#                for col, col_attr in self.table_meta.foreign_keys:
#                    if col in foreigners:
#                        c = foreigners[col]
#                        debug(c)
#                        foreign_table = c.__class__.get(c.id, connection=trans)
#                        foreign_table.set(**{col_attr: t.id})
#                        # temporary disable
#                        #trans.commit()
#                        #c.set(**{col_attr: t.id})                
#                debug('committing joins')    
#                for join_name, jv in join_values.iteritems():
#                    join_column = self.columns[join_name].meta.so_join.joinColumn
#                    # remove the _id from the end and set the table id
#                    jv[join_column[:-3]] = t.id
#                    join_table_class = jv.pop('__class__')
#                    
#                    debug(jv)
#                    if 'id' in jv:
#                        debug('updating join')                        
#                        join_table = join_table_class.get(jv.pop('id'), 
#                                                          connection=trans)
#                        join_table.set(**join)
#                    else:
#                        debug('creating join')
#                        join_table = join_table_class(connection=trans, **jv)
#                     
#                    # temporary disable
#                    #trans.commit()
#                        
#            except Exception, e:                
#                debug('rolling back changes')
#                trans.rollback()
#                #sqlhub.threadConnection = old_conn
#                sqlhub.processConnection = old_conn
#                msg = "Could not commit changes.\n" + str(e)
#                utils.message_details_dialog(msg, traceback.format_exc(), 
#                                              gtk.MESSAGE_ERROR)
#                return False      
#            else:
#                trans.commit()
#
#        sqlhub.processConnection = old_conn
#        return True
#        pass
        
#    def commit_changes_old(self):
#        """
#        commit any change made in the table editor
#        """        
##        debug("entered commit_changes")
#        # TODO: do a map through the values returned from get_tables_values
#        # and check if any of them are lists in the (table, values) format
#        # if they are then we need pop the list from the values and commit
#        # the current table, set the foreign key of the sub table and commit 
#        # it
#        # TODO: if i don't set the connection parameter when i create the
#        # table then is it really using the transaction, it might be if 
#        # sqlhub.threadConnection is set to the transaction
#        values = self.get_values_from_view()
#        old_conn = sqlhub.getConnection()
#        trans = old_conn.transaction()
#        #sqlhub.threadConnection = trans
#        sqlhub.processConnection = trans
#        for v in values:
#            # make sure it's ok to commit these values            
#            if not self.test_values_before_commit(v):                
#                continue                
#            # first pop out columns in table_meta.foreign_keys so we can
#            # set their foreign key id later                
#            foreigners = {}
#            for col, col_attr in self.table_meta.foreign_keys:
#                # use has_key to check the dict and not the table, 
#                # see ModelRowDict.__contains__
#                if v.has_key(col): 
#                    foreigners[col] = v.pop(col)
#            try:                
#                if 'id' in v:# updating row
#                    t = self.table.get(v["id"], connection=trans)
#                    del v["id"]
#                    t.set(**v)
#                else: # adding row
#                    debug('adding row: ' + str(v))
#                    t = self.table(connection=trans, **v)
#                #print 'foreign: ' + str(foriegners)
#                # set the foreign keys id of the foreigners
#                trans.commit()
#                for col, col_attr in self.table_meta.foreign_keys:
#                    if col in foreigners:
#                        c = foreigners[col]
#                        debug(c)
#                        foreign_table = c.__class__.get(c.id, connection=trans)
#                        foreign_table.set(**{col_attr: t.id})
#                        trans.commit()
#                        #c.set(**{col_attr: t.id})                
#            except Exception, e:                
#                trans.rollback()
#                #sqlhub.threadConnection = old_conn
#                sqlhub.processConnection = old_conn
#                msg = "Could not commit changes.\n" + str(e)
#                utils.message_details_dialog(msg, traceback.format_exc(), 
#                                              gtk.MESSAGE_ERROR)
#                return False      
##            else:      
##                #trans.commit()
##                debug("commited: " + str(v))
##                for col, col_attr in self.table_meta.foreign_keys:
##                    if col in foreigners:
##                        c = foreigners[col]
##                        try:
##                            # have to do some voodoo here b/c if c was created 
##                            # from a different connection or a different t
##                            # transaction then there will be problems
##                            foreign_table = c.__class__.get(t.id, connection=trans)
##                            foreign_table.set(**{col_attr: t.id})
##                            trans.commit()
##                            #c.set(**{col_attr: t.id})
##                        except:
##                            trans.rollback()
##                            msg = "could not set foreign table: %s.%s" \
##                                  % (col, col_attr)
##                            utils.message_details_dialog(msg, 
##                                                         traceback.format_exc(),
##                                                         gtk.MESSAGE_ERROR)
##                            return False
##                #trans.commit()
#                
#        #sqlhub.threadConnection = old_conn
#        sqlhub.processConnection = old_conn
#        return True
    

    def on_view_move_cursor(self, view, step, count, data=None):
        #debug('move_cursor')
        pass
        
    
    def on_cursor_changed(self, view, data=None):
        # TODO: this should be reworked to have some sort of information
        # panel for the editor, similar to eclipse
        path, column = view.get_cursor()
        if column is None:
            return
        editor_status_context_id = 5698
        if column.meta.editor is not None:
            bauble.app.gui.statusbar.push(editor_status_context_id,
                                          'Press enter to edit the %s' \
                                          % column.get_property('title'))
        else:
            bauble.app.gui.statusbar.pop(editor_status_context_id)


    def create_view_columns(self):                
        columns = TreeViewEditorDialog.ColumnDict()        
        # create tree columns for table columns
        for name, col in self.table.sqlmeta.columns.iteritems():
            #debug("create_view_column: %s -- %s", name, col)
            if name.startswith("_"): # private/not editable
                continue
            title = name.replace('_', '__')
            if isinstance(col, SOEnumCol):
                column = ComboColumn(self, title, so_col=col)
                model = gtk.ListStore(str)
                for v in column.meta.so_col.enumValues:
                    model.append([v])
                column.model = model
            elif isinstance(col, SOBoolCol):
                column = ToggleColumn(self, title, so_col=col)
            else:
                column = TextColumn(self, title, so_col=col)
            columns[name] = column
            
            # set handlers for the view
            if isinstance(column, TextColumn):
                column.renderer.connect('edited', self.on_column_edited,
                                        column)
            elif isinstance(column, ToggleColumn):
                column.renderer.connect('toggled', self.on_column_toggled,
                                        column)
        
        for join in self.table.sqlmeta.joins:
            # we create columns for the joins here but we remove the column
            # once the view is created if there isn't an external editor, this
            # allows classes that extend this editor class to setup the editor
            # in their constructor like they would do with normal column
            #debug(join)            
            name = join.joinMethodName
            # FIXME: right now we only support editing of single join though 
            # this could be a problem if the editor returns multiple values
            if not isinstance(join, SOSingleJoin):                         
                continue
            #debug(join.joinColumn)            
            debug('join: %s' % name)            
            column = TextColumn(self, title, so_join=join)
            column.renderer.connect('edited', self.on_column_edited, column)
            columns[name] = column
            #columns.joins.append(name)
            
        return columns
        
        
    def on_column_toggled(self, renderer, path, column):
        if column.dirty:
            self.set_dirty(True)
    
    
    def on_column_edited(self, renderer, path, new_text, column):
        debug("on_column_edited: '%s'" % new_text)
        #if new_text != "": # only set dirty if something has changed
        #    self.set_dirty(True)
        if column.dirty:
            debug('set dirty')
            self.set_dirty(True)
        else:
            debug('not dirty')
        
        # edited the last row so add a new one,
        # i think this may a bit of a bastardization of path but works for now
        model = self.view.get_model()
        if new_text != "" and int(path) == len(model)-1:
            self.add_new_row()
            self.dummy_row = True
    
        
    def add_new_row(self, row=None):
        model = self.view.get_model()
        if model is None: raise ception("no model in the row")
        if row is None:
            row = self.table        
        model.append([ModelRowDict(row, self.columns, self.defaults)])        


    def set_visible_columns_from_prefs(self, prefs_key):
        visible_columns = prefs[prefs_key]
        if visible_columns is None: 
            return
        # reset all visibility from prefs
        for name, col in self.columns.iteritems():            
            if name in visible_columns:
                col.set_visible(True)
            elif not col.meta.required: 
                col.set_visible(False)

    
    def get_column_widths_from_prefs(self):
        if self.column_width_pref is None or self.column_width_pref not in prefs:
            return {}        
        return prefs[self.column_width_pref]


    def store_column_widths(self):
        """
        store the column widths as a dict in the preferences, self
        if self.column_width_pref is None then just don't store the prefs
        """
        if self.column_width_pref is None:
            return 
                    
        width_dict = {}
        for name, col in self.columns.iteritems():
            width_dict[name] = col.get_property('width')        
        
        #debug(width_dict)
        pref_dict = prefs[self.column_width_pref]
        if pref_dict is None:
            prefs[self.column_width_pref] = width_dict
        else: 
            pref_dict.update(width_dict)
            prefs[self.column_width_pref] = pref_dict

        
    def store_visible_columns(self):
        """
        get the currently visible columns and store them to the preferences
        """
        if self.visible_columns_pref == None:
            return
        visible = []
        for c in self.view.get_columns():
            if c.get_visible():
                visible.append(c.name)
        prefs[self.visible_columns_pref] = visible
        #prefs.save()
        
