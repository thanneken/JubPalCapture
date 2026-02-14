import time
import os
from datetime import datetime
import PySpin
import numpy as np
from skimage import io
import math

"""
https://softwareservices.flir.com/FFY-U3-04S2/latest/Model/public/ImageFormatControl.html
	describes roi, binning, pixel format, adc bit depth
Acquisition Modes
	single frame... I think even live view is one frame at a time, not true video stream
	continuous
		self.camera.AcquisitionMode.SetValue(PySpin.AcquisitionMode_Continuous)
	multi-frame
"""

verbose = True
reportheader = '___MS__|_MAYBE_|_98THP_|__SAT__|__MIN__|__MAX__|______LIGHT______|______FILTER_____'

class Flir():

	def __init__(self):
		print("Initializing Flir Camera")
		self.rotate = False
		self.system = PySpin.System.GetInstance()
		self.cam_list = self.system.GetCameras()
		if self.cam_list.GetSize() == 0:
			print("Flir camera not detected")
			exit() 
		elif self.cam_list.GetSize() > 1:
			print("Taking the first of the Flir cameras detected")
		self.camera = self.cam_list.GetByIndex(0)
		self.camera.Init()
		self.camera.ExposureAuto.SetValue(PySpin.ExposureAuto_Off)
		self.camera.ExposureTime.SetValue(1000000) # Necessary?
		self.camera.GainAuto.SetValue(PySpin.GainAuto_Off)
		self.camera.AutoExposureTargetGreyValueAuto.SetValue(PySpin.AutoExposureTargetGreyValueAuto_Off)
		self.camera.GammaEnable.SetValue(False)
		self.camera.BlackLevelSelector.SetValue(PySpin.BlackLevelSelector_All)
		sNodemap = self.camera.GetTLStreamNodeMap()
		node_bufferhandling_mode = PySpin.CEnumerationPtr(sNodemap.GetNode('StreamBufferHandlingMode'))
		node_newestonly = node_bufferhandling_mode.GetEntryByName('NewestOnly')
		node_newestonly_mode = node_newestonly.GetValue()
		node_bufferhandling_mode.SetIntValue(node_newestonly_mode)

	def session(self,config,target): 
		print("Configuring session")
		self.config = config
		self.target = target
		self.reports = []
		offset = 1.5
		if target == 'liveview':
			print("Using Continuous Acquisition Mode")
			self.camera.AcquisitionMode.SetValue(PySpin.AcquisitionMode_Continuous) 
		else:
			print("Using SingleFrame Acquisition Mode")
			self.camera.AcquisitionMode.SetValue(PySpin.AcquisitionMode_SingleFrame) 
		print(f"Setting offset to {offset}")
		self.camera.BlackLevel.SetValue(offset)
		if 'gain' in config:
			print(f"Setting gain to {config['gain']}")
			self.camera.Gain.SetValue(float(config['gain'])) # float in decibels
		else:
			print("Setting gain to 11.1 db")
			self.camera.Gain.SetValue(11.1) 
		if 'bpp' in config:
			self.SetBit(config['bpp'])
		else:
			self.SetBit(16)
		self.SetBinMode(1,1) 

	def showInfo(self):
		print("Width in pixels: %s"%(self.camera.Width.GetMax()))
		print("Height in pixels: %s"%(self.camera.Height.GetMax()))

	def GetLiveFrame(self):
		if not self.camera.IsStreaming():
			print("Begin Acquisition")
			self.camera.BeginAcquisition()
			time.sleep(2)
		while not self.camera.IsStreaming():
			print("Giving the camera two seconds to catch up")
			time.sleep(2)
		image_result = self.camera.GetNextImage()
		while image_result.IsIncomplete():
			print("Waiting for complete image")
			time.sleep(1)
			image_result = self.camera.GetNextImage()
		img = image_result.GetNDArray()
		image_result.Release()
		if self.rotate:
			np.rot90(img,2)
		return img

	def shoot(self,light,wheel,exposure):
		if exposure > 29900:
			print("Flir cannot accept exposure times longer than 29.9 seconds. Capping...")
			exposure = 29900
		self.SetExposure(exposure)# self.SetExposure(self,exposure)
		if True:
			self.camera.BeginAcquisition()
		print("Shooting for %sms"%(exposure))
		image_result = self.camera.GetNextImage()
		while image_result.IsIncomplete():
			print("Waiting for complete image")
			time.sleep(1)
			image_result = self.camera.GetNextImage()
		img = image_result.GetNDArray()
		image_result.Release()
		if True:
			self.camera.EndAcquisition()
		if self.rotate:
			np.rot90(img,2)
		if True:
			exposureGoal = 0.85*2**16 # might be 2**12 on flir
			suggestion = exposureGoal*int(exposure)/np.percentile(img,98)
			saturatedpct = 100 * np.count_nonzero(img > 64000) / np.count_nonzero(img) # might be lower on flir
			report = f"{exposure:_>6}_|{suggestion:_>6.0f}_|{np.percentile(img,98):_>6.0f}_|{saturatedpct:_>5.1f}%_|{np.min(img):_>6}_|{np.max(img):_>6}_|{light:_^17}|{wheel:_^17}" # report = f"{light:-<10}{wheel:-<10}{exposure:->5}ms pixel values range {np.min(img):>5} - {np.max(img):5} with 98th percentile of {np.percentile(img,98):>5.0f} and {saturatedpct:>3.1f}% of pixels above 64000, consider {suggestion:5.0f}"
			print(reportheader)
			print(report)
			self.reports.append(report)
		directory = os.path.join(self.config['basepath'],self.target,'Raw')
		if not os.path.exists(directory):
			os.makedirs(directory)
		timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
		fileExtension = 'tif'
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
			light,
			wheel,
			str(exposure)+'ms',
			timestamp+'.'+fileExtension])
		outfilePath = os.path.join(directory,outfileName)
		print("Saving %s"%(outfilePath))
		io.imsave(outfilePath,img,check_contrast=False)

	def close(self):
		print(reportheader)
		for report in self.reports:
			print(report)
		print("Closing Flir camera")
		if self.camera is not None:
			if self.camera.IsStreaming():
				self.camera.EndAcquisition()
			self.camera.DeInit()
			del self.camera
			self.camera = None
		if self.cam_list is not None:
			self.cam_list.Clear()
			self.cam_list = None
		if self.system is not None:
			self.system.ReleaseInstance()
			self.system = None

	def setWheel(self,wheelNewPosition): 
		print("No wheel to set")

	def evenInteger(self,n):
		return math.ceil(n / 4) * 4

	def SetROI(self,roiX,roiY,roiW,roiH):
		if self.camera.IsStreaming():
			self.camera.EndAcquisition()
			print("Ending acquisition")
		print(f"Changing ROI to x,y,w,h = {roiX},{roiY},{roiW},{roiH}")
		self.camera.OffsetX.SetValue(self.evenInteger(roiX))
		self.camera.OffsetY.SetValue(self.evenInteger(roiY))
		if PySpin.IsWritable(self.camera.Width):
			self.camera.Width.SetValue(self.evenInteger(roiW))
			self.camera.Height.SetValue(self.evenInteger(roiH))
		else:
			print("Width cannot be changed at this time")

	def SetBit(self,bpp):
		"""
		Pixel format is not to be confused with analog to digital converter (adc) bit depth
		"""
		if bpp == 8:
			print("Setting Pixel Format to Mono8")
			self.camera.PixelFormat.SetValue(PySpin.PixelFormat_Mono8)
		else:
			print("Setting Pixel Format to Mono16")
			self.camera.PixelFormat.SetValue(PySpin.PixelFormat_Mono16)
			
	def SetBinMode(self,binX,binY):
		if self.camera.IsStreaming():
			self.camera.EndAcquisition()
			print("Ending acquisition")
		if True:
			print(f"Setting binning to {binX} × {binY}")
			self.camera.BinningSelector.SetValue(PySpin.BinningSelector_All) # Sensor
			self.camera.BinningHorizontalMode.SetValue(PySpin.BinningHorizontalMode_Sum) # Additive better for short exposures, Average better for SNR
			self.camera.BinningVerticalMode.SetValue(PySpin.BinningVerticalMode_Sum) # self.camera.BinningVerticalMode.SetValue('Additive')
			self.camera.BinningHorizontal.SetValue(int(binX))
			self.camera.BinningVertical.SetValue(binY)

	def SetExposure(self,exposure):
		self.camera.ExposureTime.SetValue(int(exposure)*1000) # camera takes microseonds

if __name__ == "__main__":
	print("This is not meant to be run but called from capture.py and liveview.py")
