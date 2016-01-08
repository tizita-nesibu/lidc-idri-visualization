# -*- coding: utf-8 -*-
"""
Created on Mon May 20 14:30:47 2015

@author: tizita nesibu
"""

import Tkinter
import tkFileDialog

from os import listdir
from os.path import isfile, join, dirname, abspath

import dicom
import dicom.contrib.pydicom_Tkinter as pydicom_Tkinter

import cv2
import numpy as np

class DicomImgData:
    
    def __init__(self, dicom_data):
        self.components = [] 
        
        if ('RescaleIntercept' in dicom_data):
            self.RescaleIntercept = dicom_data.RescaleIntercept
            self.components.extend(['RescaleIntercept'])
        
        if ('RescaleSlope' in dicom_data):
            self.RescaleSlope = dicom_data.RescaleSlope
            self.components.extend(['RescaleSlope'])
        
        if ('WindowCenter' in dicom_data):
            self.WindowCenter = dicom_data.WindowCenter
            self.components.extend(['WindowCenter'])
        
        if ('WindowWidth' in dicom_data):
            self.WindowWidth = dicom_data.WindowWidth
            self.components.extend(['WindowWidth'])
     
        self.pixel_array = np.copy(dicom_data.pixel_array)
        
        return

    def __contains__(self, key):
        return key in self.components

            
class MainGui_tk(Tkinter.Tk):
    
    def __init__(self, parent):
        Tkinter.Tk.__init__(self, parent)
        
        self.parent = parent
        self.visualframe = Tkinter.Frame(self)
        self.controlframe = Tkinter.Frame(self)
        self.dicom_file_path = []
        self.dicom_data = []
        self.dicom_photo_ref = []
        self.dicom_on_canvas = []
        self.dicom_img_first = True
        self.initialize_gui()


    def initialize_gui(self):
        self.grid()        
        self.visualframe.grid(column=0,row=0,sticky='N')
        self.controlframe.grid(column=0,row=1,sticky='SEW')
        
        # Create canvas for image
        self.canvas = Tkinter.Canvas(self.visualframe, width=640, height=480,bg='white')
        self.canvas.grid(column=0, row=0)
        self.canvas_shape = (640,512)
        
        # create listbox for list of dicom images
        self.listbx = Tkinter.Listbox(self.visualframe, height=30)
        self.listbx.grid(column=1,row=0)
        self.listbx.bind("<Double-Button-1>", self.OnlistboxClick)
        
        #create the scroll bar
        self.scrollbar = Tkinter.Scrollbar(self.visualframe, orient=Tkinter.VERTICAL)
        self.scrollbar.grid(column=2,row=0,sticky='NS')

        #associate the scroll         
        self.listbx.config(yscrollcommand=self.scrollbar.set)
        self.scrollbar.config(command=self.listbx.yview)
        

        self.load_button = Tkinter.Button(self.controlframe,
                                          text=u'Load DICOM',
                                          command=self.OnButtonLoadDicom)
        self.load_button.grid(column=1, row=0,rowspan=2, padx=5, pady=5, sticky='NEWS')
        
        self.clear_button = Tkinter.Button(self.controlframe,
                                          text=u'Clear Data',
                                          command=self.OnButtonClearData)
        self.clear_button.grid(column=2, row=0, rowspan=2, padx=5, pady=5, sticky='NEWS')
        
        logo_fname = dirname(abspath(__file__)) + '/logo.gif'
        self.img = Tkinter.PhotoImage(file=logo_fname)
        self.logo_canvas = Tkinter.Canvas(self.controlframe, 
                                          width=125, height=85, bg='white')
        self.logo_canvas.grid(column=0, row=0, rowspan=2, sticky='NEWS')
        self.image_on_canvas = self.logo_canvas.create_image(0,0, anchor='nw', image=self.img)
        
        self.resizable(False, False)        
        self.visualframe.update()
        self.controlframe.update()
        self.update()
        self.geometry(self.geometry())
        
    def OnButtonLoadDicom(self):
        
        self.dicom_file_path = tkFileDialog.askdirectory(initialdir='/opt/DataSet/') + '/'
        try:
            flist = [f for f in listdir(self.dicom_file_path) if (isfile(join(self.dicom_file_path,f)) and f.endswith('.dcm')) ]
        except IOError:
            print "ERROR, openning files in %s " % self.dicom_file_path
            self.listbx.delete(0, Tkinter.END)
            return
        
        self.listbx.delete(0, Tkinter.END)

        flist.sort()
        for f in flist:
            self.listbx.insert(Tkinter.END, f)
        
        return

    def OnlistboxClick(self, event):
        lstbx = event.widget
        selection=lstbx.curselection()
        if len(selection) > 0:
            value = lstbx.get(selection[0])
            #print "selection:", selection, ": '%s'" % value
            full_file_name = self.dicom_file_path + "/" + value
            self.dicom_data = dicom.read_file(full_file_name)

            dicom_img_data = DicomImgData(self.dicom_data)
            
            w_ratio = dicom_img_data.pixel_array.shape[1]/self.canvas_shape[1]
            h_ratio = dicom_img_data.pixel_array.shape[0]/self.canvas_shape[0]

            if ((h_ratio > 1) or (w_ratio > 1) ):

                if (w_ratio > h_ratio):
                    new_sz = (int(dicom_img_data.pixel_array.shape[1]/w_ratio),
                              int(dicom_img_data.pixel_array.shape[0]/w_ratio))
                else:
                    new_sz = (int(dicom_img_data.pixel_array.shape[1]/h_ratio),
                              int(dicom_img_data.pixel_array.shape[0]/h_ratio))                          
                dicom_img_data.pixel_array = cv2.resize(dicom_img_data.pixel_array, new_sz)

            self.dicom_photo_ref = pydicom_Tkinter.get_tkinter_photoimage_from_pydicom_image(dicom_img_data)
            
            if self.dicom_img_first:
                self.dicom_on_canvas = self.canvas.create_image(0,0,anchor='nw', image=self.dicom_photo_ref)
                self.dicom_img_first = False
            else:
                self.canvas.itemconfig(self.dicom_on_canvas, image=self.dicom_photo_ref)
                
        pass
    
    def OnButtonClearData(self):
        
        if not self.dicom_img_first:
            #clear image
            self.canvas.delete('all')
            self.canvas.itemconfig(self.dicom_on_canvas, image=self.dicom_photo_ref)
            self.dicom_img_first = True
        self.listbx.delete(0, Tkinter.END)
        pass

        
def main2():
    print "Python Gui tutorials! ;)!"
    simple_app = SimpleApp_tk(None)
    simple_app.title("Lung-ct Classification")
    simple_app.mainloop()

def main():
    '''
    master = Tkinter.Tk()

    scrollbar = Tkinter.Scrollbar(master)
    scrollbar.pack(side=Tkinter.RIGHT, fill=Tkinter.Y)

    listbox = Tkinter.Listbox(master, yscrollcommand=scrollbar.set)
    for i in range(1000):
        listbox.insert(Tkinter.END, str(i))
        listbox.pack(side=Tkinter.LEFT, fill=Tkinter.BOTH)

    scrollbar.config(command=listbox.yview)

    Tkinter.mainloop()
    return
    '''
    main_app = MainGui_tk(None)
    main_app.title("LIDC LUNG-CT Visualizer")
    main_app.mainloop()

if __name__ == "__main__":
    main()




class SimpleApp_tk(Tkinter.Tk):
    def __init__(self, parent):
        Tkinter.Tk.__init__(self, parent)
        
        self.parent = parent
        self.initialize()

    def initialize(self):
        self.grid()
        
        self.txtVariable = Tkinter.StringVar()
        self.txtinput = Tkinter.Entry(self, textvariable=self.txtVariable) #passing self as parent parameter
        self.txtinput.grid(column=0, row=0, sticky='EW')
        self.txtinput.bind("<Return>", self.OnPressEnter)
        self.txtVariable.set(u"Enter text here")
        
        self.button = Tkinter.Button(self, text=u'Click me!',
                                     command=self.OnButtonClick)
        self.button.grid(column=1, row=0)
        
        self.labelVariable = Tkinter.StringVar()
        self.label = Tkinter.Label(self, textvariable=self.labelVariable,
                                   anchor='w',fg='white',bg='blue')
        self.label.grid(column=0, row=1, columnspan=2,sticky='EW')
        self.labelVariable.set(u"Hello World!")
        
        self.grid_columnconfigure(0,weight=1)
        self.resizable(True, False)
        self.update()
        self.geometry(self.geometry())
        
        self.txtinput.focus_set()
        self.txtinput.selection_range(0, Tkinter.END)
    
    def OnButtonClick(self):
        self.labelVariable.set(self.txtVariable.get()+" (button-click) ")
        self.txtinput.focus_set()
        self.txtinput.selection_range(0, Tkinter.END)
    
    def OnPressEnter(self,event):
        self.labelVariable.set(self.txtVariable.get() + " (pressed-enter) ")
        self.txtinput.focus_set()
        self.txtinput.selection_range(0, Tkinter.END)