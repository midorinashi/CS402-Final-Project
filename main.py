import imageio
imageio.plugins.ffmpeg.download()

import matplotlib
matplotlib.use('TkAgg')
from moviepy.editor import *

import tuio
from pynput import keyboard

def play():
    try:
    	#haxx to ensure the TUIO message is fresh - sometimes it's not??
    	for i in range(20):
            tracking.update()
        print sum(1 for _ in tracking.objects())
        screensize = (720,460)
        clips = []
        for obj in tracking.objects():
            print obj, obj.xpos, "hi"
            txtClip = TextClip(str(obj.id),color='white', font="Amiri-Bold",
                               kerning = 5, fontsize=100).set_pos('center').set_duration(2)
            clips.append(CompositeVideoClip([txtClip], size=screensize))
        
        return clips

    except KeyboardInterrupt:
        tracking.stop()

def on_press(key):
	if key == keyboard.Key.space:
        print "hi"
        clips = play()
        if len(clips) > 0:
            cvc = concatenate_videoclips(clips)
            cvc.preview()

def on_release(key):
    print('{0} released'.format(
        key))
    if key == keyboard.Key.esc:
        # Stop listener
        return False

tracking = tuio.Tracking()
print "loaded profiles:", tracking.profiles.keys()
print "list functions to access tracked objects:", tracking.get_helpers()

while True:
    with keyboard.Listener(
            on_press=on_press,
            on_release=on_release) as listener:
        listener.join()


#clip = VideoFileClip("videoviewdemo.mp4")
#clip.preview()


