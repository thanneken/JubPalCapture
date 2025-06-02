import edsdk
import time
import rawpy
import numpy as np
from datetime import datetime
from io import BytesIO
from os import makedirs, path
from skimage import io
from edsdk import (CameraCommand, ObjectEvent, FileCreateDisposition, Access, EdsObject, PropID, PropertyEvent, SaveTo, ISOSpeedCamera, AEMode, AFMode, Av, Tv, ImageQuality)

verbose = 4
exposureGoal = 0.85*2**14 # possibly different for R7

class Canon:
		copyPicture = False # this is to copy the file from the SD card, not create a numpy object from image data
		buildNumpyImage = True
		milliseconds = {
				30000:'30\"', 25000:'25\"', 20000:'20\"', 15000:'15\"', 13000:'13\"', 10000:'10\"',
				8000:'8\"', 6000:'6\"', 5000:'5\"', 4000:'4\"', 3200:'3\"2', 3000:'3',
				2500:'2\"5', 2000:'2', 1600:'1\"6', 1500:'1\"5', 1333:'1\"3', 1000:'1',
				800:'0\"8', 700:'0\"7', 600:'0\"6', 500:'0\"5', 400:'0\"4', 300:'0\"3',
				250:'1/4', 200:'1/5', 167:'1/6', 125:'1/8', 100:'1/10', 77:'1/13',
				67:'1/15', 50:'1/20', 40:'1/25', 33:'1/30', 25:'1/40', 22:'1/45',
				20:'1/50', 17:'1/60', 13:'1/80', 11:'1/90', 10:'1/100', 8:'1/125',
				6:'1/160', 5:'1/200', 4:'1/250', 3:'1/320', 2:'1/500', 1:'1/750'
		}
		# not using fractions of a second that already have an equivalent setting in milliseconds: 1/350, 1/400, 1/640, 1/180, 1/800, 
		# 1/1000, 1/1250, 1/1500, 1/1600, 1/2000, 1/2500, 1/3000, 1/3200, 1/4000, 1/5000, 1/6000, 1/6400, 1/8000, 1/10000, 1/12800, 1/16000
		# not using third stops: 20\" (1/3), 10\" (1/3), 6\" (1/3), 0\"3 (1/3), 1/6 (1/3), 1/10 (1/3), 1/20 (1/3)
		def __init__(self,config,target):
			self.reports = []
			self.config = config
			self.target = target
			print("Initializing...")
			edsdk.InitializeSDK()
			cam_list = edsdk.GetCameraList()
			if edsdk.GetChildCount(cam_list) == 0:
				print("No Canon cameras connected")
				exit(1)
			self.camera = edsdk.GetChildAtIndex(cam_list, 0)
			print("Starting camera session...")
			edsdk.OpenSession(self.camera)
			print("Setting object event handler")
			edsdk.SetObjectEventHandler(self.camera, ObjectEvent.All, self.callback_object)
			print("Setting gain to %s"%(config['gain']))
			edsdk.SetPropertyData(self.camera,PropID.ISOSpeed,0,getattr(ISOSpeedCamera,config['gain']))
			print("Setting aperture to %s"%(config['aperture']))
			edsdk.SetPropertyData(self.camera,PropID.Av,0,self.codeLookup(config['aperture']))
			edsdk.GetEvent()
		def showInfo(self):
				print("Product name is %s"%(edsdk.GetPropertyData(self.camera,PropID.ProductName,0)))
				print("Gain reported from camera is %s"%(ISOSpeedCamera(edsdk.GetPropertyData(self.camera,PropID.ISOSpeed,0)).name))
				print("Aperture reported from camera is %s"%(Av[edsdk.GetPropertyData(self.camera,PropID.Av,0)]))
				print("Auto Exposure Mode is %s"%(AEMode(edsdk.GetPropertyData(self.camera,PropID.AEMode,0)).name))
				print("Auto Focus Mode is %s"%(AFMode(edsdk.GetPropertyData(self.camera,PropID.AFMode,0)).name))
				print("Image Quality is %s"%(ImageQuality(edsdk.GetPropertyData(self.camera,PropID.ImageQuality,0)).name))
				print("Save To setting is %s"%(SaveTo(edsdk.GetPropertyData(self.camera,PropID.SaveTo,0)).name))
				edsdk.GetEvent()
		def setWheel(self,wheel):
				if wheel == 'NoFilter':
						print("No filter besides built-in Bayer RGGB")
				elif wheel == 'BayerRGGB':
						print("No filter besides built-in Bayer RGGB")
				else:
						print("Canon cameras do not have software controlled filter wheels. Settings are descriptive, not prescriptive. Set filter to NoFilter if appropriate.")
		def shoot(self,light,wheel,exposure):
				self.light = light
				self.wheel = wheel
				self.exposure = exposure
				self.exposure = int(self.exposure.strip('ms'))
				if not self.exposure in self.milliseconds:
						self.exposure = min(self.milliseconds.keys(),key=lambda k: abs(k-self.exposure))
						print("Rounding to %s ms, or %s seconds"%(self.exposure,self.milliseconds[self.exposure])) if verbose > 1 else None
				print("Setting exposure time to %s"%(self.exposure)) if verbose > 4 else None
				waitForCamera = self.exposure/1000 + 5 # at four failed on 30sec exposure
				edsdk.SetPropertyData(self.camera,PropID.Tv,0,self.codeLookup(self.milliseconds[self.exposure]))
				edsdk.GetEvent()
				width = 6960 # for purposes of calculating memory to reserve, 4752 on t1i, 6960 on r7
				height = 4640 # not super precise because of compression, 3168 on t1i, 4640 on r7
				imageData = bytes(width*height*2) # 1 for 8-bit, 2 for 16-bit, 3 for three channels of 8-bit	.... won't need all that space because compressed
				self.memStream = edsdk.CreateMemoryStreamFromPointer(imageData)
				edsdk.SendCommand(self.camera,CameraCommand.TakePicture,0)
				time.sleep(waitForCamera)
				edsdk.GetEvent()
				if False:
						with rawpy.imread(BytesIO(imageData)) as raw:
								img = raw.raw_image.copy()
						print("We now have a numpy object named img with shape %s dtype %s range %s - %s"%(img.shape,img.dtype,np.min(img),np.max(img)))
				with rawpy.imread(BytesIO(imageData)) as raw: 
						self.saveRawFunction(raw) 
		def close(self):
				for report in self.reports:
					print(report)
				print("Closing camera session")
				edsdk.CloseSession(self.camera)
				print("Terminating software development kit")
				edsdk.TerminateSDK()
		def codeLookup(self,requested):
				codes = []
				if requested.lower().startswith('f'):
						requested = requested.strip('Ff ')
						codes = [key for key, value in Av.items() if value == requested]
				else:
						codes = [key for key, value in Tv.items() if value == requested]
				if len(codes) == 1:
						return codes[0]
				if len(codes) > 1:
						print("More than one match, using the first:",str(codes[0]))
						return codes[0]
				if len(codes) < 1:
						print("Did not find a match for requested setting",requested)
						print("Recognized aperture settings are F: 1, 1.1, 1.2, 1.2 (1/3), 1.4, 1.6, 1.8, 1.8 (1/3), 2, 2.2, 2.5, 2.5 (1/3), 2.8, 3.2, 3.4, 3.5, 3.5 (1/3), 4, 4.5, 4.5, 5.0, 5.6, 6.3, 6.7, 7.1, 8, 9, 9.5, 10, 11, 13 (1/3), 13, 14, 16, 18, 19, 20, 22, 25, 27, 29, 32, 36, 38, 40, 45, 51, 54, 57, 64, 72, 76, 80, 91")
						print("Recognized exposure times are: 30\",25\",20\",20\" (1/3),15\",13\",10\",10\" (1/3),8\",6\" (1/3),6\",5\",4\",3\"2,3,2\"5,2,1\"6,1\"5,1\"3,1,0\"8,0\"7,0\"6,0\"5,0\"4,0\"3,0\"3 (1/3),1/4,1/5,1/6,1/6 (1/3),1/8,1/10 (1/3),1/10,1/13,1/15,1/20 (1/3),1/20,1/25,1/30,1/40,1/45,1/50,1/60,1/80,1/90,1/100,1/125,1/160,1/180,1/200,1/250,1/320,1/350,1/400,1/500,1/640,1/750,1/800,1/1000,1/1250,1/1500,1/1600,1/2000,1/2500,1/3000,1/3200,1/4000,1/5000,1/6000,1/6400,1/8000,1/10000,1/12800,1/16000")
						exit()
		def callback_object(self,event:ObjectEvent,object_handle:EdsObject): 
				print("Object event! Event %s created object %s"%(ObjectEvent(event).name,object_handle)) if verbose > 4 else None
				if event == ObjectEvent.DirItemCreated:
						print("Directory item created on the camera") if verbose > 4 else None
						if self.copyPicture:
								print("Ready to copy file from camera to Pictures directory") if verbose > 4 else None
								self.copy_image(object_handle)
						if self.buildNumpyImage:
								print("Ready to build numpy image") if verbose > 4 else None
								self.buildNumpyFunction(object_handle)
		def copy_image(self,object_handle): 
				fileExtension = 'cr2'
				directory = path.join(self.config['basepath'],self.target,fileExtension.upper)
				if not path.exists(directory):
						makedirs(directory)
				timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
				self.wheel = 'BayerRGGB'
				if self.config['cool']:
						gainDesc = 'gain'+str(self.config['gain'])+'_'+str(self.config['cool']).strip('-')
				else:
						gainDesc = 'gain'+str(self.config['gain'])
				outfileName = '-'.join([
						self.target,
						self.config['sensor'],
						self.config['lens'],
						self.config['aperture'],
						gainDesc,
						self.light,
						self.wheel,
						str(self.exposure)+'ms',
						timestamp+'.'+fileExtension])
				outfilePath = path.join(directory,outfileName)
				dir_item_info = edsdk.GetDirectoryItemInfo(object_handle)
				print("Ready to copy image from camera SD card %s"%(dir_item_info))
				print("Ready to create file stream %s"%(outfilePath))
				out_stream = edsdk.CreateFileStream(outfilePath, FileCreateDisposition.CreateAlways, Access.ReadWrite)
				edsdk.Download(object_handle, dir_item_info["size"], out_stream)
				edsdk.DownloadComplete(object_handle)
		def buildNumpyFunction(self,object_handle): 
				dir_item_info = edsdk.GetDirectoryItemInfo(object_handle)
				print("Note: ObjectFormat 10874880 = 0xA5F000 = Canon Raw") if verbose > 4 else None
				print("Copying image data from camera SD card to RAM with size %s"%(dir_item_info["size"])) if verbose > 4 else None
				edsdk.Download(object_handle,dir_item_info["size"],self.memStream)
				print("Download Complete") if verbose > 5 else None
				edsdk.DownloadComplete(object_handle)
		def saveRawFunction(self,raw):
				bayerChannels = {0:'BayerR',1:'BayerG',2:'BayerB'}
				directory = path.join(self.config['basepath'],self.target,'Raw')
				if not path.exists(directory):
						makedirs(directory)
				timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
				fileExtension = 'tif'
				self.wheel = 'BayerRGGB'
				if 'cool' in self.config:
						gainDesc = 'gain'+str(self.config['gain'])+'_'+str(self.config['cool']).strip('-')
				else:
						gainDesc = 'gain'+str(self.config['gain'])
				outfileName = '-'.join([
						self.target,
						self.config['sensor'],
						self.config['lens'],
						self.config['aperture'],
						gainDesc,
						self.light,
						self.wheel,
						str(self.exposure)+'ms',
						timestamp+'.'+fileExtension])
				outfilePath = path.join(directory,outfileName)
				io.imsave(path.join(directory,outfilePath),raw.raw_image.copy(),check_contrast=False)
				report = f">>> {self.light:<15} 98th percentile of raw image is {np.percentile(raw.raw_image.copy(),98):>5.0f} after {self.exposure:>5.0f}, consider {exposureGoal*self.exposure/np.percentile(raw.raw_image.copy(),98):5.0f}"
				print(report)
				self.reports.append(report)
				half_size=True # each 2x2 block becomes one pixel in each of three channels without interpolation
				no_auto_bright=True # see https://letmaik.github.io/rawpy/api/rawpy.Params.html and https://www.libraw.org/docs/API-datastruct-eng.html
				no_auto_scale=True # Not as artificial as auto_bright
				gamma=(1,1) # None for default setting of power = 2.222 and slope = 4.5; (1,0) for linear; when power is 1 it does not matter if slope is 1 or 0
				output_bps=16 # 8 or 16 bits per sample
				print("Settings:\n\thalf_size: %s\n\tno_auto_bright: %s\n\tno_auto_scale: %s\n\tgamma (power, slope): %s\n\toutput_bps: %s"%(half_size,no_auto_bright,no_auto_scale,gamma,output_bps)) if verbose > 4 else None
				raw = raw.postprocess(half_size=half_size,no_auto_bright=no_auto_bright,gamma=gamma,no_auto_scale=no_auto_scale,output_bps=output_bps)
				height,width,channels = raw.shape
				print("Processed image is %s pixels high, %s pixels wide, and %s channels deep with each pixel described with %s data"%(height,width,channels,raw.dtype)) if verbose > 4 else None
				if 'cool' in self.config:
						gainDesc = 'gain'+str(self.config['gain'])+'_'+str(self.config['cool']).strip('-')
				else:
						gainDesc = 'gain'+str(self.config['gain'])
				for channel in range(channels):
						self.wheel = bayerChannels[channel]
						outfileName = '-'.join([
								self.target,
								self.config['sensor'],
								self.config['lens'],
								self.config['aperture'],
								gainDesc,
								self.light,
								self.wheel,
								str(self.exposure)+'ms',
								timestamp+'.'+fileExtension])
						outfilePath = path.join(directory,outfileName)
						io.imsave(path.join(directory,outfilePath),raw[:,:,channel],check_contrast=False)

