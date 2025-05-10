#!/usr/bin/env python
import argparse
from multiprocessing import Process
import yaml
import lights
# from datetime import datetime
# import numpy as np
# from os import makedirs, path
# from skimage import io
import time

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
		with open(args.configuration,'r') as unparsedyaml:
			config = yaml.load(unparsedyaml,Loader=yaml.SafeLoader)
	else:
		print("It is necessary to specify a configuration file")
		exit()
	if args.shotlist and args.shotlist.lower().endswith('.yaml'): # makes sense to use yaml for config and txt for shotlist
		with open (args.shotlist,'r') as unparsedyaml:
			shotlist = yaml.load(unparsedyaml,Loader=yaml.SafeLoader)
	elif args.shotlist and args.shotlist.lower().endswith('txt'):
		with open (args.shotlist,'r') as unparsedtxt:
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
	print("Initializing light array")
	if config['lights'].lower() == 'octopusbluetooth':
	 	lightArray = lights.OctopusBluetooth()
	elif config['lights'].lower().startswith('octopus'):
		lightArray = lights.Octopus()
		print("Giving the Octopus another 2 seconds to open")
		time.sleep(2)
	elif config['lights'].lower().startswith('overhead'):
		lightArray = lights.Overhead()
	elif config['lights'].lower().startswith('misha'):
		lightArray = lights.Misha
	print("Starting shot list")
	for shot in shotlist:
		if shot.strip() == "":
			continue
		light,wheel,exposure = shot.strip().split(sep='-')
		print("Light = %s | Wheel = %s | Exposure = %s"%(light,wheel,exposure))
		exposure = exposure.strip('ms')
		camera.setWheel(wheel)
		lightProcess = Process(target=lightArray.on,args=(light,exposure)) 
		lightProcess.start()
		time.sleep(0.5) # Give the lights a head start
		print("Shooting!\a")
		camera.shoot(light,wheel,exposure)
		lightProcess.join()
	lightArray.close()
	camera.close()

