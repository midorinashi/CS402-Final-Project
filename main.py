import imageio
imageio.plugins.ffmpeg.download()

import matplotlib
matplotlib.use('TkAgg')
from moviepy.editor import *

import tuio
from pynput import keyboard

POINTER_OFFSET = 0.036

def concatenate(clipFromPointer=False):
    clips = []
    try:
        #haxx to ensure the TUIO message is fresh - sometimes it's not??
        for i in range(20):
            tracking.update()
        print sum(1 for _ in tracking.objects())
        screensize = (720,460)
        xposes = []
        startxpos = -1 # 28 indicates which clip to start with
        for obj in tracking.objects():
            print obj, obj.xpos, obj.ypos, "hi"
            if obj.id == 28:
                startxpos = obj.xpos
            else:
                txtClip = TextClip(str(obj.id),color='white', font="Amiri-Bold",
                                   kerning = 5, fontsize=100).set_pos('center').set_duration(2)
                clips.append(CompositeVideoClip([txtClip], size=screensize))
                xposes.append(obj.xpos)
        if clipFromPointer and startxpos != -1:
            clips = [clip for xpos,clip in sorted(zip(xposes,clips)) if xpos > startxpos - POINTER_OFFSET]
        else:
            clips = [clip for xpos,clip in sorted(zip(xposes,clips))]
        print len(clips), sorted(xposes)

    except KeyboardInterrupt:
        tracking.stop()
    return clips

def play():
    clips = concatenate(clipFromPointer=True)
    if len(clips) > 0:
        cvc = concatenate_videoclips(clips)
        cvc.preview()


def save():
    clips = concatenate()
    if len(clips) > 0:
        cvc = concatenate_videoclips(clips)
        cvc.write_videofile("video.mp4",fps=25,codec='mpeg4')


def on_press(key):
    # I can't get space and esc to work, so i'm using left and right shift instead for play and exit.
    if key == keyboard.Key.space:
        play()
    print key
    if hasattr(key, 'char') and key.char == 's':
        save()

def on_release(key):
    print('{0} released'.format(
        key))
    if key == keyboard.Key.esc:
        # Stop listener
        return False

tracking = tuio.Tracking()
print "loaded profiles:", tracking.profiles.keys()
print "list functions to access tracked objects:", tracking.get_helpers()

with keyboard.Listener(
        on_press=on_press,
        on_release=on_release) as listener:
    listener.join()


#clip = VideoFileClip("videoviewdemo.mp4")
#clip.preview()


