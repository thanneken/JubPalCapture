#!/usr/bin/env python
import yaml
import sys
import os
from skimage import io, img_as_uint, img_as_float32
import numpy as np

"""
measurenoise.py takes as an argument one or more snr.yaml files
Each snr.yaml file must be a dictionary with relative path as the top key
If the same relativepath is repeated only the last one will be kept, so be sure to add files to the beginning, not the end.
Each path contains a dictionary of areas with labels such as "Full", "CenterThird", and "Spectralon"
The areas "Full" and "CenterThird" are calculated automatically. Custom areas can be measured by providing a Label and x,y,w,h to be measured
measurenoise.py will overwrite the snr.yaml file and comments will be lost
"""

verbose = 8

def snrfromimg(img,x,y,w,h):
	noise = np.std(img[y:y+h,x:x+w])
	linearsnr = np.mean(img[y:y+h,x:x+w]) / noise
	dbsnr = 10 * np.log10(linearsnr)
	linearsnr = float(linearsnr)
	dbsnr = float(dbsnr)
	noise = float(noise)
	return {"x":x,"y":y,"w":w,"h":h,"LinearSNR":linearsnr,"Db":dbsnr,"Noise":noise}

def snrfrompath(path,label,**kwargs):
	if not os.path.isfile(path):
		path = os.path.join(os.path.split(arg)[0],path)
		if not os.path.isfile(path):
			print(f"{path} does not exist, exiting")
			exit()
	img = io.imread(path)
	x,y = 0,0
	w,h = img.shape
	if label == 'CenterThird':
		x = int(w/6)
		y = int(h/6)
		w = int(w/3)
		h = int(h/3)
	x = kwargs.get('x',x)
	y = kwargs.get('y',y)
	w = kwargs.get('w',w)
	h = kwargs.get('h',h)
	return snrfromimg(img,x,y,w,h)

if __name__ == "__main__":
	if len(sys.argv) < 2:
		print("This command takes as an argument one or more snr.yaml files")
		exit()
	for arg in sys.argv[1:]:
		if not arg.endswith('snr.yaml'):
			print(f"{arv} does not end with snr.yaml")
			continue
		if not os.path.isfile(arg):
			print(f"{arg} is not a file")
			continue
		with open(arg,'r') as unparsedyaml:
			snrdict = yaml.load(unparsedyaml,Loader=yaml.SafeLoader)
		print("Initial parsed yaml is:\n"+yaml.dump(snrdict,sort_keys=False)) if verbose > 3 else None
		for imgpath in snrdict:
			if snrdict[imgpath] == None:
				snrdict[imgpath] = {'Full' : snrfrompath(imgpath,'Full') }
			if not 'Full' in snrdict[imgpath]:
				snrdict[imgpath]['Full'] = snrfrompath(imgpath,'Full')
			if not 'CenterThird' in snrdict[imgpath]:
				snrdict[imgpath]['CenterThird'] = snrfrompath(imgpath,'CenterThird')
			for area in snrdict[imgpath].keys():
				if 'x' in snrdict[imgpath][area] and not 'LinearSNR' in snrdict[imgpath][area]:
					snrdict[imgpath][area] = snrfrompath(imgpath,area,x=snrdict[imgpath][area]['x'],y=snrdict[imgpath][area]['y'],w=snrdict[imgpath][area]['w'],h=snrdict[imgpath][area]['h'])
		with open(arg,'w') as file:
			yaml.dump(snrdict,file,sort_keys=False) 
		print("Final yaml is:\n"+ yaml.dump(snrdict,sort_keys=False)) if verbose > 3 else None
