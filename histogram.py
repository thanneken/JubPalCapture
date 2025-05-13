#!/usr/bin/env python
import matplotlib.pyplot as plt
import numpy as np
from skimage import io

verbose = False
warnblowout = True

def generate_histogram(inpath,outpath): 
    """
    currently  assumes file in, file out. Might be a case for numpy array in, return numpy array.
    could use BytesIO to save figure to RAM rather than filesystem and serve in html as base64:
        import io
        my_stringIObytes = io.BytesIO()
        plt.savefig(my_stringIObytes, format='jpg')
        my_stringIObytes.seek(0)
        my_base64_jpgData = base64.b64encode(my_stringIObytes.read()).decode()
    use of the FigureCanvasAgg backend allows drawing the figure to an rgba buffer:
        https://matplotlib.org/stable/gallery/user_interfaces/canvasagg.html
        instead of pil use np.assarray(buffer)
    """
    if verbose:
        print("Reading %s"%(inpath))
    img = io.imread(inpath)
    img = np.reshape(img,-1)
    if verbose:
        print("Image has %s pixels ranging from %s to %s with a median of %s and standard deviation of %s"%(img.shape[0],np.min(img),np.max(img),int(np.median(img)),int(np.std(img))))
    if 'LensCap-QHYmini' in inpath:
        range = (0,2**12-1)
    elif 'LensCap-' in inpath:
        range = (0,2**10-1)
    elif img.dtype == 'uint16' and warnblowout:
        range = (0,2**16-1)
        percent = 100 * np.count_nonzero(img > 0.95*range[1]) / img.shape[0]
        if percent > 0.5:
            print("%s%% of pixels are greater than 95%% of range in %s"%(int(percent),inpath))
    else:
        range = None
    plt.clf()
    plt.hist(img,bins=256,range=range)
    plt.tick_params(axis='y',labelleft=False)
    plt.margins(x=0)
    plt.savefig(outpath)

if __name__ == "__main__":
    import sys
    import os
    if len(sys.argv) == 1:
        print("This command takes a filename or glob of filenames as a command line argument")
        exit()
    imglist = []
    for argument in sys.argv[1:]:
        if os.path.isdir(argument):
            print("%s is a directory. For now we're expecting image files. Adding /*.tif might do the trick."%(argument))
        elif os.path.isfile(argument) and argument.lower().endswith('.tif'): # might be nice to catch tiff or other formats
            imglist.append(argument)
    for imgfile in imglist:
        basedir, filename = os.path.split(imgfile)
        histogramdir = os.path.join(basedir,'Histograms')
        histfilepath = os.path.join(histogramdir,filename[:-3]+'png') # assumes file extension is three characters
        if os.path.exists(histfilepath):
            print("Not replacing %s"%(histfilepath))
            continue
        if not os.path.exists(histogramdir):
            print("Creating directory %s"%(histogramdir))
            os.mkdir(histogramdir)
        generate_histogram(imgfile,histfilepath)
