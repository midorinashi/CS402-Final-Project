import imageio
imageio.plugins.ffmpeg.download()

import matplotlib
matplotlib.use('TkAgg')
from moviepy.editor import *

import tuio
from pynput import keyboard

def concatenate():
    clips = []
    try:
        #haxx to ensure the TUIO message is fresh - sometimes it's not??
        for i in range(50):
            tracking.update()
        print sum(1 for _ in tracking.objects()),'clips found!'
        screensize = (720,460)
        objects = sorted(tracking.objects(), key=lambda x: x.xpos)
        print 'clip order:', [obj.id for obj in objects]
        for obj in objects:
            txtClip = TextClip(str(obj.id),color='white', font="Amiri-Bold",
                               kerning=5, fontsize=100,
                               size=screensize).set_pos('center').set_duration(2)
            clips.append(txtClip)

    except KeyboardInterrupt:
        tracking.stop()
    return clips

def play():
    clips = concatenate()
    if len(clips) > 0:
        cvc = concatenate_videoclips(clips)
        cvc.preview()


def save():
    clips = concatenate()
    if len(clips) > 0:
        cvc = concatenate_videoclips(clips)
        cvc.write_videofile("video.mp4",fps=25,codec='mpeg4')


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


