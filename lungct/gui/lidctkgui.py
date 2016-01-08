# -*- coding: utf-8 -*-
"""
Created on Mon May 20 14:30:47 2015

@author: tizita nesibu
"""

import Tkinter
import tkFileDialog
import tkMessageBox

from PIL import Image, ImageTk

from os import listdir
from os.path import isfile, join, dirname, abspath, basename

import dicom
import dicom.contrib.pydicom_Tkinter as pydicom_Tkinter


import cv2
import numpy as np
import time

from ..structs.visstructs import DicomImgData
from ..parser.lidcxmlparser import LIDCXmlParser, LIDCXmlHeader
from ..structs.visstructs import PatientCTSeries, AnnotatedCT

#b
class CustomMessageBox(Tkinter.Tk):

    def __init__(self, parent, txtmsg="Loading file..."):
        Tkinter.Tk.__init__(self, parent)
        self.parent = parent
        self.frame = Tkinter.Frame(self)
        
        self.grid()
        self.frame.grid(column=0,row=0,sticky='N')
        
        self.message = txtmsg
        
        self.lbl_txt = txtmsg
        
        #adding label on a frame
        self.label = Tkinter.Label(self.frame, text="", font=("Helvetica", 10))
        self.label.grid(row=0, column=0, rowspan=1, padx=5, pady=5, sticky='NEWS') #padx & pady is to put space
                                                                #in x and y direction 

        self.label.config(text=txtmsg, width=40)
        
        self.title("LIDC LUNG-CT")
        self.resizable(False, False)        
        self.update()
        
        self.break_loop = False
        #self.geometry(self.geometry())
            
class LIDCInterfaceTk(Tkinter.Tk):#inharits from Tkinter.Tk
    
    def __init__(self, parent, lung_ct_path="/opt/DataSet/lung-ct/"):#this path is
                              #just for initialization(replaced when class called)
        Tkinter.Tk.__init__(self, parent)       
        
        self.parent = parent
        self.visualframe = Tkinter.Frame(self)#frame to hold image and list of CT slices
        self.controlframe = Tkinter.Frame(self)#frame to hold buttons, labels etc.
        self.optionsframe = Tkinter.Frame(self)#frame to hold checkboxes

    #class variables are initialized  by saying None
        self.xml_filename = None
        self.patient_no = None


        self.dicom_data = []
        self.dicom_photo_ref = None
        self.dicom_on_canvas = None
        self.dicom_img_first = True
        self.initialize_gui()
        
        #initialize data structure related to the xml parser
        self.xml_parser = None #LIDCXmlParser()
        self.lung_ct_rootpath = lung_ct_path
        self.patient_ct_series = []
        
        self.selected_rad = []
        self.radio_button_ctrl_vars = []
        
        self.active_ct_indx = -1
        

    
    def initialize_gui(self):
        #?????the outer container is Tk. it containes all the frames. and frams could contain canvas??????
        self.grid()        
        self.visualframe.grid(column=0,row=0,sticky='N')
        self.controlframe.grid(column=0,row=1,sticky='SEW')
        self.optionsframe.grid(column=1,row=0,sticky='SEW')
        
        # Create canvas for image and add it to the parent Frame called visualframe 
        self.canvas = Tkinter.Canvas(self.visualframe, width=640, height=512,bg='white')
        self.canvas.grid(column=0, row=0)
        self.canvas_shape = (640,512)
        
        # create listbox for list of dicom images and add it to the parent Frame called visualframe 
        self.listbx = Tkinter.Listbox(self.visualframe, height=40)
        self.listbx.grid(column=1,row=0)
        self.listbx.bind("<Double-Button-1>", self.OnlistboxClick)#bind indicates event handler(when double 
                                             #clicked calls OnlistboxClick function)
        
        #create the scroll bar for listbox
        self.scrollbar = Tkinter.Scrollbar(self.visualframe, orient=Tkinter.VERTICAL)
        self.scrollbar.grid(column=2,row=0,sticky='NS')

        #associate the scroll with listbox and put event for scrollbar        
        self.listbx.config(yscrollcommand=self.scrollbar.set)
        self.scrollbar.config(command=self.listbx.yview)
        

        self.load_button = Tkinter.Button(self.controlframe,
                                          text=u'Load LIDC XML',
                                          command=self.OnButtonLoadXml) #command is event handler
        self.load_button.grid(column=1, row=1,rowspan=2, padx=5, pady=5, sticky='NEWS')
        
        self.clear_button = Tkinter.Button(self.controlframe,
                                          text=u'Clear Data',
                                          command=self.OnButtonClearData)
        self.clear_button.grid(column=2, row=1, rowspan=2, padx=5, pady=5, sticky='NEWS')
        
        self.logo_fname = dirname(abspath(__file__)) + '/../data/logo.gif' #to get the path of the logo image
        self.img = Tkinter.PhotoImage(file=self.logo_fname)
        
        self.logo_canvas = Tkinter.Canvas(self.controlframe, 
                                          width=125, height=85, bg='white')
        self.logo_canvas.grid(column=0, row=0, rowspan=2, sticky='NEWS')
        self.image_on_canvas = self.logo_canvas.create_image(0,0, anchor='nw', image=self.img)
        
        self.options_controls = []
        
        #the following 4 lines are just to hold space to widen the frame width after the list box(doesn't do anything)
        self.dummy_label0 = Tkinter.Label(self.optionsframe, text=" "*15)
        self.dummy_label0.grid(row=0, column=0, rowspan=1, padx=5, pady=5, sticky='NEWS')
        self.dummy_label1 = Tkinter.Label(self.optionsframe, text=" "*15)
        self.dummy_label1.grid(row=0, column=1, rowspan=1, padx=5, pady=5, sticky='NEWS')
        
        #self.dummy_label2 = Tkinter.Label(self.optionsframe, text=" "*15)
        #self.dummy_label2.grid(row=0, column=2, rowspan=1, padx=5, pady=5, sticky='NEWS')
        
        self.resizable(False, False)  
        
        #to set the Tk's size according to the size of frames added to it(to make it's size dinamic),
        #update() method is used. and set the self.geometry() to self.geometry() method insted of passing 
        #it the exact size.
        self.visualframe.update()
        self.controlframe.update()
        self.optionsframe.update()
        self.update()
        
        self.geometry(self.geometry())
   
    def UpdateOptionsFrame(self):
        n_rads = len(self.xml_parser.rad_annotations) #len of rad_annotations to konw the nbr of radiologistes 
        self.options_controls = []
        self.selected_rad = []
        for nr in range(n_rads):
            caption = "Rad %d "%(nr+1)
            cntrl_var = Tkinter.IntVar() #declare int variable of Tkinter(not same as int)
                 #to control(set) the checkbutton's attribut called variable outside of Checkbutton func 
            self.options_controls.append(Tkinter.Checkbutton(self.optionsframe, text=caption, variable=cntrl_var))
            cntrl_var.set(0) # to uncheck the check box(by default), if we set it 1 it'll be checked
                            # will be set after the function self.CheckButtonOption is called
            self.options_controls[nr].bind("<Button-1>", lambda event, indx=nr: self.CheckButtonOption(event,indx))#indx-to identifay which checkbox triggered the event
            col,rw = nr%2,nr/2
            self.options_controls[nr].grid(column=col, row=rw,rowspan=1, padx=5, pady=5, sticky='NEWS')
            self.radio_button_ctrl_vars.append(cntrl_var) #to save the cntrl_var for later use

        #self.resizable(False, False))
        self.optionsframe.update()
        self.update()
        self.geometry(self.geometry())
        return
        
    #called when Checkbutton(check box) is clicked to drow the specified radiologistes annotation
    def CheckButtonOption(self, event, indx):
        #print "Clicked on button identified as [%d] "%indx
        if (not (self.active_ct_indx == -1)): #if something is displayed(!= - 1)(if it is -1 -> noting is displayed)
            
            ant_ct = self.patient_ct_series.annotated_cts[self.active_ct_indx] #to get img info of the specified 
                                                        #index by self.active_ct_indx variable
            
            rad_indx = []
            
            for ix, r in enumerate(self.radio_button_ctrl_vars): #ix is index, r is list's value 
                                                #i.e.which cntrl_var in the list(to get it's value we've to use get())
                if (ix == indx): #handle the variable of the clicked check box properly
                    if (r.get() == 0): # means check box is clicked but will be set to 1 after it gets out of this fun 
                       rad_indx.append(ix)
                elif (r.get() == 1): # means check box is checked previously
                    rad_indx.append(ix) #to identify the radiologist
            cv_mat = ant_ct.draw(rad_indx_lst=rad_indx, draw_nodules=True, draw_small =True, draw_non=True)#to dorw
            #the radiologistes annotation on to the specified img by variable ant_ct
            self.SetImage2Canvas(cv_mat) #displays the annotated img on canvas
        return

    
    #this method is called when load botton(Load LIDC XML) is clicked    
    def OnButtonLoadXml(self):
        FILEOPENOPTIONS = dict(defaultextension='*.xml',           #it is when the dialogbox appears, to show us only 
                  filetypes=[('Xml file','*.xml'),('All files','*.*')]) # the xml files in the selected folder
        self.xml_filename = tkFileDialog.askopenfilename(initialdir='./', **FILEOPENOPTIONS)
        self.active_ct_indx = -1  #means noting is displayed on canvas
        if (len(self.xml_filename) > 0):
            
            #do stuff
            msg_bx = CustomMessageBox(parent=None, txtmsg="Loading and parsing necessary data...") 
            self.withdraw()      #to not display the image visualizer window when the msg_bx is displayed
            #msg_bx.lbl_txt.set("Loading and parsing necessary data")
            bname = basename(self.xml_filename)   #(python's fun)-> to extract the file neame from the path
            self.patient_no = int(bname[:bname.find('.')])   #to extract patient_no e.g. int(0068) -> 68
            
            
            self.xml_parser = LIDCXmlParser()
            self.xml_parser.set_xml_file(self.xml_filename)
            self.xml_parser.parse()    #parses xml file and fills the data structure
           
            self.patient_ct_series = PatientCTSeries(dt_root_path=self.lung_ct_rootpath,
                                                     patient_no=self.patient_no)
            
            self.patient_ct_series.populate_from_xmlparser(self.xml_parser)
            
                    
            msg_bx.destroy()
            self.deiconify()  #?????????????????
            self.UpdateOptionsFrame()
            
            #do the following
            self.listbx.delete(0, Tkinter.END)
            for ct in self.patient_ct_series.annotated_cts:
                self.listbx.insert(Tkinter.END, ct.alias)
        return

    def SetImage2Canvas(self, cv_mat):
        w_ratio = cv_mat.shape[1]/self.canvas_shape[1]
        h_ratio = cv_mat.shape[0]/self.canvas_shape[0]

        if ((h_ratio > 1) or (w_ratio > 1) ):
            if (w_ratio > h_ratio):
                new_sz = (int(cv_mat.shape[1]/w_ratio),
                          int(cv_mat.shape[0]/w_ratio))
            else:
                new_sz = (int(cv_mat.shape[1]/h_ratio),
                          int(cv_mat.shape[0]/h_ratio))                          
            
            cv_mat = cv2.resize(cv_mat, new_sz) #e.g. new_sz = (30,50)
        
        #img = Image.fromarray(cv_mat)
        #imgtk = ImageTk.PhotoImage(image=img)
        cv2.imwrite('tmp_01010.ppm',cv_mat)
        self.dicom_photo_ref = Tkinter.PhotoImage(file='tmp_01010.ppm')#ImageTk.PhotoImage(image=img)
        
        if self.dicom_img_first:
            self.dicom_on_canvas = self.canvas.create_image(0,0, anchor='nw', image=self.dicom_photo_ref)
            self.dicom_img_first = False
        else:
            self.canvas.itemconfig(self.dicom_on_canvas, image=self.dicom_photo_ref)
            
   #this method is called when the list of image in listbox is clicked     
    def OnlistboxClick(self, event):
        lstbx = event.widget   #????????????????????????  
        selection=lstbx.curselection()
        if len(selection) > 0:
            value = lstbx.get(selection[0])
            #print "selection:", selection, ": '%s'" % value
            ct_indx = self.patient_ct_series.indx_lookup_alias[value]
            ant_ct = self.patient_ct_series.annotated_cts[ct_indx]
            
            self.active_ct_indx = ct_indx
            rad_indx = []
            
            for ix, r in enumerate(self.radio_button_ctrl_vars):
                if (r.get() == 1):
                    rad_indx.append(ix)
            cv_mat = ant_ct.draw(rad_indx_lst=rad_indx, draw_nodules=True, draw_small =True, draw_non=True)
            self.SetImage2Canvas(cv_mat)
        else:
            self.active_ct_indx = -1
        return
    #this method is called when the clear_botton(Clear Data) botton is clicked  
    def OnButtonClearData(self):
        
        if not self.dicom_img_first:
            #clear image
            self.canvas.delete('all')
            self.canvas.itemconfig(self.dicom_on_canvas, image=self.dicom_photo_ref)
            self.dicom_img_first = True
        self.listbx.delete(0, Tkinter.END)
        
        for ctrl in self.options_controls:
            ctrl.destroy()
        self.options_controls = []
        self.radio_button_ctrl_vars = []
        
        self.active_ct_indx = -1
        
        self.optionsframe.update()
        self.update()
        pass
    