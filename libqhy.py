import ctypes
from ctypes import *
import numpy as np
import time
from os import makedirs, path
from skimage import io
from datetime import datetime

variant = 'megavision'
variant = 'trh'

reportheader = '___MS__|_MAYBE_|_98THP_|__SAT__|__MIN__|__MAX__|______LIGHT______|______FILTER_____'

verbose = 3
linearityHDR = False
if variant == 'megavision':
	exposureGoal = 0.85*38600
	warnsaturation = 37700
else:
	exposureGoal = 0.5*2**16
	exposureGoal = 0.85*2**16
	warnsaturation = 64000

class Filters:
	if variant == 'megavision':
		NoFilter = 1 # 7  on Todd's wheel's, 1 on MegaVision 
		MegaVisionRed = 1
		MegaVisionGreen = 1
		MegaVisionBlue = 1
	else:
		NoFilter = 7 # Positions 1-7, not index 0-6
		WrattenBlue98 = 2
		WrattenGreen61 = 3
		WrattenRed25 = 4
		WrattenInfrared87 = 5
		WrattenInfrared87C = 6
		Position1 = 1

class Qhyccd():
	def __init__(self):
		self.reports = []
		self.x = c_uint()
		self.y = c_uint()
		self.w = c_uint()
		self.h = c_uint()
		self.roi_x =  c_uint() # self.currentRoiAreaX = c_uint32() .... uint32 is an alias for uint
		self.roi_y =  c_uint() # self.currentRoiAreaY = c_uint32()
		self.roi_w =  c_uint() # self.currentRoiAreaW = c_uint32()
		self.roi_h =  c_uint() # self.currentRoiAreaH = c_uint32()
		self.chipw = c_double() # chip width in mm
		self.chiph = c_double() # chip height in mm
		self.pixelw = c_double() # width of a pixel in micrometers, not the width of the sensor in pixels
		self.pixelh = c_double() # height of a pixel in micrometers, not the height of the sensor in pixels
		self.channels = c_uint32(1) 
		self.bpp = c_uint() # 8 or 16 bit can be set here or with SetBit
		self.sdk= CDLL('/usr/local/lib/libqhyccd.so')
		self.sdk.GetQHYCCDParam.restype = c_double
		self.sdk.OpenQHYCCD.restype = ctypes.POINTER(c_uint32)
		# ref: https://www.qhyccd.com/bbs/index.php?topic=6356.0

	def session(self,config,target): 
		self.config = config
		self.target = target
		self.connect(0) # 1 is stream, 0 is single frame
		self.sdk.SetQHYCCDParam(self.cam, CONTROL_ID.CONTROL_USBTRAFFIC, c_double(50))
		self.SetBit(16)
		self.SetBinMode(1,1) # also includes effective pixel area adjustment (drop overscan)
		self.SetROI(self.x.value, self.y.value, self.w.value, self.h.value) 
		if bytes(self.id).decode().startswith('QHYminiCam'):
			if linearityHDR:
				print("Setting read mode to LinearityHDR (it seems to be important to set read mode after gain, perhaps overriding gain setting?)")
				print("Not setting gain or offset in LinearityHDR mode")
				self.SetReadMode(1) # mini read mode 1 is LinearityHDR
			else:
				print("Setting read mode to Photographic (LinearityHDR still needs work)")
				self.SetReadMode(0) # mini read mode 1 is LinearityHDR
				print("Setting offset to 30")
				self.SetOffset(30) # mini offset starts at 30 (factory default?)
				print("Setting gain to %s"%(self.config['gain']))
				self.SetGain(self.config['gain'])
		elif bytes(self.id).decode().startswith('QHY600'):
			self.SetReadMode(0) # 600 read mode 0 is photographic
			self.SetOffset(30) # 600 offset starts at 30 (factory default?)
			print("Setting gain to %s"%(self.config['gain']))
			self.SetGain(self.config['gain'])
		else:
			print("Don't know how to set read mode or offset for this camera")
			print("Setting gain to %s"%(self.config['gain']))
			self.SetGain(self.config['gain'])
		self.sdk.SetQHYCCDParam(self.cam, CONTROL_ID.CONTROL_MANULPWM, c_double(255)) # Maximum fan speed seems to be not working but fan is certainly running even with reported value 0
		print("Setting cooling to %s"%(self.config['cool'])) 
		self.SetCooler(self.config['cool'])
		while self.CheckTemp() > 0.98*self.config['cool']:
			print("Waiting for current temp %s to reach target temp %s"%(self.CheckTemp(),self.config['cool']))
			time.sleep(3)

	def connect(self, mode):
		self.mode = mode # 1 is stream, 0 is single frame
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

	def SetBinMode(self,binX,binY):
		self.sdk.SetQHYCCDBinMode(self.cam,binX,binY) # necessary to set bin mode before query effective area
		self.sdk.GetQHYCCDEffectiveArea(self.cam,byref(self.x),byref(self.y),byref(self.w),byref(self.h))
		self.x = c_uint(int(self.x.value / binX))
		self.y = c_uint(int(self.y.value / binY))
		self.w = c_uint(int(self.w.value / binX))
		self.h = c_uint(int(self.h.value / binY))
		print("Setting %s × %s binned resolution to %s × %s starting at %s, %s"%(binX,binY,self.w.value,self.h.value,self.x.value,self.y.value))
		self.sdk.SetQHYCCDResolution(self.cam,self.x.value,self.y.value,self.w.value,self.h.value) 

	""" Set camera ROI """
	def SetROI(self, newX, newY, newW, newH):
		print("Setting ROI to x,y,w,h = %s,%s,%s,%s"%(newX,newY,newW,newH))
		self.roi_x = c_uint(newX) # likely need to take into account that effective image area does not start at x = 0
		self.roi_y = c_uint(newY)
		self.roi_w = c_uint(newW)
		self.roi_h = c_uint(newH)
		# update buffer to recive camera image
		if self.bpp.value == 16:
			self.imgdata = (ctypes.c_uint16 * newW * newH)()
		else: 
			self.imgdata = (ctypes.c_uint8 * newW * newH)()
		self.sdk.SetQHYCCDResolution(self.cam,newX,newY,newW,newH)

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
		# print("Set exposure to",self.sdk.GetQHYCCDParam(self.cam,CONTROL_ID.CONTROL_EXPOSURE)/1000)

	def SetReadMode(self,readmode):
		self.sdk.SetQHYCCDReadMode(self.cam,readmode)
		print(f"Read mode set to index {readmode}")

	def SetOffset(self,offset):
		self.sdk.SetQHYCCDParam(self.cam, CONTROL_ID.CONTROL_OFFSET, c_double(offset))
	
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
		if variant == 'megavision':
			print(f"LIBQHY: Sending live frame with max value {np.max(self.imgdata)}")
			time.sleep(1)
		return np.asarray(self.imgdata)

	def StopLive(self):
		""" Stop live mode, change to single frame """
		self.sdk.StopQHYCCDLive(self.cam)
		#self.sdk.SetQHYCCDStreamMode(self.cam, 0)  # Single Mode

	""" Relase camera and close sdk """
	def close(self):
		print(reportheader)
		for report in self.reports:
			print(report)
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
		self.sdk.GetQHYCCDCurrentROI(self.cam,byref(self.roi_x),byref(self.roi_y),byref(self.roi_w),byref(self.roi_h))
		print("Current ROI is X,Y,W,H = %s,%s,%s,%s"%(self.roi_x.value,self.roi_y.value,self.roi_w.value,self.roi_h.value))
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
			print("Selected filter is in slot",wheelNewPosition) if verbose > 3 else None
		except:
			print("No code for",wheelNewPosition,"so treating as slot number")
			pass
		if wheelNewPosition not in range(1,wheelNumSlots+1):
			print("Illegal wheel position request %s (specify position by slot number, not index)"%(wheelNewPosition))
			return
		wheelNewPosition = int(wheelNewPosition + 47) # offset by 47 when using parameters
		wheelCurrentPosition = self.sdk.GetQHYCCDParam(self.cam,CONTROL_ID.CONTROL_CFWPORT)
		print("Wheel presently at position %s of %s"%(int(wheelCurrentPosition-47),int(wheelNumSlots))) if verbose > 3 else None
		self.sdk.SetQHYCCDParam(self.cam,CONTROL_ID.CONTROL_CFWPORT,c_double(wheelNewPosition))
		if wheelNewPosition == 48 and wheelCurrentPosition != 48:
			print("Waiting 5 seconds for wheel to move to first position (fixed value because wheel reports first position while operation is in progress)")
			time.sleep(5)
			wheelCurrentPosition = self.sdk.GetQHYCCDParam(self.cam,CONTROL_ID.CONTROL_CFWPORT)
		elif bytes(self.id).decode().startswith('QHYminiCam'):
			if wheelCurrentPosition != wheelNewPosition:
				print("Waiting 8 seconds for miniCam wheel to move")
				time.sleep(8)
			wheelCurrentPosition = wheelNewPosition
		elif bytes(self.id).decode().startswith('QHYminiCam'):
			print("Restore the pause when put filters in minicam")
			wheelCurrentPosition = wheelNewPosition
		else:
			while wheelCurrentPosition != wheelNewPosition:
				print("Waiting for wheel to move from position %s to position %s"%(int(wheelCurrentPosition-47),int(wheelNewPosition-47)))
				time.sleep(1)
				wheelCurrentPosition = self.sdk.GetQHYCCDParam(self.cam,CONTROL_ID.CONTROL_CFWPORT)
		print("Wheel presently at position %s of %s"%(int(wheelCurrentPosition-47),int(wheelNumSlots))) if verbose > 3 else None

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
		self.SetExposure(int(exposure)) 
		img = self.GetSingleFrame()
		if False:
			print("Image has shape and type %s %s"%(img.shape,img.dtype))
			print("Numpy object has shape %s, dtype %s, range %s - %s, median %s with standard deviation %s"%(img.shape,img.dtype,np.min(img),np.max(img),np.median(img),np.std(img)))
		if False:
			report = f"{light:-<10}{wheel:-<11}{exposure:->5}ms pixel values range {np.min(img):>5} - {np.max(img):5} with 98th percentile of {np.percentile(img,98):>5.0f} and {saturatedpct:>3.1f}% of pixels above {warnsaturation}, consider {suggestion:5.0f}"
		if True:
			suggestion = exposureGoal*int(exposure)/np.percentile(img,98)
			saturatedpct = 100 * np.count_nonzero(img > warnsaturation) / np.count_nonzero(img)
			report = f"{exposure:_>6}_|{suggestion:_>6.0f}_|{np.percentile(img,98):_>6.0f}_|{saturatedpct:_>5.1f}%_|{np.min(img):_>6}_|{np.max(img):_>6}_|{light:_^17}|{wheel:_^17}" 
			print(reportheader)
			print(report)
			self.reports.append(report)
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
			light,
			wheel,
			str(exposure)+'ms',
			timestamp+'.'+fileExtension])
		outfilePath = path.join(directory,outfileName)
		print("Saving %s"%(outfilePath))
		io.imsave(outfilePath,img,check_contrast=False)

"""
@brief CONTROL_ID enum define
List of function could be control
"""
class CONTROL_ID:
	CONTROL_BRIGHTNESS = ctypes.c_short(0) # image brightness
	CONTROL_CONTRAST = ctypes.c_short(1)   # image contrast
	CONTROL_WBR  = ctypes.c_short(2)       # red of white balance
	CONTROL_WBB = ctypes.c_short(3)        # blue of white balance
	CONTROL_WBG = ctypes.c_short(4)        # the green of white balance
	CONTROL_GAMMA = ctypes.c_short(5)      # screen gamma
	CONTROL_GAIN = ctypes.c_short(6)       # camera gain
	CONTROL_OFFSET = ctypes.c_short(7)     # camera offset
	CONTROL_EXPOSURE = ctypes.c_short(8)   # expose time (us)
	CONTROL_SPEED = ctypes.c_short(9)      # transfer speed
	CONTROL_TRANSFERBIT = ctypes.c_short(10)  # image depth bits
	CONTROL_CHANNELS = ctypes.c_short(11)     # image channels
	CONTROL_USBTRAFFIC = ctypes.c_short(12)   # hblank
	CONTROL_ROWNOISERE = ctypes.c_short(13)   # row denoise
	CONTROL_CURTEMP = ctypes.c_short(14)      # current cmos or ccd temprature
	CONTROL_CURPWM = ctypes.c_short(15)       # current cool pwm
	CONTROL_MANULPWM = ctypes.c_short(16)     # set the cool pwm
	CONTROL_CFWPORT = ctypes.c_short(17)      # control camera color filter wheel port
	CONTROL_COOLER = ctypes.c_short(18)       # check if camera has cooler
	CONTROL_ST4PORT = ctypes.c_short(19)      # check if camera has st4port
	CAM_COLOR = ctypes.c_short(20)
	CAM_BIN1X1MODE = ctypes.c_short(21)       # check if camera has bin1x1 mode
	CAM_BIN2X2MODE = ctypes.c_short(22)       # check if camera has bin2x2 mode
	CAM_BIN3X3MODE = ctypes.c_short(23)       # check if camera has bin3x3 mode
	CAM_BIN4X4MODE = ctypes.c_short(24)       # check if camera has bin4x4 mode
	CAM_MECHANICALSHUTTER = ctypes.c_short(25)# mechanical shutter
	CAM_TRIGER_INTERFACE = ctypes.c_short(26) # triger
	CAM_TECOVERPROTECT_INTERFACE = ctypes.c_short(27)  # tec overprotect
	CAM_SINGNALCLAMP_INTERFACE = ctypes.c_short(28)    # singnal clamp
	CAM_FINETONE_INTERFACE = ctypes.c_short(29)        # fine tone
	CAM_SHUTTERMOTORHEATING_INTERFACE = ctypes.c_short(30)  # shutter motor heating
	CAM_CALIBRATEFPN_INTERFACE = ctypes.c_short(31)         # calibrated frame
	CAM_CHIPTEMPERATURESENSOR_INTERFACE = ctypes.c_short(32)# chip temperaure sensor
	CAM_USBREADOUTSLOWEST_INTERFACE = ctypes.c_short(33)    # usb readout slowest
	CAM_8BITS = ctypes.c_short(34)                          # 8bit depth
	CAM_16BITS = ctypes.c_short(35)                         # 16bit depth
	CAM_GPS = ctypes.c_short(36)                            # check if camera has gps
	CAM_IGNOREOVERSCAN_INTERFACE = ctypes.c_short(37)       # ignore overscan area
	QHYCCD_3A_AUTOBALANCE = ctypes.c_short(38)
	QHYCCD_3A_AUTOEXPOSURE = ctypes.c_short(39)
	QHYCCD_3A_AUTOFOCUS = ctypes.c_short(40)
	CONTROL_AMPV = ctypes.c_short(41)                       # ccd or cmos ampv
	CONTROL_VCAM = ctypes.c_short(42)                       # Virtual Camera on off
	CAM_VIEW_MODE = ctypes.c_short(43)
	CONTROL_CFWSLOTSNUM = ctypes.c_short(44)                # check CFW slots number
	IS_EXPOSING_DONE = ctypes.c_short(45)
	ScreenStretchB = ctypes.c_short(46)
	ScreenStretchW = ctypes.c_short(47)
	CONTROL_DDR = ctypes.c_short(48)
	CAM_LIGHT_PERFORMANCE_MODE = ctypes.c_short(49)
	CAM_QHY5II_GUIDE_MODE = ctypes.c_short(50)
	DDR_BUFFER_CAPACITY = ctypes.c_short(51)
	DDR_BUFFER_READ_THRESHOLD = ctypes.c_short(52)
	DefaultGain = ctypes.c_short(53)
	DefaultOffset = ctypes.c_short(54)
	OutputDataActualBits = ctypes.c_short(55)
	OutputDataAlignment = ctypes.c_short(56)
	CAM_SINGLEFRAMEMODE = ctypes.c_short(57)
	CAM_LIVEVIDEOMODE = ctypes.c_short(58)
	CAM_IS_COLOR = ctypes.c_short(59)
	hasHardwareFrameCounter = ctypes.c_short(60)
	CONTROL_MAX_ID = ctypes.c_short(71)
	CAM_HUMIDITY = ctypes.c_short(72)                       #check if camera has humidity sensor 

class ERR:
	QHYCCD_READ_DIRECTLY = 0x2001
	QHYCCD_DELAY_200MS   = 0x2000
	QHYCCD_SUCCESS       = 0
	QHYCCD_ERROR         = 0xFFFFFFFF
