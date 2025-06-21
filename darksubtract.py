#!/usr/bin/env python
import sys
import os
import glob
from datetime import datetime
from skimage import io, img_as_uint, img_as_ubyte, img_as_float32
import numpy as np

verbose = 4

def createmediandarkfile(basepath,darkmedianfile):
    if verbose > 2:
        print("Using all available dark files to create median dark file LensCap/Median/%s"%(darkmedianfile))
    fields = darkmedianfile.split('-')
    target = fields[0]
    camera = fields[1]
    gain = fields[4]
    passfilter = fields[6]
    if not 'Bayer' in passfilter:
      passfilter = 'NoFilter'
    exposure = fields[7]
    filemask = os.path.join(basepath,'LensCap','Raw','LensCap-'+camera+'-*-F*-'+gain+'-*-'+passfilter+'-'+exposure+'-*.tif')
    darklist = glob.glob(filemask)
    if len(darklist) == 0:
        if verbose > 0:
            print("No suitable dark files found. Take ten shots of LensCap-%s-NoLens-FNone-%s-NoLight-%s-%s-<timestamp>.tif"%(camera,gain,passfilter,exposure))
        return
    cube = []
    for darkfile in darklist:
        if verbose > 2:
            print("Reading %s"%(darkfile))
        img = io.imread(darkfile)
        if img.dtype == np.uint16:
            bpp = 16
        elif img.dtype == np.uint8:
            bpp = 8
        img = img_as_float32(img)
        cube.append(img)
    cube = np.array(cube) 
    if verbose > 3:
        print("Calculating median")
    median = np.median(cube,axis=0)
    if bpp == 16:
        median = img_as_uint(median)
    elif bpp == 8:
        median = img_as_byte(media)
    if not os.path.exists(os.path.join(basepath,'LensCap','Median')):
        if verbose > 2:
            print("Creating directory %s"%(os.path.join(basepath,'LensCap','Median')))
        os.mkdir(os.path.join(basepath,'LensCap','Median'))
    io.imsave(os.path.join(basepath,'LensCap','Median',darkmedianfile),median,check_contrast=False)

def createdarksubtractedfile(basepath,targetfile):
    if verbose > 2:
        print("Subtracting median dark noise from Raw/%s for directory DarkSubtracted/"%(targetfile))
    fields = targetfile.split('-')
    target = fields[0]
    camera = fields[1]
    gain = fields[4]
    passfilter = fields[6]
    if not 'Bayer' in passfilter:
      passfilter = 'NoFilter'
    exposure = fields[7]
    filemask = os.path.join(basepath,'LensCap','Median','LensCap-'+camera+'-*-F*-'+gain+'-NoLight-'+passfilter+'-'+exposure+'-*.tif')
    medianlist = glob.glob(filemask)
    if len(medianlist) == 0:
        if verbose > 2:
            print("No suitable median dark file found, will try to create")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        darkmedianfile = 'LensCap-'+camera+'-NoLens-FNone-'+gain+'-NoLight-'+passfilter+'-'+exposure+'-'+timestamp+'.tif'
        createmediandarkfile(basepath,darkmedianfile)
        if not os.path.exists(os.path.join(basepath,'LensCap','Median',darkmedianfile)):
            return
        createdarksubtractedfile(basepath,targetfile)
        return
    elif len(medianlist) > 1:
        if verbose > 0:
            print("More than one suitable median dark file found. Think about what to do in this situation and edit the code.")
        return
    targetimage = io.imread(os.path.join(basepath,target,'Raw',targetfile))
    darkmedianimage = io.imread(os.path.join(basepath,'LensCap','Median',medianlist[0]))
    if verbose > 3:
        print("Target image range is %s - %s"%(np.min(targetimage),np.max(targetimage)))
        print("Median image range is %s - %s"%(np.min(darkmedianimage),np.max(darkmedianimage)))
    if targetimage.dtype == np.uint8:
        bpp = 8
    else:
        bpp = 16
    targetimage = img_as_float32(targetimage)
    darkmedianimage = img_as_float32(darkmedianimage)
    darksubtractedimage = targetimage - darkmedianimage
    formermin = np.min(darksubtractedimage)
    formermax = np.max(darksubtractedimage)
    if verbose > 0:
        print("Dark subtracted image range is %s - %s"%(formermin*2**bpp-1,formermax*2**bpp-1))
    if np.min(darksubtractedimage) <= 0:
        darksubtractedimage = darksubtractedimage - formermin + (1/2**bpp) 
    if np.max(darksubtractedimage) > 1:
        darksubtractedimage = np.clip(darksubtractedimage,a_min=None,a_max=1) 
    if bpp == 8:
        darksubtractedimage = img_as_byte(darksubtractedimage)
    else:
        darksubtractedimage = img_as_uint(darksubtractedimage)
    if verbose > 0:
        print("Corrected range is %s - %s"%(np.min(darksubtractedimage),np.max(darksubtractedimage)))
    io.imsave(os.path.join(basepath,target,'DarkSubtracted',targetfile),darksubtractedimage,check_contrast=False)

if __name__ == "__main__":
    """
    Go through arguments sent from commandline and skip anything likely to create problems later
    """
    if verbose > 3:
        print("Taking list of files to be dark subtracted from the command line")
    if len(sys.argv) == 1:
        print("This command takes a filename or glob of filenames as a command line argument")
        exit()
    for argument in sys.argv[1:]:
        if os.path.isdir(argument) and verbose > 0:
            print("%s is a directory. For now we're expecting image files. Adding /*.tif might do the trick."%(argument))
        elif not "Raw" in argument and verbose > 0:
            print("We're expecting files to be dark subtracted to be in a directory called Raw. Excluding %s"%(argument))
        elif not argument.lower().endswith('.tif'):
            print("We're expecting files that end with '.tif'. Excluding %s"%(argument))
        elif not os.path.isfile(argument): 
            print(f"Not a path to a real tiff file: {argument}")
        else:
            rawpath, targetfile = os.path.split(argument)
            targetpath = os.path.dirname(rawpath)
            basepath = os.path.dirname(targetpath)
            darksubtracteddir = os.path.join(targetpath,'DarkSubtracted')
            if not os.path.exists(darksubtracteddir):
                if verbose > 2:
                    print("Creating directory %s"%(darksubtracteddir))
                os.mkdir(darksubtracteddir)
            if os.path.exists(os.path.join(darksubtracteddir,targetfile)):
                if verbose > 2:
                    print("Dark subtracted file already exists for %s"%(targetfile))
            else:
                createdarksubtractedfile(basepath,targetfile)

