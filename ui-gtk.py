import webbrowser
import os
import subprocess

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

gi.require_version('GooCanvas', '2.0')
from gi.repository import GooCanvas

from extract_references import get_paper_path, get_references

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

        label1 = Gtk.Label(label=title, xalign=0)
        label2 = Gtk.Label(label=authors, xalign=0)
        vbox.pack_start(label1, True, True, 0)
        vbox.pack_start(label2, True, True, 0)

        button = Gtk.Button.new_with_label("🌐")
        button.connect("clicked", self.on_go_to_url)
        hbox.pack_start(button, False, True, 0)

    def on_go_to_url(self, button):
        webbrowser.open_new(self.reference["URL"])

class PaperWidget(Gtk.Box):

    def __init__(self, paper_path, pdf_path=None):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL)

        self.paper_path = paper_path

        if not self.paper_path:

            title = Gtk.Label(label="No paper selected")
            self.pack_start(title,True,True,0)
            return



        self.thumbnail_path = os.path.join(paper_path, "thumbnail.jpg")

        # create the thumbnail if needed
        if not os.path.isfile(self.thumbnail_path) and pdf_path:
                cmd_line = f"convert -thumbnail 200x200 -density 300 -background white -alpha remove {pdf_path}[0] {self.thumbnail_path}"
                subprocess.run(cmd_line,shell=True)

        if os.path.isfile(self.thumbnail_path):
            thumbnail = Gtk.Image()
            thumbnail.set_from_file(self.thumbnail_path)
            self.pack_start(thumbnail,True,True,0)

        title = Gtk.Label(label="Paper's title")
        self.pack_start(title,True,True,0)



class BiblioSidebar(Gtk.Box):

    def __init__(self):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL)


        self.active_paper = PaperWidget(paper_path=None)
        self.pack_start(self.active_paper, True, True, 0)

        ref_label = Gtk.Label(label="List of references")
        self.pack_start(ref_label, True, True, 0)

        scroll_ref_list = Gtk.ScrolledWindow()
        scroll_ref_list.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll_ref_list.set_min_content_width(200)
        self.pack_start(scroll_ref_list, True, True, 0)

        self.refs_list = Gtk.ListBox()

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

        scroll_ref_list.add(self.refs_list)

    @staticmethod
    def replace_widget(old, new):
        parent = old.get_parent()

        props = {}
        for key in Gtk.ContainerClass.list_child_properties(type(parent)):
            props[key.name] = parent.child_get_property(old, key.name)

        parent.remove(old)
        parent.add(new)

        for name, value in props.items():
            parent.child_set_property(new, name, value)

    def set_active_paper(self, paper_widget):

        self.pack_start(paper_widget, True, True, 0)
        #self.replace_widget(self.active_paper, paper_widget)
        self.active_paper = paper_widget

    def set_reference_list(self, pdf_filepath):
        refs = get_references(pdf_filepath)
        print("Nb refs: %s" % len(refs))

        for ref in refs:
            self.refs_list.add(ReferenceRow(ref))
        self.refs_list.show_all()


class BiblioMapperWindow(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="BiblioMapper")
        self.set_border_width(10)

        self.connect("drag-data-received", self.got_data_cb)
        self.drag_dest_set_target_list(None)
        self.drag_dest_add_text_targets()

        box_outer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.add(box_outer)

        self.canvas = Gtk.DrawingArea()
        self.sidebar = BiblioSidebar()

        box_outer.pack_start(self.sidebar, False, True,0)
        box_outer.pack_start(self.canvas, True, True,0)


    def got_data_cb(self, wid, context, x, y, data, info, time):
        if info == 0:
            filepath = data.get_text().strip()[7:] # remove trailling characters, and remove 'file://' TODO -> probably better way to process the URI!
            print("Loading references for %s" % filepath)

            paper_path = get_paper_path(filepath)

            self.sidebar.set_active_paper(PaperWidget(paper_path, pdf_path=filepath))

            self.sidebar.set_reference_list(filepath)

    
        context.finish(True, False, time)

win = BiblioMapperWindow()
win.connect("destroy", Gtk.main_quit)
win.show_all()
Gtk.main()
