#!/usr/bin/env python
import argparse
from datetime import datetime
from multiprocessing import Process
import numpy as np
from os import makedirs, path
from skimage import io
import time
import yaml

def getArguments():
	parser = argparse.ArgumentParser()
	parser.add_argument('-c','--configuration')
	parser.add_argument('-s','--shotlist')
	parser.add_argument('-t','--target')
	parser.add_argument('-v','--verbose',action='store_true')
	return parser.parse_args()

if __name__ == "__main__":
	print("Gathering arguments from the command line")
	args = getArguments()
	if args.configuration and args.configuration.lower().endswith('.yaml'):
		with open('profiles'+args.configuration,'r') as unparsedyaml:
			config = yaml.load(unparsedyaml,Loader=yaml.SafeLoader)
	else:
		print("It is necessary to specify a configuration file")
		exit()
	if args.shotlist and args.shotlist.lower().endswith('.yaml'): # makes sense to use yaml for config and txt for shotlist
		with open ('shotlists'+args.shotlist,'r') as unparsedyaml:
			shotlist = yaml.load(unparsedyaml,Loader=yaml.SafeLoader)
	elif args.shotlist and args.shotlist.lower().endswith('txt'):
		with open ('shotlists'+args.shotlist,'r') as unparsedtxt:
			shotlist = unparsedtxt.readlines()
	else: 
		print("It is necessary to specify a shotlist file")
		exit()
	if not args.target:
		print("Let's just stop here because you're going to need to specify a target before we can save anything.")
		exit()
	print("Initializing camera")
	if config['sensor'].lower().startswith('qhy'):
		import qhyccd 
		camera = qhyccd.qhyccd()
		camera.session(config,args.target)
	elif config['sensor'].lower().startswith('canon'):
		from libcanon import Canon 
		camera = Canon(config,args.target)
	print("Camera initialized")
	if args.verbose:
		camera.showInfo()
	print("Initializing lights")
	if config['lights'].lower().startswith('octopus'):
		from lights import Octopus as lights
	elif config['lights'].lower().startswith('overhead'):
		from lights import Overhead as lights
	elif config['lights'].lower().startswith('misha'):
		from lights import Misha as lights
	print("Starting shot list")
	for shot in shotlist:
		if shot.strip() == "":
			continue
		light,wheel,exposure = shot.strip().split(sep='-')
		print("Light = %s | Wheel = %s | Exposure = %s"%(light,wheel,exposure))
		exposure = exposure.strip('ms')
		camera.setWheel(wheel)
		lightProcess = Process(target=lights.on,args=(lights,light,exposure)) 
		lightProcess.start()
		camera.shoot(light,wheel,exposure)
		lightProcess.join()
	print("It's been fun, thanks for all the tacos!")
	lights.close()
	camera.close()

