"""
Created on Wed Jun 13 11:52:12 2015

@author: tizita nesibu

"""

import xml.etree.ElementTree as ET
import os, sys
from os import listdir
from os.path import isfile, join

import Tkinter

import dicom
import dicom.contrib.pydicom_Tkinter as pydicom_Tkinter

import cv2
import numpy as np

from annotstructs import NoduleRoi, NormalNodule, SmallNodule, NonNodule, RadAnnotation, NoduleAnnotationCluster
from ..parser.lidcxmlparser import LIDCXmlParser, LIDCXmlHeader

from matplotlib import pyplot as plt

class ColorMap:
    
    def __init__(self):
        self.color_map = [(255,255,0),(255,0,255),(0,255,255),(255,0,0), \
                          (0,255,0),(0,0,255),(0,50,255),(17,255,238), \
                          (255,183,0),(128,0,0),(61,255,194),(0,139,255), \
                          (238,255,17),(255,94,0),(0,0,128),(105,255,150)]
        
        self.length = len(self.color_map) #16

    def get_color(self, indx):
        abs_indx = indx%self.length
        return self.color_map[abs_indx]                  
             

class DicomImgData:
    
    def __init__(self, dicom_data):
        self.components = [] 
        
        if ('RescaleIntercept' in dicom_data):
            self.RescaleIntercept = dicom_data.RescaleIntercept
            self.components.extend(['RescaleIntercept']) #.extend is to add another list e.g.['RescaleIntercept'] 
                                                            #onto components list
        
        if ('RescaleSlope' in dicom_data):
            self.RescaleSlope = dicom_data.RescaleSlope
            self.components.extend(['RescaleSlope'])
        
        if ('WindowCenter' in dicom_data):
            self.WindowCenter = dicom_data.WindowCenter
            self.components.extend(['WindowCenter'])
        
        if ('WindowWidth' in dicom_data):
            self.WindowWidth = dicom_data.WindowWidth
            self.components.extend(['WindowWidth'])
     
        self.pixel_array = np.copy(dicom_data.pixel_array) #dicom_data.pixel_array -> to extract only the img info from 
                                                           #dicom data(image) (ignores the header info)
        return

    def __contains__(self, key):
        return key in self.components

class AnnotatedCT:
    
    def __init__(self):
        self.abs_filename = []
        
        #unique identifier
        self.sop_uid = []
        self.z_pos = []
        self.alias = []
        
        self.rad_annots = []
        self.dicom = []
        self.image = []
        return
    
    #__normalize_dicom_array__() is pydicom's function
    def __normalize_dicom_array__(self, arr, window_center, window_width, lut_min=0, lut_max=255):
         #to change the img data b/n 0 and 255
        """
        This function is adopted from
        -> def get_PGM_from_numpy_arr(....)
    
        real-valued numpy input  ->  PGM-image formatted byte string
        
        arr: real-valued numpy array to display as grayscale image
        window_center, window_width: to define max/min values to be mapped to the
                                     lookup-table range. WC/WW scaling is done
                                 according to DICOM-3 specifications.
                                 lut_min, lut_max: min/max values of (PGM-) grayscale table: do not change
        """

        if np.isreal(arr).sum() != arr.size:
            raise ValueError

        # currently only support 8-bit colors
        if lut_max != 255:
            raise ValueError

        if arr.dtype != np.float64:
            arr = arr.astype(np.float64)

        # LUT-specific array scaling
        # width >= 1 (DICOM standard)
        window_width = max(1, window_width)
        
        wc, ww = np.float64(window_center), np.float64(window_width)
        lut_range = np.float64(lut_max) - lut_min
        
        minval = wc - 0.5 - (ww - 1.0) / 2.0
        maxval = wc - 0.5 + (ww - 1.0) / 2.0
        
        min_mask = (minval >= arr)
        to_scale = (arr > minval) & (arr < maxval)
        max_mask = (arr >= maxval)
        
        if min_mask.any():
            arr[min_mask] = lut_min
        if to_scale.any():
            arr[to_scale] = ((arr[to_scale] - (wc - 0.5)) /
                            (ww - 1.0) + 0.5) * lut_range + lut_min
        if max_mask.any():
            arr[max_mask] = lut_max

        # round to next integer values and convert to unsigned int
        return np.rint(arr).astype(np.uint8)
    
    def __get_mat__(self, data):  #change img to openCV image format 
                                    #it is pydicom's function
        '''
        This funciton is taken adopted from
        -> def get_tkinter_photoimage_from_pydicom_image(data):
            Wrap data.pixel_array in a Tkinter PhotoImage instance,
            after conversion into a PGM grayscale image.
            
            This will fail if the "numpy" module is not installed in the attempt of
        creating the data.pixel_array.
        
        data:  object returned from pydicom.read_file()
        side effect: may leave a temporary .pgm file on disk
        '''

        # get numpy array as representation of image data
        arr = data.pixel_array.astype(np.float64)   #change to float
        
        # pixel_array seems to be the original, non-rescaled array.
        # If present, window center and width refer to rescaled array
        # -> do rescaling if possible.
        if ('RescaleIntercept' in data) and ('RescaleSlope' in data):
            intercept = data.RescaleIntercept  # single value
            slope = data.RescaleSlope
            arr = slope * arr + intercept  #to normalize the img data b/n 0 and 1(float)

        # get default window_center and window_width values
        wc = (arr.max() + arr.min()) / 2.0
        ww = arr.max() - arr.min() + 1.0

        # overwrite with specific values from data, if available
        if ('WindowCenter' in data) and ('WindowWidth' in data):
            wc = data.WindowCenter
            ww = data.WindowWidth
            try:
                wc = wc[0]            # can be multiple values
            except:
                pass
            try:
                ww = ww[0]
            except:
                pass
        return self.__normalize_dicom_array__(arr, wc, ww)  #to change the img data b/n 0 and 255
    
    
    def dicom_to_mat(self, dicom_f):
        
        dicom_img_data = DicomImgData(dicom_f) 
        cv_mat = self.__get_mat__(dicom_img_data) #the underscore in __get_mat__ and __draw__ is to mimic privet fun to
        return cv_mat                            #this class (it is possible but not adviseble to access it outside 
                                                 #of this class)
     
     ## to drow one radiologist annotation in one slice(will be called only inside this class by draw fun)
    def __draw__(self, cv_mat, rad_indx, d_nodules=True, d_small =False, d_non=False, bbox=True):
        
        annotations = self.rad_annots[rad_indx]

        c_map = ColorMap().get_color(rad_indx)
        
        if (d_nodules):
            for nodules in annotations.nodules:
                for roi in nodules.rois:
                    
                    roi_array = [[x,y] for x,y in roi.roi_xy]
                    roi_array = np.array(roi_array)
                    cv2.drawContours(cv_mat,[roi_array],-1,c_map,1)
                    
                    #for x,y in roi.roi_xy:
                        #cv2.circle(cv_mat, (x,y), 1, c_map, -1)
                    if bbox:
                        cv2.rectangle(cv_mat, (roi.roi_rect[0],roi.roi_rect[1]), (roi.roi_rect[2],roi.roi_rect[3]), c_map, 1)
        
        if(d_small):
            for nodules in annotations.small_nodules:
                for roi in nodules.rois:
                    for x,y in roi.roi_xy: #for small and non nodules radiologist annotations is given by a dot
                        cv2.circle(cv_mat, (x,y), 3, c_map, 1)
                        
        if(d_non):
            for nodules in annotations.non_nodules:
                for roi in nodules.rois:
                    for x,y in roi.roi_xy:
                        cv2.circle(cv_mat, (x,y), 3, c_map, 1)
                        cv2.rectangle(cv_mat, (x-2,y-2), (x+2,y+2), c_map, 1)

        return cv_mat               
        
    #rad_indx = -1 to draw all
        
        # to drow one or more radiologistes annotation in one slice
    def draw(self, rad_indx_lst=[], draw_nodules=True, draw_small=False, draw_non=False):
        #dicom_photo_ref = pydicom_Tkinter.get_tkinter_photoimage_from_pydicom_image(dicom_img_data)
        
        cv_mat = cv2.cvtColor(self.image,cv2.COLOR_GRAY2RGB)
        
        n_rads = len(self.rad_annots)
        for rad_indx in rad_indx_lst:
            if (rad_indx < n_rads):
                cv_mat = self.__draw__(cv_mat, rad_indx, d_nodules=draw_nodules, d_small=draw_small, d_non=draw_non)
            else:
                print "ERROR: indx (%d) exceeds total no of radiologists, i.e., [%d]!"%(rad_indx, n_rads)
                return None        
        return cv_mat

    
    def no_consensus_annots(self): # counter returns 4 if all radiologist annotates the nodule(i.e. normalNodule)
        counter = 0
        for annots in self.rad_annots:
            if (len(annots.nodules) > 0):
                counter+=1
        return counter

#???????????????????????????????????????????????????????????????????????????? 
    def __nodule_in_cluster(self,clusters, nodule, thresh=20): # not for now

        ref_centroid = nodule.rois[0].roi_centroid #needs to at least have one roi
        for indx,cluster in enumerate(clusters):
            #Computer approximate cluster centroids
            xc, yc = 0.,0.
            for nod in cluster.nodules_data:
                #assume each node in the cluster at least has one roi
                xc += nod.rois[0].roi_centroid[0]
                yc += nod.rois[0].roi_centroid[1]
            xc /= float(len(cluster.nodules_data))
            yc /= float(len(cluster.nodules_data))
            #compute equilidian distance on image plane
            dx,dy = ref_centroid[0] - xc,ref_centroid[1] - yc
            dist = (dx*dx + dy*dy)**0.5 #compute square root
            
            if (dist < thresh):
                return indx
        return -1

    def save_nearest_cluster(self, selected_centroid, indx, root_path): # not for now
        #create directories if they don't exist
        mat_dir = "%s/mat/"%root_path
        dicom_dir = "%s/dicom/"%root_path
        rad_dir = "%s/rad/"%root_path
        rect_dir = "%s/rect/"%root_path
        
        if not os.path.exists(mat_dir):
                os.makedirs(mat_dir)
        if not os.path.exists(dicom_dir):
                os.makedirs(dicom_dir)
        if not os.path.exists(rad_dir):
                os.makedirs(rad_dir)
        if not os.path.exists(rect_dir):
                os.makedirs(rect_dir)
        clusters = self.get_nodule_clusters()
        
        for c_indx,(xs, ys) in enumerate(selected_centroid):
            for cluster in clusters:
                (xc,yc) = cluster.centroid
                dx = xc - xs
                dy = yc - ys
                dist = (dx*dx + dy*dy)**0.5  #sqrt(dx^2 + dy^2)
            
                if (dist < 15): #less than 15 pixels
                    cvx_hull = cluster.convex_hull_with_margin
                    (x_min, y_min) = cvx_hull[0]
                    (x_max, y_max) = cvx_hull[3]
                    roi = self.image[y_min:y_max+1, x_min:x_max+1]
                    
                    dicom_roi = self.dicom.pixel_array[y_min:y_max+1, x_min:x_max+1]
                    
                
                    if (roi.shape[0] > 5 or roi.shape[1] > 5): #???????????????/
                        fname = "%s/mat/nodcluster_%04d_%02d.png"%(root_path,indx, c_indx)
                        cv2.imwrite(fname,roi)   
                        fname = "%s/dicom/nodcluster_%04d_%02d.txt"%(root_path,indx, c_indx)
                        np.savetxt(fname,dicom_roi)
                        fname = "%s/rect/nodcluster_%04d_%02d.txt"%(root_path,indx, c_indx)
                        fo = open(fname,"w")
                        fo.write("%d:%d,%d,%d,%d\n"%(c_indx,x_min,y_min,x_max,y_max))
                        fo.close()
                        #draw radiologist data
                        for rad_indx in range(len(self.rad_annots)):
                            cv_mat = cv2.cvtColor(self.image,cv2.COLOR_GRAY2RGB)
                            cv_mat = self.__draw__(cv_mat, rad_indx, d_nodules=True,bbox=False)
                            roi = cv_mat[y_min:y_max+1, x_min:x_max+1,:]# : ??????????
                            fname = "%s/rad/radannot_%04d_%02d_%02d.png"%(root_path,indx, rad_indx, c_indx)
                            cv2.imwrite(fname,roi)
      
        pass
    
    def get_nodule_clusters(self):  # not for now
        if (self.no_consensus_annots() < 1):
            return []

        nodule_clusters = []
        #loop through the nodules 
        for annots in self.rad_annots:
            if (len(annots.nodules) > 0):
                for nod in annots.nodules:
                    indx = self.__nodule_in_cluster(nodule_clusters, nod)
                    if (indx == -1):
                        #add as new
                        cluster = NoduleAnnotationCluster()
                        cluster.id = nod.id
                        cluster.z_pos = self.z_pos    #can be used to identify the ct
                        cluster.nodules_data.append(nod)
                        cluster.no_annots += 1
                        nodule_clusters.append(cluster)
                    else:
                        #add to exisiting
                        nodule_clusters[indx].nodules_data.append(nod)  #??????????????
                        nodule_clusters[indx].no_annots += 1
        for cluster in nodule_clusters:
            cluster.compute_centroid() 
        return nodule_clusters
    
    def __lt__(self, other):  #sort utility function whch can be set to tell the sort fun how to sort the data
         return self.z_pos < other.z_pos
         
    def __str__(self):
        strng = "Alias [%s] Z-POS [%.2f] UID [%s] \n"%(self.alias, self.z_pos, self.sop_uid)
        
        strng += "# of rad annots [%d] \n"%len(self.rad_annots)
        
        for an in self.rad_annots:
            strng += str(an)
        
        return strng



class PatientCTSeries:
    
    def __init__(self, dt_root_path = "/opt/DataSet/lung-ct/", patient_no=1):
        #self.tk_instance = Tkinter.Tk()
        self.dataset_root_path = dt_root_path
        
        self.dicom_path = []
        self.xml_path = []
        self.patient_id = ("LIDC-IDRI-%04d")%patient_no #e.g. LIDC-IDRI-0068
        self.annotated_cts = []
        
        self.indx_lookup_z = {}  #is dictionary
        self.indx_lookup_uid = {}
        self.indx_lookup_alias = {}
        return
        
    def populate_from_xmlparser(self, lidc_xml_parser): #lidc_xml_parser is object of LIDCXmlParser class
        self.dicom_path =   self.dataset_root_path + "/" + self.patient_id + "/" + \
                            lidc_xml_parser.xml_header.study_instance_uid + "/" + \
                            lidc_xml_parser.xml_header.series_instance_uid
                                                        
        #list files in this directory(i.e. Dicom files)
        print " Absolute dicom path: " + self.dicom_path
        
#??????????????????????????????if the if condition is true append f in to the list dicom_files????????????????????
        dicom_files = [ f for f in listdir(self.dicom_path) if isfile(join(self.dicom_path,f)) and f.endswith('.dcm')]
        dicom_files.sort()
        
        n_anotators = range(len(lidc_xml_parser.rad_annotations)) #from 0 to nbr of radiologist-1 (i.e. from 0 to 3)
        
        #extracting one dicom slice info
        for indx, fl in enumerate(dicom_files): #indx -> index & fl-> dicom file in dicom_files path
            ant_ct = AnnotatedCT()
            ant_ct.abs_filename = self.dicom_path + "/" + fl  #the path upto the specific dicom file
            ant_ct.alias = fl
            
            ant_ct.dicom = dicom.read_file(ant_ct.abs_filename) #dicom.read_file ->reads dicom file
            ant_ct.image = ant_ct.dicom_to_mat(ant_ct.dicom)  #by separating dicom image from its header it converts
                                                                 # dicom img to openCV image format
            
            ant_ct.sop_uid = ant_ct.dicom.SOPInstanceUID  #is like the slice id (found in dicom slice image header)
            ant_ct.z_pos = float(ant_ct.dicom.SliceLocation) #is like the z pos of the slice(found in dicom slice image header)
            
            #to prepare ant_ct.rad_annots list to hold the 4 dadiologists annotation which they give for one slice of nodule
            for r in n_anotators:
                ant_ct.rad_annots.append(RadAnnotation(False)) #is not initialized just for a place holder annotation data
                    #i.e. instantiating the RadAnnotation class by using ant_ct.rad_annots object
            
            self.annotated_cts.append(ant_ct)  #ant_ct has dicom img and a place holder for the annotation info(not filled yet)
        
        self.annotated_cts.sort()  #sort by z_pos (set by telling the sort utility function(__lt__(self, other)) how  
                                   #to sort the given data
        #sort annotated_cts first
        for indx, ant_ct in enumerate(self.annotated_cts):
            self.indx_lookup_uid[ant_ct.sop_uid] = indx  #creating lookup for identifying the order of the slice
            self.indx_lookup_z[ant_ct.z_pos] = indx
            self.indx_lookup_alias[ant_ct.alias] = indx
            
            
        
        #rad_updated = [False]*n_anotators;
        
        #to hold the annotation of the 4 radiologistes info in one slice ->for drawing
        for indx, rad in enumerate(lidc_xml_parser.rad_annotations): #has 4 radiologistes
                                    #rad holds one readingSession info(rad_annotation)
            for nod in rad.nodules: #nod is one NormalNodule
                for nod_roi in nod.rois:
                    v1 = self.indx_lookup_uid[nod_roi.sop_uid] #used for checking if the slice is the correct 
                    v2 = self.indx_lookup_z[nod_roi.z]        #one which is specified by the sop_uid and the z_pos
                      #v1 and v2 holds indx value which was placed in the two lookup dictionaries
                    
                    if (not (v1 == v2)):
                        print "ERROR: v1[%d] should be equal to v2[%d]...exiting \n"%(v1,v2)
                        return

                    dicom_ct = self.annotated_cts[v1] #one ct slice specified by its sop_uid
                    ant = dicom_ct.rad_annots[indx] #dicom_ct = ant_ct i.e. obj of AnnotatedCT class                  
                                                #rad_annots is a list in AnnotatedCT class which holds many  
                                                # instantiation of RadAnnotation class (just the place holder)
                            #ant will be the reference to obj of the specified(from the list by indx) RadAnnotation class
                    if (ant.is_init()== False):
                        ant.version = rad.version
                        ant.id = rad.id
                        ant.set_init(True)
                    
                    nd = NormalNodule()
                    nd.id = nod.id
                    nd.characterstics = nod.characterstics
                
                    nd.rois.append(nod_roi)
                    ant.nodules.append(nd)
            
            for sm_nod in rad.small_nodules:
                for nod_roi in sm_nod.rois:
                    v1 = self.indx_lookup_uid[nod_roi.sop_uid]
                    v2 = self.indx_lookup_z[nod_roi.z]
                    
                    if (not (v1 == v2)):
                        print "ERROR: v1[%d] should be equal to v2[%d]...exiting \n"%(v1,v2)
                        return
                        
                    dicom_ct = self.annotated_cts[v1]
                    ant = dicom_ct.rad_annots[indx]                     
                    
                    if (not ant.is_init()):
                        ant.version = rad.version
                        ant.id = rad.id
                        ant.set_init(True)
                    
                    nd = SmallNodule()
                    nd.id = sm_nod.id

                    nd.rois.append(nod_roi)   #for small nodules only one roi and one x,y position is available
                    ant.small_nodules.append(nd)  #which means they put only one dot in one slice
            
            for non_nod in rad.non_nodules:
                for nod_roi in non_nod.rois:
                    v1 = self.indx_lookup_uid[nod_roi.sop_uid]
                    v2 = self.indx_lookup_z[nod_roi.z]
                    
                    if (not (v1 == v2)):
                        print "ERROR: v1[%d] should be equal to v2[%d]...exiting \n"%(v1,v2)
                        return
                        
                    dicom_ct = self.annotated_cts[v1]
                    ant = dicom_ct.rad_annots[indx]                     
                    
                    if (not ant.is_init()):
                        ant.version = rad.version
                        ant.id = rad.id
                        ant.set_init(True)
                    
                    nd = NonNodule()
                    nd.id = non_nod.id

                    nd.rois.append(nod_roi)  #for non nodules only one roi and one x,y position is available
                    ant.non_nodules.append(nd)  #which means they put only one dot in one slice

        return

    
    def __str__(self):
        strng = "-"*79 + "\n"
        strng += "-"*79 + "\n"
        
        strng += "Patient ID [%s] \n"%self.patient_id
        strng += "Total no of CTs in Series [%d] \n" % len(self.annotated_cts)
        
        for indx, ct in enumerate(self.annotated_cts):
            strng += " CT-Image # [%d] \n"%indx
            strng += str(ct)
            strng += "-"*79 + "\n"
    
        #strng += "Lookup-Dictionary \n"
        #strng += str(self.indx_lookup_z)
        
        return strng            
        
        
