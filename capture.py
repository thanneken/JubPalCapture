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
		import libqhy 
		camera = libqhy.Qhyccd()
		camera.session(config,args.target)
	elif config['sensor'].lower().startswith('q15'):
		import libqhy 
		camera = libqhy.Qhyccd()
		camera.session(config,args.target)
	elif config['sensor'].lower().startswith('canon'):
		from libcanon import Canon 
		camera = Canon(config,args.target)
	elif config['sensor'].lower().startswith('flir'):
		from libflir import Flir
		camera = Flir()
		camera.session(config,args.target)
	elif config['sensor'].lower().startswith('kolarielph'):
		from libchdk import Chdk
		camera = Chdk()
		camera.session(config,args.target)
	elif config['sensor'].lower().startswith('pixelink'):
		from libpixelink import Pixelink
		camera = Pixelink()
		camera.session(config,args.target)
	elif config['sensor'].lower().startswith('spencer'):
		from libcanon import Canon 
		camera = Canon(config,args.target)
		print("Giving Canon 1 seconds to initialize")
		time.sleep(1)
	else:
		print("Not sure which camera to initialize")
		exit()
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
		lightArray = lights.Misha()
		print("Giving the Misha lights another 2 seconds to open")
		time.sleep(2)
	elif config['lights'].lower().startswith('nolight'):
		lightArray = lights.Overhead()
	print("Starting shot list")
	for shot in shotlist:
		if shot.strip() == "" or shot.strip().startswith('log:') or shot.strip().startswith('#'):
			continue
		light,wheel,exposure = shot.strip().split(sep='-')
		exposure = int(exposure.strip('ms'))
		print("\aShooting Light = %s | Wheel = %s | Exposure = %s"%(light,wheel,exposure))
		camera.setWheel(wheel)
		if False:
			lightProcess = Process(target=lightArray.manualon,args=(light)) #lightProcess = Process(target=lightArray.on,args=(light,exposure)) 
			lightProcess.start()
		if True:
			lightArray.manualon(light)
		time.sleep(0.5) # Give the lights a head start
		camera.shoot(light,wheel,exposure)
		if False:
			lightProcess.join()
			lightProcess = Process(target=lightArray.off) 
			lightProcess.start()
			lightProcess.join()
		if True:
			lightArray.off()
	lightArray.close()
	camera.close()

