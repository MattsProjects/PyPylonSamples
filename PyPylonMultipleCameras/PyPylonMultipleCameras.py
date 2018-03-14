# PyPylonMultipleCameras.py
# Example of using multiple cameras with the InstantCameraArray
#
#	Copyright 2018 Matthew Breit <matt.breit@gmail.com>
#
#	Licensed under the Apache License, Version 2.0 (the "License");
#	you may not use this file except in compliance with the License.
#	You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#	Unless required by applicable law or agreed to in writing, software
#	distributed under the License is distributed on an "AS IS" BASIS,
#	WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#	See the License for the specific language governing permissions and
#	limitations under the License.
#
#	THIS SOFTWARE REQUIRES ADDITIONAL SOFTWARE (IE: LIBRARIES) IN ORDER TO COMPILE
#	INTO BINARY FORM AND TO FUNCTION IN BINARY FORM. ANY SUCH ADDITIONAL SOFTWARE
#	IS OUTSIDE THE SCOPE OF THIS LICENSE.
#
# Based on PyPylon (https://github.com/StudentCV/PyPylon) Thank you StudentCV!

import pypylon.pylon as pylon

# for demo purposes we will trigger the cameras in the background
import thread 
import time

# for demo purposes we will run this in a separate thread to trigger all of the cameras
def SendTrigger(cameraArray, triggerRate):
    while True:
        if cameraArray.IsGrabbing():
            for camera in cameraArray:
                camera.ExecuteSoftwareTrigger()
        time.sleep(1/float(triggerRate))

try:
    # number of images to grab from each camera
    numberOfImages = 10
    # framerate to trigger at
    frameRate = 10
    
    # for demo purposes, we will only look for certain types of cameras
    filters = list()
    filter1 = pylon.DeviceInfo()
    filter1.SetDeviceClass("BaslerUsb")
    filters.append(filter1)

    # detect and enumerate devices into a device info list
    tlFactory = pylon.TlFactory.GetInstance()
    devices = tlFactory.EnumerateDevices(filters)
    
    # We will use however many cameras are found
    numberOfCameras = len(devices)

    # The InstantCameraArray is generic (interface agnostic)
    # It encapsulates the physical camera and driver into one convinient object
    cameras = pylon.InstantCameraArray(numberOfCameras)

    # Attach each camera in the array to a physical device
    for i in range(cameras.GetSize()):
        cameras[i].Attach(tlFactory.CreateDevice(devices[i]))
        cameras[i].SetCameraContext(i)
        print "Using Camera ", cameras[i].GetCameraContext(), " : ", cameras[i].GetDeviceInfo().GetFriendlyName()

    # Open the cameras to access features
    cameras.Open()

    # We use the Genicam API to change features via strings
    # because we are programming generically
    for i in range(cameras.GetSize()):
        cameras[i].GetNodeMap().GetNode("Width").SetValue(640)
        cameras[i].GetNodeMap().GetNode("Height").SetValue(480)
        cameras[i].GetNodeMap().GetNode("ExposureAuto").SetValue("Off")
        cameras[i].GetNodeMap().GetNode("ExposureTime").SetValue(5000)
        # For multiple cameras, we always need to consider bandwidth implications
        # Here is an example of limiting/splitting the bandwidth between cameras
        # 300 MB/sec per camera is usually a safe maximum for a single good USB3 chipset
        cameras[i].GetNodeMap().GetNode("DeviceLinkThroughputLimitMode").SetValue("On")
        maxSupportedBps = cameras[i].GetNodeMap().GetNode("DeviceLinkThroughputLimit").GetMax() # sometimes the maxmium bandwidth supported is less (ie usb2)
        cameras[i].GetNodeMap().GetNode("DeviceLinkThroughputLimit").SetValue(min((300000000/numberOfCameras),maxSupportedBps)) 
        # It's common to want to synchronize multiple cameras.
        # It's best to use a hardware trigger in parallel to all cameras for this.
        # But for demo purposes, we will use a software trigger instead
        cameras[i].GetNodeMap().GetNode("TriggerSelector").SetValue("FrameStart")
        cameras[i].GetNodeMap().GetNode("TriggerSource").SetValue("Software") # hardware = "Line1", "Line2", etc.
        cameras[i].GetNodeMap().GetNode("TriggerMode").SetValue("On")
        

    # Driver/Grabber features are natively supported by the InstantCamera API
    # Because they are common to all camera interfaces
    for i in range(cameras.GetSize()):
        cameras[i].MaxNumBuffer.SetValue(20) # For demo only. Default is 10.

    # create a list of image counters
    imageCounters = list()
    for i in range (cameras.GetSize()):
        imageCounters.append(0)

    # Start grabbing images.
    # The camera's physical acquisition starts, and the driver's streamgrabber is configured (buffers created, etc.)
    cameras.StartGrabbing()

    # for demo purposes, start the triggering thread
    thread.start_new_thread(SendTrigger,(cameras, frameRate))
   
    while cameras.IsGrabbing():
        # Retrieve a GrabResult from the driver
        # Note: Even if triggered simultaneously, images can arrive asychronously.
        # We will use result.GetCameraContext() to sort them out later
        result = cameras.RetrieveResult(5000,pylon.TimeoutHandling_ThrowException)

        # The GrabResult is a container. It could hold a good image, corrupt image, no data, etc.
        if result.GrabSucceeded:
            print ""
            print "Grab Result Succeeded! We have an Image!"
            print " From Camera number        : ", result.GetCameraContext()
            print " Image number              : ", result.GetBlockID()
            print " Dimensions                : ", result.GetWidth(), "x", result.GetHeight()
            buffer = result.GetBuffer()
            print " Gray value of first pixel : ", buffer[0]

            # The Pylon API supports display directly from the GrabResult
            pylon.DisplayImage(result.GetCameraContext(),result) 
            
            # keep count of the images we have from each camera
            imageCounters[result.GetCameraContext()] = imageCounters[result.GetCameraContext()] + 1  
            print "Status:"
            for i in range(cameras.GetSize()):
                print " Camera: ", i, " Images: ", imageCounters[i]   
                
            # stop when we have at least numberOfImages from each camera
            if all(i >= numberOfImages for i in imageCounters):
                 cameras.StopGrabbing()
                 print ""
                 print "All Images Received"   
                 print "Grabbing Stopped"     
        else:
            print ""
            print "Grab Result Failed!"
            print " Error Description : ", result.GetErrorDescription()
            print " Error Code        : ", result.GetErrorCode()
            cameras.StopGrabbing()
            print "Grabbing Stopped"

    print ""
    print "finished!"

except pylon.GenericException as err:
    print("Pylon error: {0}".format(err))

