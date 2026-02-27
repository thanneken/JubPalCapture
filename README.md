# JubPalCapture
Python tools for capturing multispectral image data from cultural heritage artifacts

JubPalCapture is intended to run on a [Multispectral Imaging Networked Capture Controller](https://palimpsest.stmarytx.edu/thanneken/2025/controller.html).
Linux (ARM or Intel architecture) is generally presumed, but adapting to other platforms should be possible.

The controller has been tested on a wide variety of cameras (QHY, Canon, CHDK, Flir) and lights (Octopus, Misha).
Compatibility with MegaVision lights, filter wheel, and shutter is under development.
The capture suite makes a lot of assumptions about workflow and particularly about file paths and names.
Sample data following the presumed workflow can be examined from the data archive of the [Jubilees Palimpsest Project](https://palimpsest.stmarytx.edu/rodeo/2025/data/).

## Capture

### `capture.py`

```
.~/git/JubPalCapture$ /capture.py -h
Gathering arguments from the command line
usage: capture.py [-h] [-c CONFIGURATION] [-s SHOTLIST] [-t TARGET] [-v] [-w]

options:
  -h, --help            show this help message and exit
  -c CONFIGURATION, --configuration CONFIGURATION
  -s SHOTLIST, --shotlist SHOTLIST
  -t TARGET, --target TARGET
  -v, --verbose
  -w, --worklights
```

For example, to use a Canon camera to take a single shot of the first page of a manuscript, you might use:

`capture.py -c profiles/canon.yaml -s shotlists/single.txt -t "Manuscript_001r"`

The `-w` argument turns on white work lights (if available) and leaves them on until the next sequence begins.

The `-v` argument increases verbosity of information provided to the console.

### `profiles`

Configuration profiles are necessarily in `.yaml` format.
One of several examples provided is `600.yaml`:

```yaml
sensor: QHY600
lens: Milvus50
lights: Octopus
aperture: F11
cool: -10
gain: 26
basepath: ~/Pictures
```

Note that some of the fields are prescriptive and others are descriptive, depending on the equipment.
Prescriptive data will set the camera to the designated cooling (if available), gain, and aperture if controlled by the camera.
Descriptive data will be used to generate meaningful filenames that record the sensor, lens, and lights.

### `shotlists`

Shotlist files are necessarily in `.txt` format.
Each line consists of three hyphen-separated fields indicating the light, filter, and exposure time in milliseconds.
Lines can also be skipped by prefacing a `#`.
One of several examples provided is `single.txt`:

```txt
# NoLight-NoFilter-5ms
# NoLight-WrattenBlue98-40ms
# NoLight-WrattenGreen61-60ms
# NoLight-WrattenRed25-30ms
# NoLight-WrattenInfrared87-70ms
NoLight-BayerRGGB-50ms
```

It is advised to use `BayerRGGB` for cameras with Bayer arrays and `NoFilter` when there is no Bayer array.

### `liveview.py`

For Canon cameras, use the camera itself for framing and focus.
For QHY and Flir cameras, `liveview.py` and a web browser will show a live view of image data from the camera.
Live view requires Flask. 
Depending on your Flask configuration, you might start it with something like:

```bash
flask --app liveview run --host "192.168.1.120"
```

or

```bash
python -m flask --app liveview run --host "192.168.1.120"
```

If the web browser is on the same device as the controller the host can be omitted or set to localhost.

### `lights.py`

Generally lights are controlled through `capture.py`.
However, it is also possible to control the lights manually.

```python
from lights import Octopus
lights = Octopus()
lights.manualon('white6500')
lights.off()
lights.close()
```

## Processing

### `darksubtract.py`

Dark subtraction accounts for any consistent variation or noise in the sensor when there is no light signal.
For consistency, we take 3-5 captures in a dark room with the lens cap on.
Dark sets should be taken for all or many exposure times.
If possible, temperature should be consistent as well.
To capture dark sets, use `capture.py` with target `LensCap` and light `NoLight`.

The `darksubtract.py` command takes an argument for `.tif` files in a `Raw` directory and creates dark subtracted files in a sibling directory called `DarkSubtracted`.
For example:

```bash
./darksubtract.py ~/Pictures/Manuscript_001r/Raw/*.tif
```

For each `.tif` file specified on the command line, `darksubtract.py` will look for files with the same essential features in the filename in `~/Pictures/LensCap/Raw/`.
The median of those files will be calculated and stored in `~/Pictures/LensCap/Median/` to save time on subsequent runs.
The median dark signal will be subtracted from the Raw file specified on the command line and stored in the directory `~/Pictures/Manuscript_001r/DarkSubtracted/`.

### `flatten.py`

Flattening attempts to correct for any unevenness in the lighting or system noise not already accounted for with dark subtraction.
The basic technique is to image a flat (not shiny) piece of white paper. 
We then assume that any degree to which the resulting image is not all the same is bad.
We divide images of real targets (such as manuscripts) by the image of the white paper.
This is very helpful on a high-quality system, but can introduce additional noise under certain circumstances.
When a system produces noisy images, operations using more noisy images results in noisier output.
For lights with a high degree of inconsistency, flattening can backfire if the target is any more or less shiny than the white paper.
This is true when the lights are close to the object, far apart from each other, and not diffused or collimated in any way, 

Before running `flatten.py`, it is necessary to use bash to create a file listing the paths to images of white paper under the same conditions.
The images of the white paper and the target (e.g., manuscript) should already be dark subtracted.

```bash
cd ~/Pictures/Manuscript_001r/
ls ../WhitePaper/DarkSubtracted/*.tif > flats.txt
cd -
./flatten.py ~/Pictures/Manuscript_001r/flats.txt
```

This will create flattened images of every image in the directory `DarkSubtracted` in a new directory called `Flattened`.




### Additional processing

For more advanced processing, such as calibrated color and linear transformations (PCA, ICA, MNF), see [JubPalProcess](https://github.com/thanneken/JubPalProcess).

## Assessing

### `measure.py`

Measures the minimum value, maximum value, and deviation for all the images files in the present directory. 
Command line arguments can be used to select a different directory of filter for a particular field specified in the filename.

```bash
~/git/JubPalCapture$ ./measure.py -h
usage: measure.py [-h] [-d DIRECTORY] [-o OBJECT] [-s SENSOR] [-l LENS] [-f FILTER] [-i ILLUMINANT] [-g GAIN] [-a APERTURE] [-t TIME] [-c CLOCK] [-e EXT]

options:
  -h, --help            show this help message and exit
  -d DIRECTORY, --directory DIRECTORY
  -o OBJECT, --object OBJECT
  -s SENSOR, --sensor SENSOR
  -l LENS, --lens LENS
  -f FILTER, --filter FILTER
  -i ILLUMINANT, --illuminant ILLUMINANT
  -g GAIN, --gain GAIN
  -a APERTURE, --aperture APERTURE
  -t TIME, --time TIME
  -c CLOCK, --clock CLOCK
  -e EXT, --ext EXT
```

### `histogram.py`

Produces histogram images in a subdirectory called `histogram` for all files specified on the command line.
For example:

```bash
./histogram.py ~/Pictures/Manuscript_001r/Flattened/*.tif
```

Creates the subdirectory `~/Pictures/Manuscript_001r/Flattened/histogram/` and histogram images for each `.tif` file in `Flattened`.

### `measurenoise.py`

This tool starts with a `.yaml` file and fills in missing information as needed.
To start, use a text editor or bash to create a `snr.yaml` file.

```bash
cd ~/Pictures/Manuscript_001r/
for i in Flattened/*.tif; do echo "${i}:" >> snr.yaml ; done
cd -
./measurenoise.py ~/Pictures/Manuscript_001r/snr.yaml
```

For each image file, noise will be measured and recorded back into the original snr.yaml file.
Two regions will be measured: the full frame and the center third.
Additional custom regions can be written into the `snr.yaml` file.
For each regions noise will be measured as LinearSNR, dB, and Noise.

### `graphnoise.py`

Reads one or more `snr.yaml` files from command-line arguments and draws graphs to the desktop.
There are many variations that may be swapped by editing the code.

```bash
./graphnoise.py ~/Pictures/Manuscript_001/snr.yaml
```

## Libraries

* `libqhy.py` for QHY Astrophotography cameras, requires `libqhyccd.so`
* `libcanon.py` for Canon EOS Digital (e.g., Canon R7), requires [edsdk-python](https://github.com/thanneken/edsdk-python)
* `libchdk.py` for Canon Hack Development Kit (e.g. Kolari Elph), requires [chdkpth-python](https://github.com/a-hurst/chdkptp-python)
* `libflir.py` for Flir industrial cameras, requires [PySpin](https://catimapy.readthedocs.io/en/latest/camera_drivers_FLIRPySpin.html)
* `libpixelink.py` for Pixelink industrial cameras (not fully tested)

Depending on the task, different Python modules are required.
The design assumes a user willing to interpret error messages and install Python modules.
