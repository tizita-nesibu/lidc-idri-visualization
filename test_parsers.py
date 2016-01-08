# -*- coding: utf-8 -*-
"""
Created on Wed Aug 12 12:16:50 2015

@author:  tizita nesibu
"""
import os, sys
import cv2
import numpy as np

from lungct.parser.lidcxmlparser import LIDCXmlParser, LIDCXmlHeader
from lungct.structs.visstructs import PatientCTSeries, AnnotatedCT
#from lungct.gui.main_gui import MainGui_tk

from lungct.gui.lidctkgui import LIDCInterfaceTk

#1

def main():
    #main_app = LIDCInterfaceTk(None, lung_ct_path="/opt/DataSet/lung-ct/")
    #main_app = LIDCInterfaceTk(None, lung_ct_path="/opt/lung_ct/LIDC/LIDC-IDRI/")
    main_app = LIDCInterfaceTk(None, 
                               lung_ct_path="C:/Users/tizita/Documents/LIDC/LIDC-IDRI")
    main_app.title("LIDC LUNG-CT Visualizer")
    main_app.mainloop()
    
    
    
    
    

mouse_button_clicked = False
selected_centroid = []

def mouseClickCallback(event, x, y, flags, param):
    global mouse_button_clicked,selected_centroid
    if event == cv2.EVENT_LBUTTONUP:
        mouse_button_clicked = True
        selected_centroid.append((x,y))
        print "Clicked on (%d, %d)"%(x,y)

#3
def main_tmp():
    global mouse_button_clicked,selected_centroid
    #patient id 192 has a problematic xml file, so it's removed for now
    #patient_id_lst = [68,71,72,88,90,91,100,118,124,129,135,137,138,143,149,159,161,162,163,164,165,166,
    #                  167,168,169,171,173,174,175,176,178,179,180,181,182,183,184,185,186,187,188,189,190,191,
    #                  193,194,197,198,200,202,203,205,207,210,211,212,213,214,217,220,221,222,223,224,225,
    #                  226,230,231,232,233,234,235,236,237,239,242,243,244,245,246,247,248,249,250,251,252,253,
    #                  254,255,256,257,258,260,261,264,265,266,267,268,270,271,272,273,274,275,276,277,278,279,
    #                  280,281,282,283,285,286,287,288,289,290,314,325,332,377,385,399,405,454,470,493,510,522,543,
    #                  559,562,568,568,576,580,610,624,766,771,772,811,818,875,921,924,939,965,994,1002,1004]
    #patient_id_lst = [332,377,385,399,470,493,559,568,580,610,772,818,939,994,1004]
    #patient_id_lst = [162,165,190,203,248,470]
    #patient_id_lst = [165,176,178,180,198,202,231,243,266,285,818]
    #patient_id_lst = [168,198,200,202,203,212,230,231,245,248,256,270,273,282,283,286,287,288,399,559,580,818]
    gt_save_root_path = "C:/Users/tizita/Desktop/CODE/Lung-msc-code/gt/"
    patient_id_lst = [72]
    for patient_id in patient_id_lst:
        print "\n\n Processing patient id %d"%patient_id        
        
        xml_dt = LIDCXmlParser(('C:/Users/tizita/Desktop/CODE/Lung-msc-code/xml_data/%04d.xml')%patient_id)#trial-xml.xml')
        xml_dt.parse()
        print xml_dt.xml_header
        patient_ct_series = PatientCTSeries(dt_root_path="C:/Users/tizita/Documents/LIDC/LIDC-IDRI/",
                                            patient_no = patient_id)
        patient_ct_series.populate_from_xmlparser(xml_dt)
    
        cv2.namedWindow("LIDC-IDRI")
        cv2.setMouseCallback("LIDC-IDRI", mouseClickCallback)
        cv2.startWindowThread() #important
        

        for trial in [1,2]:
            print "Round : ",trial
            
            mouse_button_clicked = False
            selected_centroid = []
            for ct in patient_ct_series.annotated_cts:
                
                if ct.no_consensus_annots() > 0: #if one or more rads agree
                    clusters = ct.get_nodule_clusters()
                    cv_mat = ct.draw(rad_indx_lst=range(len(xml_dt.rad_annotations)), 
                                     draw_nodules=True, draw_small=False, draw_non=False)
                    for cluster in clusters:
                        cvx_hull = cluster.convex_hull_with_margin
                        #cv2.rectangle(img, pt1, pt2, color[, thickness[, lineType[, shift]]])#
                        cv2.rectangle(img=cv_mat, pt1=cvx_hull[0], pt2=cvx_hull[3], color=(0,255,0), thickness=1)
                    
                    cv2.imshow('LIDC-IDRI', cv_mat)
                    ky = cv2.waitKey(0)
                    if ky == 27:  #Esc key
                        cv2.waitKey(1)
                        cv2.destroyAllWindows()
                        #cv2.waitKey(1)
                        break
            
            if (mouse_button_clicked):
            #create a directory in the root path
            
                dst_path = "%s/gt%04d/"%(gt_save_root_path, patient_id)
                if not os.path.exists(dst_path):
                    os.makedirs(dst_path)
            
                fo = open("%s/centroid.txt"%dst_path, "w")
                fo.write("%d\n"%len(selected_centroid))
                for (x,y) in selected_centroid:
                    fo.write("%d,%d\n"%(x,y))
                    
                fo.close()
                
                print "[%d] cluster centroid(s) defined...processing data.."%len(selected_centroid)
                for indx,ct in enumerate(patient_ct_series.annotated_cts):
                
                    if ct.no_consensus_annots() > 0:
                        ct.save_nearest_cluster(selected_centroid, indx, dst_path)
                

        print "Finished processing patient id %d"%patient_id

# 2
           
def main_tmp2():

    xml_dt = LIDCXmlParser() #parses xml file and fills the data structure
    xml_dt.set_xml_file("C:/Users/tizita/Desktop/CODE/Lung-msc-code/xml_data/0072.xml")#one patient xml data is passed
    xml_dt.parse()                                                           #0068
    
   # print xml_dt
    #-----------------------------------------------------------
    print "\n"*2
    patient_series = PatientCTSeries(dt_root_path='C:/Users/tizita/Documents/LIDC/LIDC-IDRI', patient_no=72)#  68
    patient_series.populate_from_xmlparser(xml_dt)
    
    #print patient_series
    
    cv2.namedWindow("LIDC-IDRI") #window to display dicom image on
    #cv2.startWindowThread() #important
    
    for ct in patient_series.annotated_cts:
        rad_indx = range(len(xml_dt.rad_annotations)) # is from 0 to 3
        
        cv_mat = ct.draw(rad_indx_lst=rad_indx, #draws annotation on to the ct img using 
                         draw_nodules=True, draw_small =True, draw_non=True) #the available annotation info
        #print range(len(xml_dt.rad_annotations))
        cv2.imshow('LIDC-IDRI', cv_mat)
        ky = cv2.waitKey(0)
        if ky == 27:    # Esc key to stop(close) the window
            cv2.waitKey(1) # in milli sec
            cv2.destroyAllWindows()
            #cv2.waitKey(1)
            break

        #cv2.imshow('image', ct.draw(rad_indx=0))
        #cv2.waitKey(0)
#        raw_input('press key to continue')
    return
    
if __name__ == '__main__':
    main()