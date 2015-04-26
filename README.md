# NetworkAnalyser 

## Introduction
Python program that uses the BG7 network analyser which is available from a number of ebay sellers (such as
[here](http://www.ebay.co.uk/itm/35MHz-4-4GHz-USB-SMA-Source-Signal-Generator-Simple-Spectrum-Analyzer-35M-4-4G-/311103521591)
 ). What the actual name of the device is, isn't that clear - but appears to be *BG7TBL*, with some technical details 
[here](http://www.dalbert.net/?p=219)


As I have no Windows machines, I needed some other way to use it. I
looked at the code that was posted
[here](https://github.com/DoYouKnow/BG7TBL_Reader), but that always
crashed when I ran it (I think because I was getting more zeros than
it expected).  So I wrote my own program to talk to the device that:


* has a guiqwt graphics front end around it
* does mean and max hold
* can zoom and scroll around
* can rescan to the current bounds of the frequency axis
* has a progress bar to show the data transfer from the device

Its early days for the program - I'm sure there are a whole bunch of
bugs and missing features. And not having any real documentation about the
device doesn't help!

## Timings

I have done some timings from the device and it appears to send output
at around 4.2ms/sample. This means a 6,000 sample sweep will take
~25seconds (6000 * 0.0042).  The time per sample doesn't seem to
change with centre frequency, number of samples or bandwidth.

## Screenshot(s)

This is a screenshot of attaching an antenna to the input and looking at the local DAB transmitter:
![](https://github.com/darkstar007/NetworkAnalyser/blob/master/doc/screenshots/netan_screen1.jpg)

And this is the view of FM stereo broadcast stations:
![](https://github.com/darkstar007/NetworkAnalyser/blob/master/doc/screenshots/netan_screen2.jpg)


## Code description

### Commands
It looks like commands of are the form: `0x8f <command> <arguments>`, where command is:

| Command | Description | Arguments |
|:-------:|-------------|---------------------------|
|    x    | Receive in log (power) mode    | `"%09d%08d%04d", frequency, stepSize, numSamples` |
|    w    | Receive in linear (power) mode | `"%09d%08d%04d", frequency, stepSize, numSamples` |
|    f    | CW frequency transmission | `"%09d", frequency` |
|    v    | Get firmware version | No argumens |
!    r    | ??? | ??? |
|    m/n  |  ??? | ??? |
|    s    |  ??? | ??? |

`frequency` and `stepSize` are in 10Hz steps (i.e. 1000000 would be represented by 1000000/10 = 100000).

### Design
T.B.D.

## Dependencies

* [guidata](https://code.google.com/p/guidata/)
* [guiqwt](https://code.google.com/p/guiqwt/) 
* QWT5
* Qt4

These are all available in Debian (and also Python(x,y) for Windows) -
fedora users will have to install the first two packages themselves (I believe).

## ToDo

1. Look at calibration (tx & rx?)
2. Easy way to save data to disk (numpy arrays and screenshots).
3. Allow access to an database of known bands (so in my DAB example above, my GUI would have the
ability to annotate the DAB channels (11D, 12B & 12D) in my plot).
4. Move the GUI toolkit from guiqwt/guidata as they do not appear to be maintained any more.
5. Allow better use of GUI with touchscreen - I'm thinking RPi2/BBB with a small touchscreen on it would be a cool bit of test equipment.
6. ~~Better label of frequency axis (i.e. mega, giga) - as 220MHz is much easier than 2.2e8!~~
7. Figure out way the y-axis units are - prolly part of (1)
8. Improve GUI to allow easy selection of centre frequency.
9. Fix bugs....
10. Better error handling (eg. when it can't open the serial port)
11. Platform independent way to select a serial port
12. Remember settings (frequency, bandwidth, max hold, etc) from last use.

