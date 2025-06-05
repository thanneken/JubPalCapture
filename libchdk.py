from math import log2
from libcanon import Canon
try:
	import chdkptp
except:
	print("It is necessary to install the chdkptp python module. See the source for more information.")
	exit()
"""
See https://github.com/a-hurst/chdkptp-python
apt install libusb-dev libreadline-dev
LUPA_WITH_LUA_DLOPEN=true pip install --no-binary lupa lupa
git clone https://github.com/a-hurst/chdkptp-python.git
vim device.py
	from chdkptp.lua import LuaContext, global_lua, parse_table, PTPError # Add PTPError
	DISTANCE_RE = re.compile('([0-9]+(?:.[0-9]+)?)(mm|cm|m|ft|in)') # replace \\d with [0-9] suppresses warning
pip install .
"""

class Chdk():
	def __init__(self):
		self.reports = []
		try:
			self.device = chdkptp.ChdkDevice(chdkptp.list_devices()[0])
		except:
			print("CHDK device not found")
			exit()
		try:
			assert self.device.is_connected
		except:
		 	print("Problem connecting to CHDK device, retrying")
		 	self.device.reconnect(wait=2000)
		try:
			assert self.device.is_connected
		except:
			print("Problem connecting to CHDK device, quitting after two attempts")
			exit()
		try:
			assert self.device.mode == 'record'
		except:
			print("Switching device mode from Play to Record")
			self.device.switch_mode('record')
	def session(self,config,target): 
		self.config = config
		self.target = target
	def showInfo(self):
		print("I don't think CHDK PTP supports getting info from the Device. The class DeviceInfo is for specifying the device to which ChdkDevice should connect.")
	def setWheel(self,wheelNewPosition): 
		print("CHDK does not support automated filter wheel, but could be interesting to work in a pause for manual changing of filters")
	def shoot(self,light,wheel,exposure):
		self.light = light
		self.wheel = wheel
		self.exposure = exposure
		"""
		Parameters:
		shutter_speed (int/float/None) – Shutter speed in APEX96 (default: None)
		real_iso (int/float/None) – Canon ‘real’ ISO (default: None)
		market_iso (int/float/None) – Canon ‘market’ ISO (default: None)
		aperture (int/float/None) – Aperture value in APEX96 (default: None)
		isomode (int/None) – Must conform to ISO value in Canon UI, shooting mode must have manual ISO (default: None)
		nd_filter (boolean/None) – Toggle Neutral Density filter (default: None)
		distance (str/unicode/int) – Subject distance. 
			If specified as an integer, the value is interpreted as the distance in milimeters. 
			You can also pass a string that contains a number followed by one of the following units: ‘mm’, ‘cm’, ‘m’, ‘ft’ or ‘in’ (default: None)
		dng (boolean) – Dump raw framebuffer in DNG format (default: False)
		wait (boolean) – Wait for capture to complete (default: True)
		download_after (boolean) – Download and return image data after capture (default: False)
		remove_after (boolean) – Remove image data after shooting (default: False)
		stream (boolean) – Stream and return image data directly from device (will not be saved on camera storage) (default: True)

		APEX = Additive System for Photographic Exposure
		https://petapixel.com/2024/11/18/how-the-defunct-apex-system-inspired-aperture-and-shutter-priority-modes/
		Tv = -log2(sec)
		Av = 2*log2(fstop)
		Sv = log2(iso/3.125)
		"""
		timevalueapex96 = -log2(exposure/1000) 
		if self.config['gain'].lower().startswith('iso'):
			iso = int(self.config['gain'].lower().strip('iso'))
			real_iso = log2(iso*8/25)
		elif int(self.config['gain']) >=100:
			iso = int(self.config['gain'])
			real_iso = log2(iso*8/25)
		else:
			real_iso= int(self.config['gain'])
		aperturevalueapex96 = 2*log2(int(self.config['aperture'].strip('F')))
		dng = self.device.shoot(dng=True,shutter_speed=timevalueapex96,real_iso=real_iso,aperture=aperturevalueapex96)
		Canon.saveRawFunction(self,dng) 
	def close(self):
		for report in self.reports:
			print(report)
		print("No separate step to close a CHDK device")
