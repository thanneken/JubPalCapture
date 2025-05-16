import time
import datetime
import PySpin
import numpy as np
"""
TODO liveview.py support continuous rather than single frame acquisition mode
resume here with flir examples
	grep -i acquisitionmode ~/Downloads/spinnaker_python/Examples/Python3/*.*
	node_acquisition_mode = PySpin.CEnumerationPtr(nodemap.GetNode('AcquisitionMode'))
	cam.AcquisitionMode.SetValue(PySpin.AcquisitionMode_Continuous)
also internet search of "pyspin acquisitionmode"
then liveview.py itself, perhaps abandon webcam and combine qhy and flir
"""
class Flir():
	def StopLive():
		pass
	def BeginLive():
		pass
	def GetLiveFrame():
		pass
	def __init__(self):
		print("Initializing Flir Camera")
		self.rotate = False
		offset = 1.5
		self.system = PySpin.System.GetInstance()
		self.cam_list = self.system.GetCameras()
		if self.cam_list.GetSize() == 0:
			print("Flir camera not detected")
			exit() 
		self.camera = self.cam_list.GetByIndex(0)
		self.camera.Init()
		self.camera.ExposureAuto.SetValue(PySpin.ExposureAuto_Off)
		self.camera.ExposureTime.SetValue(1000000)
		self.camera.GainAuto.SetValue(PySpin.GainAuto_Off)
		self.camera.AutoExposureTargetGreyValueAuto.SetValue(PySpin.AutoExposureTargetGreyValueAuto_Off)
		self.camera.AcquisitionMode.SetValue(PySpin.AcquisitionMode_SingleFrame) # what about live view?
		self.camera.GammaEnable.SetValue(False)
		self.camera.BlackLevelSelector.SetValue(PySpin.BlackLevelSelector_All)
		self.camera.BlackLevel.SetValue(offset)
		sNodemap = self.camera.GetTLStreamNodeMap()
		node_bufferhandling_mode = PySpin.CEnumerationPtr(sNodemap.GetNode('StreamBufferHandlingMode'))
		node_newestonly = node_bufferhandling_mode.GetEntryByName('NewestOnly')
		node_newestonly_mode = node_newestonly.GetValue()
		node_bufferhandling_mode.SetIntValue(node_newestonly_mode)
	def session(self,config,target): 
		print("Configuring session")
		self.config = config
		self.target = target
		self.camera.Gain.SetValue(int(config['gain']))
	def showInfo(self):
		print("Width in pixels: %s"%(self.camera.Width.GetMax()))
		print("Height in pixels: %s"%(self.camera.Height.GetMax()))
	def shoot(self,light,wheel,exposure):
		self.camera.ExposureTime.SetValue(int(exposure)*1000)
		print("Shooting for %sms"%(exposure))
		image_result = self.camera.GetNextImage()
		while image_result.IsIncomplete():
			print("Waiting for complete image")
			time.sleep(1)
			image_result = self.camera.GetNextImage()
		img = image_result.GetNDArray()
		image_result.Release()
		if self.rotate:
			np.rot90(img,2)
		print("Image has shape %s, dtype %s, range %s - %s, median %s with standard deviation %s"%(img.shape,img.dtype,np.min(img),np.max(img),np.median(img),np.std(img)))
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
	def close(self):
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
	def SetROI(self,roiX,roiY,roiW,roiH):
		self.camera.OffsetX.SetValue(roiX)
		self.camera.OffsetY.SetValue(roiY)
		self.camera.Height.SetValue(roiH)
		self.camera.Width.SetValue(roiW)
	def SetBit(self,bpp):
		print("Received request to set bit depth per pixel to %s. I don't know how to do that."%(bpp))
		print("Manufacturer page suggests data is 10 or 12 bits per pixel. Hereford data is 8 bits per pixel.")
	def SetBinMode(self,binX,binY):
		self.camera.BinningHorizontal.SetValue(binX)
		self.camera.BinningVertical.SetValue(binY)

if __name__ == "__main__":
	print("This is not meant to be run but called from capture.py and liveview.py")
