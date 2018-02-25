import imageio
imageio.plugins.ffmpeg.download()

import matplotlib
matplotlib.use('TkAgg')
from moviepy.editor import *

import tuio
from pynput import keyboard

import os, glob, time


POINTER_OFFSET = 0.036

importedClipNames = [] # clip names in the import folder from oldest to newest add date

# credit to https://www.daniweb.com/programming/software-development/code/216688/file-list-by-date-python
def importClips():
    date_file_list = []
    for file in glob.glob("./imports/*.*"):
        # retrieves the stats for the current file as a tuple
        # (mode, ino, dev, nlink, uid, gid, size, atime, mtime, ctime)
        # the tuple element mtime at index 8 is the last-modified-date
        stats = os.stat(file)
        # create tuple (year yyyy, month(1-12), day(1-31), hour(0-23), minute(0-59), second(0-59),
        # weekday(0-6, 0 is monday), Julian day(1-366), daylight flag(-1,0 or 1)) from seconds since epoch
        # note:  this tuple can be sorted properly by date and time
        lastmod_date = time.localtime(stats[8])
        # create list of tuples ready for sorting by date
        date_file_tuple = lastmod_date, file
        date_file_list.append(date_file_tuple)

    date_file_list.sort() # oldest video first
    for file in date_file_list:
        file_name = file[1]
        # add the clip if the name is new
        if file_name not in importedClipNames:
            importedClipNames.append(file_name)
    print "There are ", len(importedClipNames), " imported clips."
    print importedClipNames

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
        startxpos = -1 # 0 indicates which clip to start with

        for obj in objects:
            #print obj, obj.xpos, obj.ypos, "hi"
            if obj.id == 0:
                startxpos = obj.xpos
            #if the fiducial has a clip associated with it
            else:
                if obj.id <= len(importedClipNames):
                    # the first imported clip is associated with fiducial 1 since 0 is the seeker
                    fileClip = VideoFileClip(importedClipNames[obj.id - 1])
                    clips.append(fileClip)
                else:
                    txtClip = TextClip(str(obj.id),color='white', font="Amiri-Bold",
                                       kerning = 5, fontsize=100).set_pos('center').set_duration(2)
                    clips.append(CompositeVideoClip([txtClip], size=screensize).set_fps(25))
                xposes.append(obj.xpos)

        #when playing, play starting from fiducial 0 if it's on the screen
        if clipFromPointer and startxpos != -1:
            clips = [clip for xpos,clip in zip(xposes,clips) if xpos > startxpos - POINTER_OFFSET]
        print len(clips), xposes

        #concatenate all clips
        if len(clips) > 0:
            cvc = concatenate_videoclips(clips, method="compose")
            #hack to get the audio working, apparently it doesn't copy audio fps properly
            if cvc.audio != None:
                cvc.audio.fps = 44100
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
        #the default video file encodes audio in a way quicktime won't play, so we add these params
        clip.write_videofile("video.mp4", codec="libx264", temp_audiofile='temp-audio.m4a', remove_temp=True, audio_codec='aac')


def on_press(key):
    if key == keyboard.Key.space:
        play()
    print key, 'pressed'
    if hasattr(key, 'char'):
        if key.char == 's':
            save()
        if key.char == 'i':
            importClips()

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


