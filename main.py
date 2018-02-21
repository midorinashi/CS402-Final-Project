import imageio
imageio.plugins.ffmpeg.download()

import matplotlib
matplotlib.use('TkAgg')
from moviepy.editor import *

import tuio
from pynput import keyboard

POINTER_OFFSET = 0.036

def concatenate(clipFromPointer=False):
    try:
        #haxx to ensure the TUIO message is fresh - sometimes it's not??
        for i in range(50):
            tracking.update()

        print sum(1 for _ in tracking.objects()),'clips found!'
        screensize = (720,460)
        objects = sorted(tracking.objects(), key=lambda x: x.xpos)
        print 'clip order:', [obj.id for obj in objects]

        clips = []
        xposes = []
        startxpos = -1 # 28 indicates which clip to start with

        for obj in objects:
            #print obj, obj.xpos, obj.ypos, "hi"
            if obj.id == 28:
                startxpos = obj.xpos
            else:
                txtClip = TextClip(str(obj.id),color='white', font="Amiri-Bold",
                                   kerning = 5, fontsize=100).set_pos('center').set_duration(2)
                clips.append(CompositeVideoClip([txtClip], size=screensize))
                xposes.append(obj.xpos)

        #when playing, play starting from fiducial 28 if it's on the screen
        if clipFromPointer and startxpos != -1:
            clips = [clip for xpos,clip in zip(xposes,clips) if xpos > startxpos - POINTER_OFFSET]
        print len(clips), xposes

        #concatenate all clips
        if len(clips) > 0:
            cvc = concatenate_videoclips(clips)
            return cvc

    except KeyboardInterrupt:
        tracking.stop()
    return None

def play():
    clip = concatenate(clipFromPointer=True)
    if clip != None:
        clip.preview()


def save():
    clip = concatenate()
    if clip != None:
        clip.write_videofile("video.mp4",fps=25,codec='mpeg4')


def on_press(key):
    if key == keyboard.Key.space:
        play()
    print key, 'pressed'
    if hasattr(key, 'char') and key.char == 's':
        save()

def on_release(key):
    print key, 'released'
    if key == keyboard.Key.esc:
        # Stop listener
        print 'Goodbye!'
        return False

tracking = tuio.Tracking()
print "loaded profiles:", tracking.profiles.keys()
print "list functions to access tracked objects:", tracking.get_helpers()

with keyboard.Listener(
        on_press=on_press,
        on_release=on_release) as listener:
    listener.join()


