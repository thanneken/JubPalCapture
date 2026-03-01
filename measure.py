#!/usr/bin/env python
import argparse
import glob
from skimage import io
import numpy as np

parser = argparse.ArgumentParser(argument_default='*')
parser.add_argument('-d','--directory')
parser.add_argument('-o','--object')
parser.add_argument('-s','--sensor')
parser.add_argument('-l','--lens')
parser.add_argument('-f','--filter')
parser.add_argument('-i','--illuminant')
parser.add_argument('-g','--gain')
parser.add_argument('-a','--aperture')
parser.add_argument('-t','--time')
parser.add_argument('-c','--clock')
parser.add_argument('-e','--ext')
args = parser.parse_args()
filemask = args.directory+'-'.join((args.object,args.sensor,args.lens,'F'+args.aperture,'gain'+args.gain,args.illuminant,args.filter,args.time,args.clock))+'.'+args.ext
print("Looking for files that match filemask %s"%(filemask))
filelist = glob.glob(filemask)
print("Found %s files matching parameters"%(len(filelist)))
cube = []
for filename in filelist: 
	print("Working on file %s"%(filename))
	img = io.imread(filename)
	print("Values range from %s to %s with a standard deviation of %s"%(np.min(img),np.max(img),round(np.std(img),2)))
	cube.append(img) 

cube = np.array(cube,dtype=np.float32)
print("Cube has shape",cube.shape)
median = np.median(cube,axis=0)
print("Median has shape",median.shape)
print("Values range from %s to %s with a standard deviation of %s"%(np.min(median),np.max(median),round(np.std(median),2)))

for filename in filelist: 
	print("Working on file %s"%(filename))
	img = io.imread(filename)
	img = img - median
	print("After subtracting cube median, values range from %s to %s with a standard deviation of %s"%(np.min(img),np.max(img),round(np.std(img),2)))

