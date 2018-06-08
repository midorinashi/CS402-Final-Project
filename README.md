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
1) Find Reactivision application
    1. Right-click -> "Show Package Contents" -> "Contents" -> "Resources" -> "camera.xml"
    2. In line `<camera id="0">`, play with id number until camera is synced with plugged in camera
