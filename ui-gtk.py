import webbrowser

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

gi.require_version('GooCanvas', '2.0')
from gi.repository import GooCanvas

from extract_references import get_references

class ReferenceRow(Gtk.ListBoxRow):
    def __init__(self, reference):
        super(Gtk.ListBoxRow, self).__init__()

        self.reference = reference

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=50)
        self.add(hbox)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        hbox.pack_start(vbox, True, True, 0)

        title = reference["title"]
        title = title if len(title) < 40 else title[:39] + "..."

        authors = reference["author"]
        authors = ", ".join(authors) if len(authors) < 3 else authors[0] + " et al."

        label1 = Gtk.Label(title, xalign=0)
        label2 = Gtk.Label(authors, xalign=0)
        vbox.pack_start(label1, True, True, 0)
        vbox.pack_start(label2, True, True, 0)

        button = Gtk.Button.new_with_label("🌐")
        button.connect("clicked", self.on_go_to_url)
        hbox.pack_start(button, False, True, 0)

    def on_go_to_url(self, button):
        webbrowser.open_new(self.reference["URL"])



class OntoBiblioWindow(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="ListBox Demo")
        self.set_border_width(10)

        self.connect("drag-data-received", self.got_data_cb)
        self.drag_dest_set_target_list(None)
        self.drag_dest_add_text_targets()

        box_outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add(box_outer)


        ref_label = Gtk.Label(label="List of references")
        box_outer.pack_start(ref_label, True, True, 0)

        self.refs_list = Gtk.ListBox()
#        items = "This is a sorted ListBox Fail".split()
#
#        for item in items:
#            listbox_2.add(ListBoxRowWithData(item))
#
#        def sort_func(row_1, row_2, data, notify_destroy):
#            return row_1.data.lower() > row_2.data.lower()
#
#        def filter_func(row, data, notify_destroy):
#            return False if row.data == "Fail" else True
#
#        listbox_2.set_sort_func(sort_func, None, False)
#        listbox_2.set_filter_func(filter_func, None, False)
#
#        def on_row_activated(listbox_widget, row):
#            print(row.data)
#
#        listbox_2.connect("row-activated", on_row_activated)

        box_outer.pack_start(self.refs_list, True, True, 0)
        self.refs_list.show_all()

    def got_data_cb(self, wid, context, x, y, data, info, time):
        if info == 0:
            filepath = data.get_text().strip()[7:] # remove trailling characters, and remove 'file://' TODO -> probably better way to process the URI!
            print("Loading references for %s" % filepath)

            refs = get_references(filepath)
            print("Nb refs: %s" % len(refs))

            for ref in refs:
                self.refs_list.add(ReferenceRow(ref))
            self.refs_list.show_all()


        context.finish(True, False, time)

win = OntoBiblioWindow()
win.connect("destroy", Gtk.main_quit)
win.show_all()
Gtk.main()
