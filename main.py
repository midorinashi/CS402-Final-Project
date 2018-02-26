import imageio
imageio.plugins.ffmpeg.download()

import matplotlib
matplotlib.use('TkAgg')
from moviepy.editor import *
import moviepy.video.fx.all as vfx

import tuio
from pynput import keyboard

import os, glob, time


POINTER_OFFSET = 0.036
screensize = (720,460)
effectsFiducialIds = range(1, 6)

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

#speeds up clips by up to a factor of 4 and slows down clips down to a factor of 0.25
def changeSpeed(effectObj, clip):
    print "angle", effectObj.angle
    # 0 degrees indicates normal speed
    speed = 1
    #slow down - 225, 270, and 315 degrees are .25, .5, and .75 respectively
    if effectObj.angle >= 225:
        speed = (effectObj.angle - 180) / 180.0
    #speed up - 45, 90, and 135 degrees are 1.5, 2, and 4 respectively
    #note that between 1 and 2 it goes up by .5 per 45 degrees and between 2 and 4 it scales differently
    elif effectObj.angle < 90:
        speed = (effectObj.angle / 90.0) + 1
    elif effectObj.angle <= 135:
        speed = (effectObj.angle - 90) / 22.5 + 2
    #if it's basically pointing down, don't do anything - unclear what they want
    return clip.speedx(speed)

def changeBrightness(effectObj, clip):
    brightness = (effectObj.angle / 360) * 1.5
    return clip.fx(vfx.colorx, brightness)

# could be replaced by fiducial glove
def trimClip(effectObj, clip):
    if effectObj.angle < 180:
        return clip.subclip((effectObj.angle / 180.0) * clip.duration, clip.duration)
    return clip.subclip(0, ((effectObj.angle - 180) / 180.0) * clip.duration)

# currently adds text to bottom of video based on keyboard input
# ugh
def addText(effectObj, clip):
    text = raw_input("Describe this scene: ")
    txtClip = TextClip(text, color='white', font="Amiri-Bold",
                                       kerning = 4, fontsize=20).set_pos('bottom').set_duration(clip.duration)
    return CompositeVideoClip([clip, txtClip])

def applyEffects(effectObjs, clips, clipObjs):
    for effectObj in effectObjs:
        for index in range(len(clipObjs)):
            clipObj = clipObjs[index]
            #if the effect fiducial looks like it's in line with the given clip objects
            if effectObj.xpos >= clipObj.xpos - POINTER_OFFSET and \
                    effectObj.xpos <= clipObj.xpos + POINTER_OFFSET:
                if effectObj.id == 1:
                    clips[index] = clips[index].fx(vfx.time_mirror)
                if effectObj.id == 2:
                    clips[index] = changeSpeed(effectObj, clips[index])
                if effectObj.id == 3:
                    clips[index] = changeBrightness(effectObj, clips[index])
                if effectObj.id == 4:
                    clips[index] = trimClip(effectObj, clips[index])
                if effectObj.id == 5:
                    clips[index] = addText(effectObj, clips[index])

def concatenate(clipFromPointer=False):
    try:
        #haxx to ensure the TUIO message is fresh - sometimes it's not??
        for i in range(100):
            tracking.update()

        print sum(1 for _ in tracking.objects()),'clips found!'
        objects = sorted(tracking.objects(), key=lambda x: x.xpos)
        print 'clip order:', [obj.id for obj in objects]

        clips = []
        clipObjs = []
        effectObjs = []
        startxpos = -1 # 0 indicates which clip to start with

        for obj in objects:
            if obj.id == 0:
                startxpos = obj.xpos
            #if the fiducial has a clip associated with it
            elif obj.id <= len(effectsFiducialIds):
                effectObjs.append(obj)

                print "id", obj.id, "angle", obj.angle
            else:
                if obj.id <= len(importedClipNames) + len(effectsFiducialIds):
                    # the first imported clip is associated with fiducial 1 since 0 is the seeker
                    fileClip = VideoFileClip(importedClipNames[obj.id - 1 - len(effectsFiducialIds)])
                    clips.append(fileClip)
                else:
                    txtClip = TextClip(str(obj.id),color='white', font="Amiri-Bold",
                                       kerning = 5, fontsize=100).set_pos('center').set_duration(2)
                    clips.append(CompositeVideoClip([txtClip], size=screensize).set_fps(25))
                clipObjs.append(obj)

        #when playing, play starting from fiducial 0 if it's on the screen
        if clipFromPointer and startxpos != -1:
            clips = [clip for obj,clip in zip(clipObjs,clips) if obj.xpos > startxpos - POINTER_OFFSET]
        print len(clips)

        applyEffects(effectObjs, clips, clipObjs)

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


