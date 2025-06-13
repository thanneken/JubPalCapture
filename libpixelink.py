import time
import datetime
import numpy as np
from pixelinkWrapper import *
import sys

class Pixelink():
	hCamera = None
	frame = None

	def __init__(self):
		print("Initializing Pixelink Camera")
		self.hCamera = None
		self.frame = None
		ret = PxLApi.initialize(0)
		self.hCamera = ret[1]

	def session(self,config,target): 
		"""
		Not able to find ability to set offset
		"""
		print("Configuring session")
		self.reports = []
		self.config = config
		self.target = target
		self.SetGain(self,float(config['gain']))
		if 'bpp' in config:
			self.SetBitDepth(self,config['bpp'])
		else:
			self.SetBitDepth(self,16)
		self.Begin_Acquisition(self)

	def SetGain(self,db):
		ret = PxLApi.getFeature(self.hCamera, PxLApi.FeatureId.GAIN) 
		params = ret[2]
		print(f"Gain had been {params[0]}, changing to {db}")
		params[0] = db # worth checking with more than one setting
		ret = PxLApi.setFeature(self.hCamera, PxLApi.FeatureId.GAIN, PxLApi.FeatureFlags.MANUAL, params)

	def SetBitDepth(self,bpp): 
		ret = PxLApi.getFeature(self.hCamera, PxLApi.FeatureId.PIXEL_FORMAT) # PIXEL_FORMAT_MONO8 (0), PIXEL_FORMAT_MONO16 (1), PIXEL_FORMAT_MONO12_PACKED, PIXEL_FORMAT_MONO12_PACKED_MSFIRST 
		params = ret[2]
		if bpp == 8:
			params[0] = PxLApi.PixelFormat.MONO8
		else:
			params[0] = PxLApi.PixelFormat.MONO16 
		ret = PxLApi.setFeature(self.hCamera, PxLApi.FeatureId.PIXEL_FORMAT, PxLApi.FeatureFlags.MANUAL, params)
		self.bpp = bpp

	def Begin_Acquisition(self):
		"""
		self.frame needs to know size and bit depth
		"""
		ret = PxLApi.getFeature(self.hCamera, PxLApi.FeatureId.ROI)
		params = ret[2]
		self.roiWidth = int(params[PxLApi.RoiParams.WIDTH])
		self.roiHeight = int(params[PxLApi.RoiParams.HEIGHT])
		ret = PxLApi.getFeature(self.hCamera, PxLApi.FeatureId.PIXEL_ADDRESSING)
		params = ret[2]
		if not params[PxLApi.PixelAddressingParams.X_VALUE] == params[PxLApi.PixelAddressingParams.Y_VALUE]:
			print("Check why binning is not square... exiting...")
			exit()
		self.binXY = params[PxLApi.PixelAddressingParams.X_VALUE] 
		self.imgWidth = self.roiWidth / self.binXY
		self.imgHeight = self.roiHeight / self.binXY
		ret = PxLApi.getFeature(self.hCamera, PxLApi.FeatureId.PIXEL_FORMAT) 
		params = ret[2]
		pixelFormat = int(params[0])
		self.bpp = 8 * PxLApi.getBytesPerPixel(pixelFormat) # returns bytes per pixel, so multiply for bits per pixel
		if self.bpp == 16:
			print(f"Confirmed using {self.bpp} bits per pixel")
			self.frame = np.zeros([self.imgHeight, self.imgWidth], dtype=np.uint16) 
		else:
			print(f"Using {self.bpp}! Fix that before proceeding...")
			exit() # or self.frame = np.zeros([self.imgHeight, self.imgWidth], dtype=np.uint8) 
		PxLApi.setStreamState(self.hCamera, PxLApi.StreamState.START)

	def End_Acquisition(self):
		PxLApi.setStreamState(self.hCamera, PxLApi.StreamState.STOP)

	def showInfo(self):
		print(f"Pixel dimensions {self.roiWidth} × {self.roiHeight} binned to {self.binXY} for {self.imgWidth} × {self.imgHeight} with {self.bpp} bits per pixel")
		ret = PxLApi.getCameraInfo(hCamera)
		cameraInfo = ret[1]
		self.name = cameraInfo.CameraName.decode("utf-8")
		print("Name -------------- '%s'" % cameraInfo.CameraName.decode("utf-8"))
		print("Description ------- '%s'" % cameraInfo.Description.decode("utf-8"))
		print("Vendor Name ------- '%s'" % cameraInfo.VendorName.decode("utf-8"))
		print("Serial Number ----- '%s'" % cameraInfo.SerialNumber.decode("utf-8"))
		print("Firmware Version -- '%s'" % cameraInfo.FirmwareVersion.decode("utf-8"))
		print("FPGA Version ------ '%s'" % cameraInfo.FPGAVersion.decode("utf-8"))
		print("XML Version ------- '%s'" % cameraInfo.XMLVersion.decode("utf-8"))
		print("Bootload Version -- '%s'" % cameraInfo.BootloadVersion.decode("utf-8"))
		print("Model Name -------- '%s'" % cameraInfo.ModelName.decode("utf-8"))
		print("Lens Description -- '%s'" % cameraInfo.LensDescription.decode("utf-8"))
		ret = PxLApi.getFeature(self.hCamera, PxLApi.FeatureId.SENSOR_TEMPERATURE)
		params = ret[2]
		print("Sensor Temp °C ---- '%s'" % params[0])

	def SetExposure(self, exposureMS):
		ret = PxLApi.getFeature(self.hCamera, PxLApi.FeatureId.EXPOSURE)
		params = ret[2]
		params[0] = exposureMS/1000 # confirm that takes seconds
		ret = PxLApi.setFeature(self.hCamera, PxLApi.FeatureId.EXPOSURE, PxLApi.FeatureFlags.MANUAL, params)

	def shoot(self,light,wheel,exposure):
		SetExposure(exposure)
		for i in range(5): # try five times to get a frame
			ret = PxLApi.getNextNumPyFrame(self.hCamera,self.frame)
			if PxLApi.apiSuccess(ret[0]):
				break
		if True:
			exposureGoal = 0.85*2**16 # might be 2**12 on pixelink
			suggestion = exposureGoal*int(exposure)/np.percentile(img,98)
			saturatedpct = 100 * np.count_nonzero(img > 64000) / np.count_nonzero(img) # might be lower on pixelink
			report = f"{light:-<10}{wheel:-<10}{exposure:->5}ms pixel values range {np.min(img):>5} - {np.max(img):5} with 98th percentile of {np.percentile(img,98):>5.0f} and {saturatedpct:>3.1f}% of pixels above 64000, consider {suggestion:5.0f}"
			print(report)
			self.reports.append(report)
		directory = path.join(self.config['basepath'],self.target,'Raw')
		if not path.exists(directory):
			makedirs(directory)
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
			self.light,
			self.wheel,
			str(self.exposure)+'ms',
			timestamp+'.'+fileExtension])
		outfilePath = path.join(directory,outfileName)
		print("Saving %s"%(outfilePath))
		io.imsave(outfilePath,self.frame,check_contrast=False)

	def close(self):
		print("Closing Pixelink camera")
		for report in self.reports:
			print(report)
		End_Acquisition(self)
		ret = PxLApi.setStreamState(self.hCamera, PxLApi.StreamState.STOP)
		if self.hCamera is not None:
			ret = PxLApi.uninitialize(self.hCamera)
			self.hCamera = None

	def setWheel(self,wheelNewPosition): 
		print("No wheel to set")

	def SetBinMode(self,binX,binY):
		"""
		pixelink calls it pixel addressing in binning mode (2)
		avoid decimation mode (0)
		7620 supports 2x2 binning
		stop stream first
		parameters
			fValue
			fMode
			fHorizontal Value
			fVerticalValue
		redo self.frame size calculation
		"""
		End_Acquisition(self)
		ret = PxLApi.getFeature(self.hCamera, PxLApi.FeatureId.PIXEL_ADDRESSING) 
		params = ret[2]
		if binX == 1:
			params[0] = PxLApi.PixelAddressingValues.VALUE_NONE
		else:
			params[0] = PxLApi.PixelAddressingValues.VALUE_BY_2
		params[1] = PxLApi.PixelAddressingModes.BIN 
		params[2] = binX
		params[3] = binY
		ret = PxLApi.setFeature(self.hCamera, PxLApi.FeatureId.PIXEL_ADDRESSING, PxLApi.FeatureFlags.MANUAL, params)
		Begin_Acquisition(self)

	def SetROI(self,roiX,roiY,roiW,roiH):
		"""
		x possible values range 0-5408 in steps of 8 (default 0)
		y possible values range 0-3584 in steps of 8 (default 0)
		w possible values range 64-5472 in steps of 8 (default 5472)
		h possible values range 64-3648 in steps of 8 (default 3648)
		"""
		print(f"Stopping acquire mode to change ROI to x,y,w,h = {roiX},{roiY},{roiW},{roiH}")
		End_Acquisition(self)
		ret = PxLApi.getFeature(self.hCamera, PxLApi.FeatureId.ROI) 
		params = ret[2]
		params[0] = roiX
		params[1] = roiY
		params[2] = roiW
		params[3] = roiH
		ret = PxLApi.setFeature(self.hCamera, PxLApi.FeatureId.ROI, PxLApi.FeatureFlags.MANUAL, params)
		print("Restarting acquire mode after changing ROI")
		Begin_Acquisition(self)

	def StopLive(self):
		End_Acquisition(self)

	def BeginLive(self):
		Begin_Acquisition(self)

	def GetLiveFrame(self):
		for i in range(5): # try five times to get a frame
			ret = PxLApi.getNextNumPyFrame(self.hCamera,self.frame)
			if PxLApi.apiSuccess(ret[0]):
				break
		return self.frame

if __name__ == "__main__":
	print("This is not meant to be run but called from capture.py and liveview.py")

