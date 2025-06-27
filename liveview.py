#!usr/bin/env python
from flask import Flask, render_template, request, Response, redirect, url_for
import time
import cv2
from threading import Thread
import numpy as np

variation = 'megavision'
variation = 'qhy'

global height,width,scale,roiY,roiH,roiX,roiW,camera,gracefulStop,exposure,roiYPct,roiXPct,filterwheel
camera = False
gracefulStop = False
scale = float(1)
roiYPct = float(0.5)
roiXPct = float(0.5)
if variation == 'megavision':
	filterwheel = 'Position1'
else:
	filterwheel = 'NoFilter'

def initializeWebcam():
	global camera,width,height,roiX,roiY,roiH,roiW,binXY
	height = roiH = 1080
	width = roiW = 1920
	roiX = roiY = 0
	binXY = 1
	if not camera or not camera.isOpened():
		camera = cv2.VideoCapture(0)
		ret = camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
		ret = camera.set(cv2.CAP_PROP_FRAME_HEIGHT,height)
		ret = camera.set(cv2.CAP_PROP_FRAME_WIDTH,width)

def initializeQhy(): 
	global camera,exposure,binXY,roiX,roiY,width,height,roiW,roiH,cameraName,filterwheel
	if not camera:
		exposure = 16 # exposure = 1
		import libqhy 
		camera = libqhy.Qhyccd()
		camera.connect(1) # 1 is stream, 0 is single frame
		cameraName = bytes(camera.id).decode()
		if cameraName.startswith('QHYminiCam'):
			print("Applying settings for QHY miniCam8")
			height = 2180 
			width = 3856
			binXY = 2 
			camera.SetReadMode(0) # mini read mode 1 is LinearityHDR
			camera.SetGain(26)  # factory was 30, 78 on demo and appears to be optimal point on graphs
			roiX = 0
			roiY = 0
		elif cameraName.startswith('QHY411'):
			print("Applying settings for QHY411")
			height = 10656
			width = 14208
			camera.SetReadMode(0) 
			camera.SetGain(0)
			binXY = 4
			roiX = 0
			roiY = 0
		else:
			print("Applying settings for QHY 600")
			camera.SetGain(26)
			height = 6388 # could get this from camera after set bin mode
			width = 9576
			binXY = 4
			roiX = 24
			roiY = 0
		camera.setWheel(filterwheel) 
		roiX = int(roiX/binXY)
		roiY = int(roiY/binXY)
		roiW = int(width/binXY)
		roiH = int(height/binXY)
		camera.SetBit(8)
		camera.SetBinMode(binXY,binXY) 
		camera.SetROI(roiX,roiY,roiW,roiH)
		camera.SetExposure(int(exposure/(binXY**2)))

def initializePixelink():
	global camera,exposure,binXY,roiX,roiY,width,height,roiW,roiH,cameraName,filterwheel
	if not camera:
		exposure = 16 # library automatically converts ms to s for the camera
		import libpixelink 
		camera = libpixelink.Pixelink()
		config = {'gain':11.1,'bpp':8}
		camera.session(config,'liveview')
		camera.showInfo()
		if camera.name.lower().startswith('pixelink'):
			print("Applying settings for Pixelink")
		cameraName = camera.name
		height = 3648
		width = 5472
		binXY = 2 
		roiX = 0
		roiY = 0
		roiX = int(roiX/binXY)
		roiY = int(roiY/binXY)
		roiW = int(width/binXY)
		roiH = int(height/binXY)
		camera.SetBinMode(binXY,binXY) 
		camera.SetROI(roiX,roiY,roiW,roiH)
		camera.SetExposure(int(exposure/(binXY**2)))

def initializeFlir():
	global camera,exposure,binXY,roiX,roiY,width,height,roiW,roiH,cameraName,filterwheel
	if not camera:
		exposure = 16 
		import libflir
		camera = libflir.Flir()
		config = {'gain':11.1,'bpp':8}
		camera.session(config,'liveview')
		cameraName = 'Flir'
		height = 3648
		width = 5472
		binXY = 2 
		roiX = 0
		roiY = 0
		roiX = int(roiX/binXY)
		roiY = int(roiY/binXY)
		roiW = int(width/binXY)
		roiH = int(height/binXY)
		camera.SetBinMode(binXY,binXY) 
		camera.SetROI(roiX,roiY,roiW,roiH)
		camera.SetExposure(int(exposure/(binXY**2)))

def closeWebcam():
	global camera,gracefulStop
	if camera and camera.isOpened():
		print("Closing camera")
		camera.release()
		cv2.destroyAllWindows()
		gracefulStop = False
		camera = False

def closeQhy():
	global camera,gracefulStop
	if camera:
		print("Closing camera")
		camera.StopLive()
		camera.close()
		camera = False
		gracefulStop = False
		print("Camera now closed")

def closePixelink():
	global camera,gracefulStop
	if camera:
		print("Closing Pixelink Camera")
		camera.close()
		camera = False
		gracefulStop = False
		print("Camera now closed")

def closeFlir():
	global camera,gracefulStop
	if camera:
		print("Closing Flir Camera")
		camera.close()
		camera = False
		gracefulStop = False
		print("Camera now closed")

def framesWebcam():
	global camera,roiY,roiH,roiX,roiW,scale,gracefulStop
	while not gracefulStop:
		success, frame = camera.read() 
		if success:
			frame = frame[roiY:roiY+roiH,roiX:roiX+roiW]
			frame = cv2.resize(frame,(int(roiW*scale),int(roiH*scale)))
			try:
				ret, buffer = cv2.imencode('.jpg',frame) 
				frame = buffer.tobytes()
				yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
			except Exception as e:
				pass
		else:
			initializeWebcam()
			pass
	thread = Thread(target = closeWebcam, args=[]) 
	thread.start()

def framesQhy():
	global camera,roiW,roiH,scale,binXY,cameraName
	camera.BeginLive()
	while not gracefulStop:
		frame = camera.GetLiveFrame()
		if binXY > 1:
			frameH,frameW = frame.shape
			frame = cv2.resize(frame,(int(frameW*scale),int(frameH*scale)))
		try:
			ret, buffer = cv2.imencode('.jpg',frame) 
			frame = buffer.tobytes()
			yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
		except Exception as e:
			print("Failed to yield jpeg frame")# pass

def framesPixelink():
	global camera,roiW,roiH,scale,binXY,cameraName
	while not gracefulStop:
		frame = camera.GetLiveFrame()
		if binXY > 1:
			frameH,frameW = frame.shape
			frame = cv2.resize(frame,(int(frameW*scale),int(frameH*scale)))
		try:
			ret, buffer = cv2.imencode('.jpg',frame) 
			frame = buffer.tobytes()
			yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
		except Exception as e:
			print("Failed to yield jpeg frame")# pass

def framesFlir():
	global camera,roiW,roiH,scale,binXY,cameraName
	while not gracefulStop:
		frame = camera.GetLiveFrame()
		if binXY > 1:
			frameH,frameW = frame.shape
			frame = cv2.resize(frame,(int(frameW*scale),int(frameH*scale)))
		try:
			ret, buffer = cv2.imencode('.jpg',frame) 
			frame = buffer.tobytes()
			yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
		except Exception as e:
			print("Failed to yield jpeg frame")# pass

app = Flask(__name__)

@app.route('/')
def index():
	return render_template('index.html')

@app.route('/webcam/live',methods=['POST','GET'])
def webcamlive():
	system='webcam'
	global scale,roiYPct,roiXPct,roiY,roiH,roiX,roiW,gracefulStop
	if request.method == 'POST':
		if request.form.get('Stop') == 'Stop':
			gracefulStop = True	
			return redirect(url_for('index'))
		else:
			scale = float(request.form.get('scale'))
			roiW = int(scale*width)
			roiH = int(scale*height)
			roiYPct = float(request.form.get('roiYPct'))
			roiXPct = float(request.form.get('roiXPct'))
			roiY = int((height - roiH) * roiYPct)
			roiX = int((width - roiW) * roiXPct)
	elif request.method == 'GET':
		pass
	return render_template('liveview.html',scale=scale,roiYPct=roiYPct,roiXPct=roiXPct,system=system)

@app.route('/qhy/live',methods=['POST','GET'])
def qhylive():
	system='qhy'
	scope = 'full'
	global scale,roiYPct,roiXPct,roiY,roiH,roiX,roiW,gracefulStop,camera,width,height,exposure,binXY,cameraName,filterwheel
	if request.method == 'POST':
		scope = request.form.get('scope')
		if request.form.get('Stop') == 'Stop':
			gracefulStop = True	
			thread = Thread(target = closeQhy, args=[]) 
			thread.start()
			return redirect(url_for('index'))
		elif scope == 'full':
			if not camera:
				initializeQhy()
			if cameraName.startswith('QHYminiCam'):
				binXY = 2
			else:
				binXY = 4
			camera.SetBinMode(binXY,binXY) 
			roiX = 0
			roiY = 0
			roiW = int(width/binXY)
			roiH = int(height/binXY)
			camera.SetROI(roiX,roiY,roiW,roiH)
			exposure = int(request.form.get('exposure'))
			print("Setting exposure to %s"%(int(exposure/(binXY**2))))
			camera.SetExposure(int(exposure/(binXY**2)))
			if request.form.get('filterwheel') != filterwheel:
				filterwheel = request.form.get('filterwheel')
				camera.setWheel(filterwheel) 
			scale = float(request.form.get('scale'))
		elif scope == 'detail':
			if not camera:
				initializeQhy()
			binXY = 1
			camera.SetBinMode(binXY,binXY) 
			scale = float(request.form.get('scale'))
			roiW = int(scale*width/4)
			roiH = int(scale*height/4)
			roiXPct = float(request.form.get('roiXPct'))
			roiYPct = float(request.form.get('roiYPct'))
			roiX = int((width - roiW) * roiXPct)
			roiY = int((height - roiH) * roiYPct)
			camera.SetROI(roiX,roiY,roiW,roiH)
			exposure = int(request.form.get('exposure'))
			print("Setting exposure to %s"%(int(exposure/(binXY**2))))
			camera.SetExposure(int(exposure/(binXY**2)))
			if request.form.get('filterwheel') != filterwheel:
				filterwheel = request.form.get('filterwheel')
				camera.setWheel(filterwheel) 
		else: 
			print("UNANTICIPATED SITUATION")
			closeQhy()
			exit()
	elif request.method == 'GET':
		exposure = 32
	return render_template('liveview.html',scale=scale,system=system,exposure=exposure,roiYPct=roiYPct,roiXPct=roiXPct,scope=scope,filterwheel=filterwheel) 

@app.route('/pixelink/live',methods=['POST','GET'])
def pixelinklive():
	system='pixelink'
	scope = 'full'
	global scale,roiYPct,roiXPct,roiY,roiH,roiX,roiW,gracefulStop,camera,width,height,exposure,binXY,cameraName,filterwheel
	if request.method == 'POST':
		scope = request.form.get('scope')
		if request.form.get('Stop') == 'Stop':
			gracefulStop = True	
			thread = Thread(target = closePixelink, args=[]) 
			thread.start()
			return redirect(url_for('index'))
		elif scope == 'full':
			if not camera:
				initializePixelink()
			binXY = 2
			camera.SetBinMode(binXY,binXY) 
			roiX = 0
			roiY = 0
			roiW = int(width/binXY)
			roiH = int(height/binXY)
			camera.SetROI(roiX,roiY,roiW,roiH)
			exposure = int(request.form.get('exposure'))
			print("Setting exposure to %s"%(int(exposure/(binXY**2))))
			camera.SetExposure(int(exposure/(binXY**2)))
			if request.form.get('filterwheel') != filterwheel:
				filterwheel = request.form.get('filterwheel')
				camera.setWheel(filterwheel) 
			scale = float(request.form.get('scale'))
		elif scope == 'detail':
			if not camera:
				initializePixelink()
			binXY = 1
			camera.SetBinMode(binXY,binXY) 
			scale = float(request.form.get('scale'))
			roiW = int(scale*width/4)
			roiH = int(scale*height/4)
			roiXPct = float(request.form.get('roiXPct'))
			roiYPct = float(request.form.get('roiYPct'))
			roiX = int((width - roiW) * roiXPct)
			roiY = int((height - roiH) * roiYPct)
			camera.SetROI(roiX,roiY,roiW,roiH)
			exposure = int(request.form.get('exposure'))
			print("Setting exposure to %s"%(int(exposure/(binXY**2))))
			camera.SetExposure(int(exposure/(binXY**2)))
			if request.form.get('filterwheel') != filterwheel:
				filterwheel = request.form.get('filterwheel')
				camera.setWheel(filterwheel) 
		else: 
			print("UNANTICIPATED SITUATION")
			closePixelink()
			exit()
	elif request.method == 'GET':
		exposure = 32 # may be different for pixelink
	return render_template('liveview.html',scale=scale,system=system,exposure=exposure,roiYPct=roiYPct,roiXPct=roiXPct,scope=scope,filterwheel=filterwheel) 

@app.route('/flir/live',methods=['POST','GET'])
def flirlive():
	system='flir'
	scope = 'full'
	global scale,roiYPct,roiXPct,roiY,roiH,roiX,roiW,gracefulStop,camera,width,height,exposure,binXY,cameraName,filterwheel
	if request.method == 'POST':
		scope = request.form.get('scope')
		if request.form.get('Stop') == 'Stop':
			gracefulStop = True	
			thread = Thread(target = closeFlir, args=[]) 
			thread.start()
			return redirect(url_for('index'))
		elif scope == 'full':
			if not camera:
				initializeFlir()
			binXY = 2
			camera.SetBinMode(binXY,binXY) 
			roiX = 0
			roiY = 0
			roiW = int(width/binXY)
			roiH = int(height/binXY)
			camera.SetROI(roiX,roiY,roiW,roiH)
			exposure = int(request.form.get('exposure'))
			print("Setting exposure to %s"%(int(exposure/(binXY**2))))
			camera.SetExposure(int(exposure/(binXY**2)))
			if request.form.get('filterwheel') != filterwheel:
				filterwheel = request.form.get('filterwheel')
				camera.setWheel(filterwheel) 
			scale = float(request.form.get('scale'))
		elif scope == 'detail':
			if not camera:
				initializeFlir()
			binXY = 1
			camera.SetBinMode(binXY,binXY) 
			scale = float(request.form.get('scale'))
			roiW = int(scale*width/4)
			roiH = int(scale*height/4)
			roiXPct = float(request.form.get('roiXPct'))
			roiYPct = float(request.form.get('roiYPct'))
			roiX = int((width - roiW) * roiXPct)
			roiY = int((height - roiH) * roiYPct)
			camera.SetROI(roiX,roiY,roiW,roiH)
			exposure = int(request.form.get('exposure'))
			print("Setting exposure to %s"%(int(exposure/(binXY**2))))
			camera.SetExposure(int(exposure/(binXY**2)))
			if request.form.get('filterwheel') != filterwheel:
				filterwheel = request.form.get('filterwheel')
				camera.setWheel(filterwheel) 
		else: 
			print("UNANTICIPATED SITUATION")
			closeFlir()
			exit()
	elif request.method == 'GET':
		exposure = 32 # may be different for flir
	return render_template('liveview.html',scale=scale,system=system,exposure=exposure,roiYPct=roiYPct,roiXPct=roiXPct,scope=scope,filterwheel=filterwheel) 

@app.route('/webcam/feed')
def feedWebcam():
	initializeWebcam()
	return Response(framesWebcam(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/qhy/feed')
def feedQhy():
	initializeQhy()
	return Response(framesQhy(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/pixelink/feed')
def feedPixelink():
	initializePixelink()
	return Response(framesPixelink(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/flir/feed')
def feedFlir():
	initializeFlir()
	return Response(framesFlir(), mimetype='multipart/x-mixed-replace; boundary=frame')

# flask --app liveview run --debug --host 192.168.23.166
# python -m flask --app liveview run --host 192.168.1.120
