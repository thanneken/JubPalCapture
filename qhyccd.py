#!/bin/python3
import ctypes
from ctypes import *
import numpy as np
import time
from libqhy import *
from os import makedirs, path
from skimage import io
from datetime import datetime

class Filters:
	NoFilter = 7 # Positions 1-7, not index 0-6
	WrattenBlue98 = 2
	WrattenGreen61 = 3
	WrattenRed25 = 4
	WrattenInfrared87 = 5
	WrattenInfrared87C = 6

class qhyccd():
	def __init__(self):
		# initialize variables 
		self.currentRoiAreaX = c_uint32()
		self.currentRoiAreaY = c_uint32()
		self.currentRoiAreaW = c_uint32()
		self.currentRoiAreaH = c_uint32()
		self.chipw = c_double()
		self.chiph = c_double()
		self.w = c_uint()
		self.h = c_uint()
		self.pixelw = c_double()
		self.pixelh = c_double() 
		self.channels = c_uint32(1)
		self.bpp = c_uint() # 8 or 16 bit can be set here or with SetBit
		# create sdk handle
		self.sdk= CDLL('/usr/local/lib/libqhyccd.so')
		self.sdk.GetQHYCCDParam.restype = c_double
		self.sdk.OpenQHYCCD.restype = ctypes.POINTER(c_uint32)
		# ref: https://www.qhyccd.com/bbs/index.php?topic=6356.0
		if False:
			self.mode = 0 # 1 is stream, 0 is single frame
			self.bpp = c_uint(16) # 8 bit
			self.exposureMS = 100 # 100ms
			self.connect(self.mode)

	def connect(self, mode):
		self.mode = mode
		ret = -1
		self.sdk.InitQHYCCDResource()
		self.sdk.ScanQHYCCD()
		type_char_array_32 = c_char*32
		self.id = type_char_array_32()
		self.sdk.GetQHYCCDId(c_int(0), self.id)    # open the first camera
		print("Open camera:", bytes(self.id).decode())
		self.cam = self.sdk.OpenQHYCCD(self.id)
		self.sdk.SetQHYCCDStreamMode(self.cam, self.mode)  
		self.sdk.InitQHYCCD(self.cam)
		# Get Camera Parameters
		self.sdk.GetQHYCCDChipInfo(self.cam,byref(self.chipw),byref(self.chiph),byref(self.w),byref(self.h),byref(self.pixelw),byref(self.pixelh),byref(self.bpp))
		self.imgdata = (ctypes.c_uint8 * self.w.value* self.h.value)()
		if False:
			self.SetExposure( self.exposureMS )
			self.roi_w = self.w
			self.roi_h = self.h #TODO: keep roi between stream mode change
			self.SetBit(self.bpp.value)
			self.sdk.SetQHYCCDParam(self.cam, CONTROL_ID.CONTROL_TRANSFERBIT, self.bpp)
			self.SetROI(0, 0, self.w.value, self.h.value)
		self.sdk.SetQHYCCDParam(self.cam, CONTROL_ID.CONTROL_USBTRAFFIC, c_double(50))
		# Maximum fan speed
		self.sdk.SetQHYCCDParam(self.cam, CONTROL_ID.CONTROL_MANULPWM, c_double(255)) # seems to be not working but fan is certainly running even with reported value 0

	def session(self,config,target): 
		self.config = config
		self.target = target
		self.connect(0)
		self.roi_w = self.w
		self.roi_h = self.h 
		self.SetROI(0, 0, self.w.value, self.h.value)
		self.SetBit(16)
		self.SetBinMode(1,1)
		print("Setting gain to %s"%(self.config['gain']))
		self.SetGain(self.config['gain'])
		print("Setting cooling to %s"%(self.config['cool'])) 
		self.SetCooler(self.config['cool'])
		while self.CheckTemp() > 0.98*self.config['cool']:
			print("Waiting for current temp %s to reach target temp %s"%(self.CheckTemp(),self.config['cool']))
			time.sleep(3)

	def SetStreamMode(self, mode):
		""" TODO: Unable to change"""
		self.sdk.CloseQHYCCD(self.cam)
		self.mode = mode
		self.connect(mode)

	"""Set camera exposure in ms, return actual exposure after setting """
	def SetExposure(self, exposureMS):
		# sdk exposure uses us as unit
		self.exposureMS = exposureMS # input ms
		self.sdk.SetQHYCCDParam(self.cam, CONTROL_ID.CONTROL_EXPOSURE, c_double(exposureMS*1000))
		print("Set exposure to",self.sdk.GetQHYCCDParam(self.cam,CONTROL_ID.CONTROL_EXPOSURE)/1000)

	""" Set camera gain """
	def SetGain(self, gain):
		self.sdk.SetQHYCCDParam(self.cam, CONTROL_ID.CONTROL_GAIN, c_double(gain))

	""" Set cooler """
	def SetCooler(self,cool): # Cooler to -15
		self.sdk.SetQHYCCDParam(self.cam, CONTROL_ID.CONTROL_COOLER, c_double(cool))
	
	""" Set camera depth """
	def SetBit(self, bpp):
		self.bpp.value = bpp
		self.sdk.SetQHYCCDParam(self.cam, CONTROL_ID.CONTROL_TRANSFERBIT, c_double(bpp))

	""" Set camera ROI """
	def SetROI(self, x0, y0, roi_w, roi_h):
		self.roi_w =  c_uint(roi_w)
		self.roi_h =  c_uint(roi_h)
		# update buffer to recive camera image
		if self.bpp.value == 16:
			self.imgdata = (ctypes.c_uint16 * roi_w * roi_h)()
			self.sdk.SetQHYCCDResolution(self.cam, x0, y0, self.roi_w, self.roi_h)
		else: # 8 bit
			self.imgdata = (ctypes.c_uint8 * roi_w * roi_h)()
			self.sdk.SetQHYCCDResolution(self.cam, x0, y0, self.roi_w, self.roi_h)

	""" Exposure and return single frame """
	def GetSingleFrame(self):
		ret = self.sdk.ExpQHYCCDSingleFrame(self.cam)
		ret = self.sdk.GetQHYCCDSingleFrame(
			self.cam, byref(self.roi_w), byref(self.roi_h), byref(self.bpp),
			byref(self.channels), self.imgdata)
		return np.asarray(self.imgdata) #.reshape([self.roi_h.value, self.roi_w.value])
 
	def BeginLive(self):
		""" Begin live mode"""
		#self.sdk.SetQHYCCDStreamMode(self.cam, 1)  # Live mode
		self.sdk.BeginQHYCCDLive(self.cam)
	
	def GetLiveFrame(self):
		""" Return live image """
		self.sdk.GetQHYCCDLiveFrame(self.cam, byref(self.roi_h), byref(self.roi_w), 
			byref(self.bpp), byref(self.channels), self.imgdata)
		return np.asarray(self.imgdata)

	def StopLive(self):
		""" Stop live mode, change to single frame """
		self.sdk.StopQHYCCDLive(self.cam)
		#self.sdk.SetQHYCCDStreamMode(self.cam, 0)  # Single Mode

	""" Relase camera and close sdk """
	def close(self):
		print("Closing %s"%(bytes(self.id).decode()))
		self.sdk.CloseQHYCCD(self.cam)
		self.sdk.ReleaseQHYCCDResource()
    
	def GetExtraInfo(self):
		print("Getting extra info")
		self.versionYear = c_uint32()
		self.versionMonth = c_uint32()
		self.versionDay = c_uint32()
		self.versionSubday = c_uint32()
		self.sdk.GetQHYCCDSDKVersion(byref(self.versionYear),byref(self.versionMonth),byref(self.versionDay),byref(self.versionSubday))
		print("SDK Version is %s.%s.%s.%s"%(self.versionYear.value,self.versionMonth.value,self.versionDay.value,self.versionSubday.value))
		self.firmwareVersion = c_uint8() 
		self.sdk.GetQHYCCDFWVersion(self.cam,byref(self.firmwareVersion))
		print("Firmware version is %s"%(self.firmwareVersion.value))
		self.numReadModes = c_uint32()
		self.readModeName = (c_char * 32)()
		self.readModeWidth = c_uint32()
		self.readModeHeight = c_uint32()
		self.sdk.GetQHYCCDNumberOfReadModes(self.cam,byref(self.numReadModes))
		print("Number of read modes is %s"%(self.numReadModes.value))
		for count, mode in enumerate(range(self.numReadModes.value)):
				self.sdk.GetQHYCCDReadModeName(self.cam,c_uint32(mode),byref(self.readModeName))
				self.sdk.GetQHYCCDReadModeResolution(self.cam,c_uint32(mode),byref(self.readModeWidth),byref(self.readModeHeight))
				print("Read mode index %s named %s has resolution %s x %s"%(count,bytes(self.readModeName).decode(),self.readModeWidth.value,self.readModeHeight.value))
		self.effectiveAreaX = c_uint32()
		self.effectiveAreaY = c_uint32()
		self.effectiveAreaW = c_uint32()
		self.effectiveAreaH = c_uint32()
		self.sdk.GetQHYCCDEffectiveArea(self.cam,byref(self.effectiveAreaX),byref(self.effectiveAreaY),byref(self.effectiveAreaW),byref(self.effectiveAreaH))
		print("Effective area is X,Y,W,H = %s,%s,%s,%s"%(self.effectiveAreaX.value,self.effectiveAreaY.value,self.effectiveAreaW.value,self.effectiveAreaH.value))
		self.overscanAreaX = c_uint32()
		self.overscanAreaY = c_uint32()
		self.overscanAreaW = c_uint32()
		self.overscanAreaH = c_uint32()
		self.sdk.GetQHYCCDOverScanArea(self.cam,byref(self.overscanAreaX),byref(self.overscanAreaY),byref(self.overscanAreaW),byref(self.overscanAreaH))
		print("Overscan area is X,Y,W,H = %s,%s,%s,%s"%(self.overscanAreaX.value,self.overscanAreaY.value,self.overscanAreaW.value,self.overscanAreaH.value))
		self.sdk.GetQHYCCDCurrentROI(self.cam,byref(self.currentRoiAreaX),byref(self.currentRoiAreaY),byref(self.currentRoiAreaW),byref(self.currentRoiAreaH))
		print("Current ROI is X,Y,W,H = %s,%s,%s,%s"%(self.currentRoiAreaX.value,self.currentRoiAreaY.value,self.currentRoiAreaW.value,self.currentRoiAreaH.value))
		self.memLength = c_uint32()
		self.memLength = self.sdk.GetQHYCCDMemLength(self.cam)
		print("Memory required to safely accept full image is %s"%(self.memLength))
		if False:
			self.pixelPeriod = c_uint32()
			self.linePeriod = c_uint32()
			self.framePeriod = c_uint32()
			self.clocksPerLine = c_uint32()
			self.linesPerFrame = c_uint32()
			self.actualExposureTime = c_uint32()
			self.isLongExposureMode = c_uint8()
			self.sdk.GetQHYCCDPreciseExposureInfo(
				self.cam,
				byref(self.pixelPeriod),
				byref(self.linePeriod),
				byref(self.framePeriod),
				byref(self.clocksPerLine),
				byref(self.linesPerFrame),
				byref(self.actualExposureTime),
				byref(self.isLongExposureMode))
			print("Precise exposure info:")
			print("\tPixel period is %s"%(self.pixelPeriod.value))
			print("\tLine period is %s"%(self.linePeriod.value))
			print("\tFrame period is %s"%(self.framePeriod.value))
			print("\tClocks per line is %s"%(self.clocksPerLine.value))
			print("\tLines per frame is %s"%(self.linesPerFrame.value))
			print("\tActual exposure time is %s"%(self.actualExposureTime.value))
			print("\tIs long exposure mode is %s"%(self.isLongExposureMode.value))
		self.sensorName = (c_char * 32)()
		self.sdk.GetQHYCCDSensorName(self.cam,byref(self.sensorName))
		print("Sensor name is %s"%(bytes(self.sensorName).decode()))
    
	def CheckAllParameters(self):
		self.controlMin = c_double()
		self.controlMax = c_double()
		self.controlStep = c_double()
		listUnavailableControls = []
		for controllable in [a for a in dir(CONTROL_ID) if not a.startswith('__')]: 
			available = self.sdk.IsQHYCCDControlAvailable(self.cam,getattr(CONTROL_ID,controllable)) 
			if available < 0:
				listUnavailableControls.append(controllable)
			else:
				controlCurrentValue = self.sdk.GetQHYCCDParam(self.cam,getattr(CONTROL_ID,controllable))
				if controlCurrentValue == 0xffffffff:
					controlCurrentValue = 'NOT SET'
				self.sdk.GetQHYCCDParamMinMaxStep(self.cam,getattr(CONTROL_ID,controllable),byref(self.controlMin),byref(self.controlMax),byref(self.controlStep))
				print("Control %s is currently set to %s with min value %s, max value %s, step %s"
					%(controllable,controlCurrentValue,self.controlMin.value,self.controlMax.value,self.controlStep.value))
		print("Controls available in SDK but not on camera:",listUnavailableControls)

	def CheckTemp(self):
		# return self.sdk.GetQHYCCDParam(self.cam,getattr(CONTROL_ID,CONTROL_CURTEMP))
		return self.sdk.GetQHYCCDParam(self.cam,CONTROL_ID.CONTROL_CURTEMP)

	def setWheel(self,wheelNewPosition): # No clear difference between using parameters and the commands GetQHYCCDCFWStatus and SendOrder2QHYCCDCFW
		if False:
			if self.sdk.IsQHYCCDCFWPlugged(self.cam) < 0:
				print("No filter wheel detected")
				return
		wheelNumSlots = int(self.sdk.GetQHYCCDParam(self.cam,CONTROL_ID.CONTROL_CFWSLOTSNUM))
		try:
			wheelNewPosition = getattr(Filters,wheelNewPosition)
			print("Selected filter is in slot",wheelNewPosition)
		except:
			print("No code for",wheelNewPosition,"so treating as slot number")
			pass
		if wheelNewPosition not in range(1,wheelNumSlots+1):
			print("Illegal wheel position request %s (specify position by slot number, not index)"%(wheelNewPosition))
			return
		wheelNewPosition = int(wheelNewPosition + 47) # offset by 47 when using parameters
		wheelCurrentPosition = self.sdk.GetQHYCCDParam(self.cam,CONTROL_ID.CONTROL_CFWPORT)
		print("Wheel presently at position %s of %s"%(int(wheelCurrentPosition-47),int(wheelNumSlots)))
		self.sdk.SetQHYCCDParam(self.cam,CONTROL_ID.CONTROL_CFWPORT,c_double(wheelNewPosition))
		if wheelNewPosition == 48 and wheelCurrentPosition != 48:
			print("Waiting 5 seconds for wheel to move to first position (fixed value because wheel reports first position while operation is in progress)")
			time.sleep(5)
			wheelCurrentPosition = self.sdk.GetQHYCCDParam(self.cam,CONTROL_ID.CONTROL_CFWPORT)
		elif bytes(self.id).decode().startswith('QHYminiCam'):
			print("Waiting 8 seconds for miniCam wheel to move")
			time.sleep(8)
			wheelCurrentPosition = wheelNewPosition
		else:
			while wheelCurrentPosition != wheelNewPosition:
				print("Waiting for wheel to move from position %s to position %s"%(int(wheelCurrentPosition-47),int(wheelNewPosition-47)))
				time.sleep(1)
				wheelCurrentPosition = self.sdk.GetQHYCCDParam(self.cam,CONTROL_ID.CONTROL_CFWPORT)
		print("Wheel presently at position %s of %s"%(int(wheelCurrentPosition-47),int(wheelNumSlots)))

	def SetBinMode(self,binX,binY):
		newW = int(self.w.value / binX)
		newH = int(self.h.value / binY)
		print("Setting %s × %s binned resolution to %s × %s"%(binX,binY,newW,newH))
		self.sdk.SetQHYCCDBinMode(self.cam,binX,binY)
		self.sdk.SetQHYCCDResolution(self.cam,0,0,newW,newH)

	def showInfo(self):
		print("Camera %s properties"%(bytes(self.id).decode()))
		print("\tchip width = %s"%(self.chipw.value))
		print("\tchip height = %s"%(self.chiph.value))
		print("\twidth in pixels = %s"%(self.w.value))
		print("\theight in pixels = %s"%(self.h.value))
		print("\twidth per pixel w = %s"%(self.pixelw.value))
		print("\theight per pixel = %s"%(self.pixelh.value))
		print("\tchannels = %s"%(self.channels.value))
		print("\tbpp = %s"%(self.bpp.value))
		self.GetExtraInfo()
		self.CheckAllParameters()

	def shoot(self,light,wheel,exposure):
		self.light = light
		self.wheel = wheel
		self.exposure = exposure
		self.SetExposure(int(self.exposure)) 
		img = self.GetSingleFrame()
		print("Image has shape and type %s %s"%(img.shape,img.dtype))
		print("Numpy object has shape %s, dtype %s, range %s - %s, median %s with standard deviation %s"%(img.shape,img.dtype,np.min(img),np.max(img),np.median(img),np.std(img)))
		directory = path.join(self.config['basepath'],self.target,'Raw')
		if not path.exists(directory):
			makedirs(directory)
		timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
		fileExtension = 'tif'
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
		print("Saving %s"%(outfilePath))
		io.imsave(outfilePath,img,check_contrast=False)
