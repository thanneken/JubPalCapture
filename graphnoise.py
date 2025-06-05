#!/usr/bin/env python
import matplotlib.pyplot as plt
import numpy as np
import sys
import os
import yaml
from skimage import io

verbose = 3
area = 'Full'

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
		measurements = {}
		for imgpath in snrdict:
			imgpatharray = imgpath.split('-')
			base = '-'.join(imgpatharray[0:-2])
			exposuretime = imgpatharray[-2]
			exposuretime = exposuretime.strip('ms')
			print(f"{base} >> {exposuretime:>7}") if verbose > 3 else None
			if not base in measurements:
				measurements.update({base:{exposuretime:{'linear':snrdict[imgpath][area]['LinearSNR']}}})
			else:
				measurements[base][exposuretime] = {'linear':snrdict[imgpath][area]['LinearSNR']}
		print(measurements) if verbose > 5 else None
		plt.switch_backend('Qt5Agg')
		for measurement in measurements.keys():
			print(f"Adding {measurement}") if verbose > 4 else None
			x = sorted(measurements[measurement])
			y = [] 
			for exposuretime in x:
				y.append(measurements[measurement][exposuretime]['linear'])
			print(list(zip(x,y))) if verbose > 4 else None
			plt.plot(x,y)
		plt.show()

