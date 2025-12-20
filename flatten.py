#!/usr/bin/env python
import sys
import os
from skimage import io, img_as_uint, img_as_float32
import numpy as np

verbose = 4
convention = {'source':'DarkSubtracted','flatid':'midfilename'}
convention = {'source':'Raw','flatid':'indexnumber'}

def flattenimg(unflatimg,flatimg):
	if verbose > 4:
		print(f"Unflattened image has range {np.min(unflatimg)} - {np.max(unflatimg)}")
		print(f"Flat image has range {np.min(flatimg)} - {np.max(flatimg)}")
	unflatimg = img_as_float32(unflatimg)
	flatimg = img_as_float32(flatimg)
	flattenedimg =	np.divide(unflatimg*np.average(flatimg),flatimg,out=np.zeros_like(unflatimg*np.average(flatimg)),where=flatimg!=0)
	if verbose > 4:
		print(f"Flattened image has range {np.min(flattenedimg)} - {np.max(flattenedimg)}")
		print(f"Flattened 99.999th percentile is {np.percentile(flattenedimg,99.999)}")
	if np.max(flattenedimg) > 1:
		if verbose > 0:
			counttoohigh = np.count_nonzero(flattenedimg > 1)
			nonextreme = np.percentile(flattenedimg,99.9)
			print(f"Flattened image has range {np.min(flattenedimg)} - {np.max(flattenedimg)} with {counttoohigh} pixels greater than 1")
			print(f"Clipping to 99.9%, which is {nonextreme}")
		flattenedimg = np.clip(flattenedimg,0,nonextreme)
		if np.max(flattenedimg) > 1:
			if verbose > 0:
				counttoohigh = np.count_nonzero(flattenedimg > 1)
				print(f"Flattened image has range {np.min(flattenedimg)} - {np.max(flattenedimg)} with {counttoohigh} pixels greater than 1")
				print(f"Dividing by max to keep flattened image in range")
			flattenedimg = flattenedimg / np.max(flattenedimg)
	flattenedimg = img_as_uint(flattenedimg)
	if verbose > 4:
		print(f"Flatened image has range {np.min(flattenedimg)} - {np.max(flattenedimg)}")
	return flattenedimg

def flattenfile(unflatpath,flatpath,flattenedpath):
	if verbose > 4:
		print(f"+ {unflatpath}")
		print(f"- {flatpath}")
	unflatimg = io.imread(unflatpath)
	flatimg = io.imread(flatpath)
	flattenedimg = flattenimg(unflatimg,flatimg)
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
		print(f"This command takes one argument, a path to a text file that lists relative paths to flats to be used to flatten the files in {convention['source']}/")
		exit()
	flatlistpath = sys.argv[1]
	if not os.path.isfile(flatlistpath):
		print("The specified flats list file does not exist")
		exit()
	targetdir = os.path.dirname(flatlistpath)
	unflatdir = os.path.join(targetdir,convention['source'])
	if not os.path.isdir(unflatdir):
		print(f"The specified flats list file does not share a directory with a directory named {convention['source']}/. Perhaps it is time to run darksubtract.py.")
		exit()
	with open(flatlistpath,'r') as flatslisthandle:
		flatlist = flatslisthandle.readlines()
		flatlist = [line.rstrip() for line in flatlist]
	unflatfilelist = os.listdir(unflatdir)
	for unflatfile in unflatfilelist:
		if convention['flatid'] == 'midfilename':
			essential = unflatfile[unflatfile.index('-'):unflatfile.rindex('-')+1]
		elif convention['flatid'] == 'indexnumber':
			essential = unflatfile[unflatfile.rindex('_'):]
		for flatpath in flatlist:
			if essential in flatpath:
				unflatpath = os.path.join(targetdir,convention['source'],unflatfile)
				flatpath = os.path.join(targetdir,flatpath)
				flattenedpath = unflatpath.replace(convention['source'],'Flattened')
				if not os.path.isfile(unflatpath):
					print(f"Error finding {unflatpath=}")
					continue
				if not os.path.isfile(flatpath):
					print(f"Error finding {flatpath=}")
					continue
				if os.path.isfile(flattenedpath):
					print(f"Flattened file already exists: {flattenedpath}")
					continue
				flattenfile(unflatpath,flatpath,flattenedpath)

