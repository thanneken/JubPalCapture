#!/usr/bin/env python
import sys
import os
from skimage import io, img_as_uint, img_as_float32
import numpy as np

verbose = 4

def flattenimg(unflatimg,flatimg):
    if verbose > 3:
        print(f"Unflattened image has range {np.min(unflatimg)} - {np.max(unflatimg)}")
        print(f"Flat image has range {np.min(flatimg)} - {np.max(flatimg)}")
    unflatimg = img_as_float32(unflatimg)
    flatimg = img_as_float32(flatimg)
    flattenedimg =  np.divide(unflatimg*np.average(flatimg),flatimg,out=np.zeros_like(unflatimg*np.average(flatimg)),where=flatimg!=0)
    if np.max(flattenedimg) > 1:
        if verbose > 0:
            print(f"Flatened image by max to fix range {np.min(flattenedimg)} - {np.max(flattenedimg)}")
            print(f"Dividing by max to keep flattened image in range")
        flattenedimg = flattenedimg / np.max(flattenedimg)
    flattenedimg = img_as_uint(flattenedimg)
    if verbose > 2:
        print(f"Flatened image has range {np.min(flattenedimg)} - {np.max(flattenedimg)}")
    return flattenedimg

def flattenfile(unflatpath,flatpath):
    if verbose > 3:
        print(f"+ {unflatpath}")
        print(f"- {flatpath}")
    unflatimg = io.imread(unflatpath)
    flatimg = io.imread(flatpath)
    flattenedimg = flattenimg(unflatimg,flatimg)
    flattenedpath = unflatpath.replace('DarkSubtracted','Flattened')
    flatteneddir = os.path.split(flattenedpath)[0]
    if not os.path.isdir(flatteneddir):
        if verbose > 3: 
            print(f"Creating directory {flatteneddir}")
        os.mkdir(flatteneddir)
    if verbose > 0:
        print(f"Saving flattened image as {flattenedpath}")
    io.imsave(flattenedpath,flattenedimg,check_contrast=False)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("This command takes one argument, a path to a directory which contains a file named flats.txt and a directory named DarkSubtracted/")
        exit()
    targetdir = sys.argv[1]
    if not os.path.isdir(targetdir):
        print("The specifified path is not a directory")
        exit()
    flatslistfile = os.path.join(targetdir,'flats.txt')
    if not os.path.isfile(flatslistfile):
        print("The specified directory does not contain a file called flats.txt")
        exit()
    unflatdir = os.path.join(targetdir,'DarkSubtracted')
    if not os.path.isdir(unflatdir):
        print("The specified directory does not contain a directory named DarkSubtracted/")
        exit()
    with open(flatslistfile,'r') as flatslisthandle:
        flatlist = flatslisthandle.readlines()
        flatlist = [line.rstrip() for line in flatlist]
    unflatfilelist = os.listdir(unflatdir)
    for unflatfile in unflatfilelist:
        essential = unflatfile[unflatfile.index('-'):unflatfile.rindex('-')+1]
        for flatpath in flatlist:
            if essential in flatpath:
                unflatpath = os.path.join(targetdir,'DarkSubtracted',unflatfile)
                flatpath = os.path.join(targetdir,flatpath)
                if not os.path.isfile(unflatpath):
                    print(f"Error finding {unflatpath}")
                if not os.path.isfile(flatpath):
                    print(f"Error finding {flatpath}")
                flattenfile(unflatpath,flatpath)

