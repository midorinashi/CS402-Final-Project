# CS402-Final-Project
ClipWorks: A Tangible Interface for Collaborative Video Editing

# Setup
1) `pip install -r requirements.txt`  
2) `brew install imagemagick`  
3) `brew install ffmpeg`
4) *for running simulator only:*  
 - Download TUIO simulator from http://prdownloads.sourceforge.net/reactivision/TUIO_Simulator-1.4.zip?download  
 - Run TuioSimulator.jar

5) `python main.py` 

# Running on TUI table
1) Install Reactivision: http://reactivision.sourceforge.net/
2) Plug in external camera and open Reactivision
3) *If Reactivision does not match with what the camera should show:*
- Find Reactivision application
- Right-click -> "Show Package Contents" -> "Contents" -> "Resources" -> "camera.xml"
- In line `<camera id="0">`, try id number 0, 1, 2, etc. until camera is synced with plugged in camera (you will need to save the `camera.xml` file after each change and restart Reactivision)
4) Move the camera under the middle of the TUI table

# Calibrating TUI table
1) Open Reactivision, place a fiducial on the TUI table
- *press 'h' for help menu*
2) press 's' (to see a clearer image)
3) press 'o' for camera options
- Change "Exposure Mode" to "Manual"
- Play with "Exposure Time" until all fiducial numbers are clearly shown on Reactivision screen (try 120 to start)
4) press 'c' (this enters calibration mode)
5) move the fiducial around on the table, see how it is tracked in Reactivision
- *If horizontal movement is flipped*: press 'i' -> Right arrow (should now say "invert X-axis 1")
- *If vertical movement is flipped*: press 'i' -> Down arrow -> Right arrow (should now say "invert Y-axis 1")
- press 'i' to return to calibration
6) Move / rotate camera so that it exactly shows the size of the TUI table
7) Plug in projector power, move mirror under table and focus projector lens until it exactly displays on the TUI screen
8) Plug in an HDMI cable to the projector and to laptop



