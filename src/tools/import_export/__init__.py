#
# exporter module
#

import sys, os
import threading
import gtk
import sqlobject
from tables import tables
import utils
from bauble import bauble

# TODO: load a list of all exporters, or require the exporters to register
# themselves with us, right now just hard code them in
#
# TODO: convert this to use threading, could just include the threading
# in the exporter class and have the Exporter subclasses be the workers,
# then the progress dialog could be done one time
#
# TODO: be able to dynamically add exporters/importers depending on which 
# the modules available in this directory, should be able to check for 
# "importer" and "exporter" in the module to see if the module provides
# an importer/exporter
#
# TODO: popup a message dialog that says "Success." or something
# to indicate everything was imported without problems


class IEDialog(gtk.Dialog):
    def __init__(self, title="Export", parent=None,
                 flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                 buttons=(gtk.STOCK_OK, gtk.RESPONSE_OK,
                          gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)):
        gtk.Dialog.__init__(self, title, parent, flags, buttons)
        self.current_ie = None
        self.connect("response", self.on_response)

    
    def create_gui(self):
        self.vbox.set_spacing(10)
        self.type_combo = gtk.combo_box_new_text()
        self.type_combo.connect("changed", self.on_changed_type_combo)
        self.vbox.pack_start(self.type_combo)
        
        sep = gtk.HSeparator()
        self.vbox.pack_start(sep, False, False)
        
        self.show_all()
        
        
    def on_changed_type_combo(self, combo, data=None):        
        if self.current_ie is not None:
            self.vbox.remove(self.current_ie)
        self.current_ie = self.factory.create(combo.get_active_text(), self)
        self.vbox.pack_start(self.current_ie)
        self.show_all()

        
    def on_response(self, dialog, response, data=None):
        if response == gtk.RESPONSE_OK:
            self.current_ie.start()
            #self.current_ie.run()


class ImportDialog(IEDialog):
    def __init__(self, title="Import", parent=None,
        flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
        buttons=(gtk.STOCK_OK, gtk.RESPONSE_OK,
                 gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)):
        IEDialog.__init__(self, title, parent, flags, buttons)
        # how do i do this automatically or instruct the super contructor to 
        # call the correct one
        self.factory = ImporterFactory
        super(ImportDialog, self).create_gui()
        self.create_gui()
        

    def create_gui(self):
        self.type_combo.append_text("Comma Separated Values")
        #conn = sqlobject.sqlhub.threadConnection.getConnection()
        conn = sqlobject.sqlhub.getConnection()
        if conn.__class__.__name__ == "MySQLConnection":
            self.type_combo.append_text("MySQL Import")
        self.type_combo.set_active(0)


class ExportDialog(IEDialog):
    def __init__(self, title="Export", parent=None,
                 flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                 buttons=(gtk.STOCK_OK, gtk.RESPONSE_OK,
                          gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)):
        IEDialog.__init__(self, title, parent, flags, buttons)
        self.factory = ExporterFactory
        super(ExportDialog, self).create_gui()
        self.create_gui()
        

    def create_gui(self):
        self.type_combo.append_text("Comma Separated Values")
        self.type_combo.set_active(0)
        
        
class IEFactory:
    
    def create(type, dialog):
        raise NotImplementedError()
    create = staticmethod(create)
    

class ExporterFactory(IEFactory):
    
    def create(exporter_type, dialog):
        if exporter_type == "Comma Separated Values":
            import iecsv
            return iecsv.CSVExporter(dialog)
    create = staticmethod(create)
        

class Exporter(gtk.VBox):
    
    def __init__(self, dialog):
        gtk.VBox.__init__(self)
        self.dialog = dialog
    
    def start(self):
        raise NotImplemtedError
    
                    
class ImporterFactory(IEFactory):
    
    def create(importer_type, dialog):
        if importer_type == "Comma Separated Values":
            import iecsv
            return iecsv.CSVImporter(dialog)
        if importer_type == "MySQL Import":
            import iemysql
            return iemysql.MySQLImporter(dialog)
    create = staticmethod(create)


class Importer(gtk.VBox):    

    def __init__(self, dialog):
        gtk.VBox.__init__(self)
        self.dialog = dialog
        
    def start(self):
        raise NotImplementedError

    