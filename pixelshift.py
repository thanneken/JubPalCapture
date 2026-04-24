#!/usr/bin/env python
import numpy as np

def debayer(capturestack): # Takes a stack of four captures using pixel shift
	bggr = np.zeros(capturestack.shape)
	bggr[:, 0::2, 0::2] = capturestack[[1, 0, 2, 3], 0::2, 0::2] # y even, x even
	bggr[:, 0::2, 1::2] = capturestack[[2, 3, 1, 0], 0::2, 1::2] # y even, x odd
	bggr[:, 1::2, 0::2] = capturestack[[0, 1, 3, 2], 1::2, 0::2] # y odd, x even
	bggr[:, 1::2, 1::2] = capturestack[[3, 2, 0, 1], 1::2, 1::2] # y odd, x odd
	bgr = [bggr[0], (bggr[1] + bggr[2]) / 2.0, bggr[3]]
	return bgr

if __name__ == "__main__":
	import time
	shot1 = [ [0.4,0.7,0.4,0.7] , [0.3,0.6,0.3,0.6] , [0.4,0.7,0.4,0.7] , [0.3,0.6,0.3,0.6] ]
	shot2 = [ [0.3,0.6,0.3,0.6] , [0.4,0.7,0.4,0.7] , [0.3,0.6,0.3,0.6] , [0.4,0.7,0.4,0.7] ]
	shot3 = [ [0.6,0.3,0.6,0.3] , [0.7,0.4,0.7,0.4] , [0.6,0.3,0.6,0.3] , [0.7,0.4,0.7,0.4] ]
	shot4 = [ [0.7,0.4,0.7,0.4] , [0.6,0.3,0.6,0.3] , [0.7,0.4,0.7,0.4] , [0.6,0.3,0.6,0.3] ]
	capturestack = np.stack([shot1,shot2,shot3,shot4]) # simulates a solid color target with B,G1,G2,R = 0.3,0.4,0.6,0.7
	capturestack = np.stack(capturestack)
	start = time.time()
	_ = debayer(capturestack)
	debayertime = time.time() - start
	print(f"Processing small known stack took {debayertime:.6f} seconds")
	print(debayer(capturestack))
	capturestack = np.random.rand(4, 6336, 9504) # four captures of 61 megapixels
	start = time.time()
	_ = debayer(capturestack)
	debayertime = time.time() - start
	print(f"Processing large random stack took {debayertime:.6f} seconds")
	capturestack = np.zeros((4,6336,9504))
	start = time.time()
	_ = debayer(capturestack)
	debayertime = time.time() - start
	print(f"Processing large stack of zeros took {debayertime:.6f} seconds")

