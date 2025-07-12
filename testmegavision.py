#!/usr/bin/env python
import time

mcp2210serial = '0000134062' # how to get this if not from the Microchip Utility Software?
scanSerialPortDescriptions = True
scanMicrochip2210 = True
pause = 5 # seconds between attempts to send commands
spiCodeCandidates = [
	[64,0,0], # based on 2023, initialize
	[64,10,255], # based on 2023, logic high all
	[64,10,0], # based on 2023, logic low all
	[0,52,0], # based on n-shot table text file from Ivan
	[0,0,8], # based on another n-shot table, cyan
	[0,8,0], # based on another n-shot table, cyan
	[64,0,8], # first value is not always explicit in n-shot table text files
	[8], # maybe just one byte
	[52] # mind the commas
]

if scanSerialPortDescriptions:
	try:
		import serial
		import serial.tools.list_ports
	except:
		print("Please run pip install serial")
		exit()
	ports = serial.tools.list_ports.comports()
	print("These are the serial ports available")
	for port in ports:
		print(f"{port.name=} {port.description=}")
		if 'spectra' in port.description.lower(): # edit this line if a port description other than Spectra looks promising
			print("Found a port with Spectra in the description, attempting to connect")
			try:
				serialConnection = serial.Serial(port.device,115200)
				if not serialConnection.isOpen():
					serialConnection.open()
			except:
				print(f"Failed to open {port.description}")
				continue
			print("Connected to serial device named Spectra, trying to send some codes...")
			for spiCodeCandidate in spiCodeCandidates:
				print(f"Sending {spiCodeCandidate} as bytes")
				serialConnection.write(bytes(spiCodeCAndidate))
				print(f"Waiting {pause} seconds")
				time.sleep(pause)
			print(f"Closing {port.description}")
			serialConnection.close()

if scanMicrochip2210:
	try:
		from mcp2210 import Mcp2210, Mcp2210GpioDesignation
	except:
		print("To use the MCP2210 module it is necessary to run pip install mcp2210-python")
		exit()
	try:
		mcp = Mcp2210(serial_number=mcp2210serial) 
	except:
		print(f"Failed to open Microchip 2210 USB to SPI controller with {mcp2210serial=}.")
		print("Probably the best way to find the serial number is to use the Windows MCP2210 Utility.")
		print("Download from https://www.microchip.com/en-us/development-tool/adm00421")
		print("Edit the code to enter the new serial number")
		exit()
	for pin in range(9): # I believe GPIO 4 is standard or common for chip select
		print(f"{pin=}")
		mcp.set_gpio_designation(pin, Mcp2210GpioDesignation.CHIP_SELECT) 
		for spiCodeCandidate in spiCodeCandidates:
			print(f"{spiCodeCandidate=}")
			mcp.spi_exchange(bytes(spiCodeCandidate),cs_pin_number=pin)
			print(f"Waiting {pause} seconds")
			time.sleep(pause)

"""
Could also try the Windows MCP2210 Utility, download from https://www.microchip.com/en-us/development-tool/adm00421
"""
