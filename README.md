# NetworkAnalyser 

## Introduction
Python program that uses the BG7 network analyser which is available from a number of ebay sellers (such as
[here](http://www.ebay.co.uk/itm/35MHz-4-4GHz-USB-SMA-Source-Signal-Generator-Simple-Spectrum-Analyzer-35M-4-4G-/311103521591)
 ). What the actual name of the device is, isn't that clear! 

As I have no Windows machines, I needed some other way to use it. I
looked at the code that was posted
[here](https://github.com/DoYouKnow/BG7TBL_Reader), but that always
crashed when I ran it (I think because I was getting more zeros than
it expected).  So I wrote my own program to talk to the device that:


* has a guiqwt graphics front end around it
* does mean and max hold
* can zoom and scroll around
* can rescan to the current bounds of the frequency axis
* has a progress bar to show 

Its early days for the program - I'm sure there are a whole bunch of
bugs and missing features. And not having any documentation doesn't
help!

## Screenshot(s)

This is a screenshot of attaching an antenna to the input and looking at the local DAB transmitter:
![](https://github.com/darkstar007/NetworkAnalyser/blob/master/doc/screenshots/netan_screen1.jpg)

## Code description

T.B.D.

## Dependancies

* [guidata](https://code.google.com/p/guidata/)
* [guiqwt](https://code.google.com/p/guiqwt/) 
* QWT5
* Qt4

These are all available in Debian (and also Python(x,y) for Windows) -
fedora users will have to install the first two packages themselves (I beleive).

