import time

verbose = 3

class Octopus: # Arduino is the default Octopus, specify 2023 or Bluetooth for variants
	def __init__(self):
		import serial
		import serial.tools.list_ports
		self.port0 = (0,9)
		self.test = (0,9) # format is port, octopus index where 9 is all octopodes
		self.testRight = (0,0)
		self.testLeft = (0,1)
		self.port1 = (1,9)
		self.white6500 = (1,9)
		self.white6500Right = (1,1)
		self.white6500Left = (1,0)
		self.port2 = (2,9)
		self.white2800 = (2,9)
		self.white2800Right = (2,1)
		self.white2800Left = (2,0)
		self.port3 = (3,9)
		self.uv385 = (3,9)
		self.port4 = (4,9)
		self.uv405 = (4,9)
		self.port5 = (5,9)
		self.blue475 = (5,9)
		self.blue475Right = (5,1)
		self.blue475Left = (5,0)
		self.port6 = (6,9)
		self.ir730 = (6,9)
		self.port7 = (7,9)
		self.ir850 = (7,9)
		self.port8 = (8,9)
		self.ir940 = (8,9)
		self.raking = (8,9)
		self.rakingRight = (8,1)
		self.rakingLeft = (8,0)
		self.octopodes = []
		ports = serial.tools.list_ports.comports()
		for port in ports:
			if "USB to UART Bridge Controller" in port.description:
				octopus = serial.Serial(port.device,115200)
				if not octopus.isOpen():
					octopus.open()
				self.octopodes.append(octopus) # octopus comparable to self.led_connection
				print("Connected to %s %s"%(port.name,port.description))
	def on(self,light,exposure):
		port = getattr(self,light)
		try:
			for num, octopus in enumerate(self.octopodes): 
				if port[1] > 8 or port[1] == num:
					print("Asking Octopus index %s to turn on port %s for light %s for %s milliseconds"%(num,port[0],light,exposure))
					octopus.write((port[0]+48).to_bytes(1)) # octopus interprets integer 0-8 as turn on that port; add 48 because
		except:
			print("Failure trying to write command %s-%s"%(port[0],port[1]))
		time.sleep(int(exposure)/1000)
		if True:
			time.sleep(2) 
		try:
			for octopus in self.octopodes: 
				octopus.write(int(58).to_bytes(1)) # octopus interprets a number greater than known ports (1 internal, 8 ports) as all off; add 48
		except:
			print("Failure trying to write command 10 for all off")
	def close(self):
		for octopus in self.octopodes:
			print("Closing",octopus.name)
			octopus.close()
	def manualon(self,light):
		port = getattr(self,light)
		try:
			for num, octopus in enumerate(self.octopodes): 
				if port[1] > 8 or port[1] == num:
					print("Asking Octopus index %s to turn on port %s for light %s indefinately"%(num,port[0],light)) if verbose > 3 else None
					octopus.write((port[0]+48).to_bytes(1)) # octopus interprets integer 0-8 as turn on that port; add 48 because
					print(f"Light {light} is on. It will not turn off unless you use the function off() to turn off all lights") if verbose > 3 else None
		except:
			print("Failure trying to write command %s-%s"%(port[0],port[1]))
	def off(self):
		try:
			for octopus in self.octopodes: 
				octopus.write(int(58).to_bytes(1)) # octopus interprets a number greater than known ports (1 internal, 8 ports) as all off; add 48
				print("Successfully issued command to turn off all lights") if verbose > 3 else None
		except:
			print("Failure trying to write command 10 for all off")

class Misha:
	def __init__(self):
		import serial
		import serial.tools.list_ports
		ports = serial.tools.list_ports.comports()
		for port in ports:
			if "seeeduino Nano" in port.description:
				port_number = port.device
				break
			elif "Silicon Labs CP210x USB to UART Bridge" in port.description:
				port_number = port.device
				break
		self.led_connection = serial.Serial(port_number, 9600)
		if not self.led_connection.isOpen():
				self.led_connection.open()
	def on(self,light,exposure):
		if light not in ['365','385','395','420','450','470','500','530','560','590','615','630','660','730','850','940']:
			print("I don't think Misha light panels will understand your request for light %s, but we can try…"%(light))
		print("Turning on light %s for %s"%(light,exposure))
		exposure = int(exposure.strip('ms'))
		self.led_connection.write((light + ',100\n').encode()) # wavelength,intensity(on a scale of 100)\n
		time.sleep(exposure/1000)
		self.led_connection.write('0,0\n'.encode())
	def manualon(self,light):
		if light not in ['365','385','395','420','450','470','500','530','560','590','615','630','660','730','850','940']:
			print("I don't think Misha light panels will understand your request for light %s, but we can try…"%(light))
		print("Turning on light %s"%(light))
		self.led_connection.write((light + ',100\n').encode()) # wavelength,intensity(on a scale of 100)\n
	def off(self):
		self.led_connection.write('0,0\n'.encode())
	def close(self):
		self.led_connection.close()

class Overhead:
	def __init__(self):
		print("No lights to initialize...")
	def on(self,light,exposure):
		if isinstance(exposure,str):
			exposure = int(exposure.strip('ms'))
		if light == "NoLight":
			time.sleep(exposure/1000)
	def manualon(self,light):
		pass
	def off(self):
		pass
	def close(self):
		print("No need to close the overhead lights")

class Octopus2023:
	class Ports:
		Raking1 = 0x01
		Raking2 = 0x02
		Raking3 = 0x04
		Raking5 = 0x10
	def __init__(self):
		print("Initializing lights")
		from mcp2210 import Mcp2210, Mcp2210GpioDesignation
		mcp2210serial = '0000134062' 
		mcp = Mcp2210(serial_number=mcp2210serial) 
		mcp.set_gpio_designation(4, Mcp2210GpioDesignation.CHIP_SELECT) # initialize communication
		mcp.spi_exchange([0x40,0x00,0x00], cs_pin_number=4) # initialize communication
		mcp.spi_exchange([0x40,0x0A,0xFF], cs_pin_number=4) # all lights off (voltage high to current controllers)
	def on(self,light,exposure):
		if light == "NoLight":
			time.sleep(exposure/1000)
		else:
			print("Turning on light %s for %s"%(light,exposure))
			light = getattr(Ports,light)
			exposure = int(exposure.strip('ms'))
			mcp.spi_exchange([0x40,0x0A,0xFF-light],cs_pin_number=4)
			time.sleep(exposure/1000)
			mcp.spi_exchange([0x40,0x0A,0xFF],cs_pin_number=4)
	def close(self):
		pass

class OctopusBluetooth:
	def __init__(self):
		import simplepyble
		self.port0 = (0,9)
		self.test = (0,9) # format is port, octopus index where 9 is all octopodes
		self.testLeft = (0,0)
		self.testRight = (0,1)
		self.port1 = (1,9)
		self.white6500 = (1,9)
		self.white6500Left = (1,0)
		self.white6500Right = (1,1)
		self.port2 = (2,9)
		self.white2800 = (2,9)
		self.white2800Left = (2,0)
		self.white2800Right = (2,1)
		self.port3 = (3,9)
		self.uv385 = (3,9)
		self.port4 = (4,9)
		self.uv405 = (4,9)
		self.port5 = (5,9)
		self.blue475 = (5,9)
		self.port6 = (6,9)
		self.ir850 = (6,9)
		self.port7 = (7,9)
		self.ir940 = (7,9)
		self.port8 = (8,9)
		self.raking = (8,9)
		scantime = int(5)
		self.serviceuuid = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E".lower()
		adapters = simplepyble.Adapter.get_adapters()
		if len(adapters) == 0:
			print("No bluetooth adapters found on this machine")
		elif len(adapters) == 1:
			adapter = adapters[0]
		else:
			for adapter in adapters:
				print(f"Adapter: {adapter.identifier()} [{adapter.address()}]")
			print("Please select a local bluetooth adapter:") 
			for i, adapter in enumerate(adapters):
				print(f"{i}: {adapter.identifier()} [{adapter.address()}]")
			choice = int(input("Enter choice: "))
			adapter = adapters[choice]
		print(f"Selected local bluetooth adapter: {adapter.identifier()} [{adapter.address()}]")
		adapter.set_callback_on_scan_start(lambda: print("Scan started."))
		adapter.set_callback_on_scan_stop(lambda: print("Scan complete."))
		adapter.set_callback_on_scan_found(lambda peripheral: print(f"Found {peripheral.identifier()} [{peripheral.address()}]"))
		adapter.scan_for(scantime*1000)
		results = adapter.scan_get_results()
		self.octopodes = []
		for result in results:
			services = result.services()
			for service in services:
				if service.uuid() == self.serviceuuid:
					self.octopodes.append(result) 
		try:
			for octopus in self.octopodes:
				print(f"Connecting to: {octopus.identifier()} [{octopus.address()}]")
				octopus.connect()
		except:
			print("Not able to find and connect to a peripheral offering service %s"%(self.serviceuuid))
	def on(self,light,exposure):
		characteristicRx = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E".lower()
		port = getattr(self,light)
		try:
			for num, octopus in enumerate(self.octopodes): 
				if port[1] > 8 or port[1] == num:
					print("Asking Octopus index %s at %s to turn on port %s for light %s for %s milliseconds"%(num,octopus.address(),port[0],light,exposure))
					octopus.write_request(self.serviceuuid,characteristicRx,port[0].to_bytes(1)) # octopus interprets integer 0-8 as turn on that port
		except:
			print("Failure trying to write command %s-%s to %s"%(port[0],port[1],characteristicRx))
		time.sleep(exposure/1000)
		try:
			for octopus in self.octopodes: 
				octopus.write_request(self.serviceuuid,characteristicRx,int(10).to_bytes(1)) # octopus interprets a number greater than known ports (1 internal, 8 ports) as all off
		except:
			print("Failure trying to write command 10 %s"%(characteristicRx))
	def close(self):
		try:
			for octopus in self.octopodes:
				print("Closing %s"%(octopus.address()))
				octopus.disconnect()
				print("Closed")
		except:
			print("Error trying to close bluetooth connection")

