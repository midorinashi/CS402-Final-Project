import imageio
imageio.plugins.ffmpeg.download()
import graphics as g

import matplotlib
matplotlib.use('TkAgg')
from moviepy.editor import *
import moviepy.video.fx.all as vfx

import tuio
from pynput import keyboard

import os, glob, math, time, sys

CANVAS_WIDTH = 500
CANVAS_HEIGHT = 500

POINTER_OFFSET = 0.036
screensize = (720,460)

importedClipNames = [] # clip names in the import folder from oldest to newest add date
effectsForClips = {} # each index in the form of fiducialid: [{func: func, effectObjs: [array of effectObjs]]}]

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

#scales distance of a slider to a fraction from 0 to 1, where 0 is if the slider is all the way to the
#left and 1 is where the slider is all the way to the right
MINDISTANCE = .084
MAXDISTANCE = .26
def scaledDistance(obj1, obj2):
    dist = math.sqrt((obj1.xpos - obj2.xpos) ** 2 + (obj1.ypos - obj2.ypos) ** 2)
    scaledDist =  1 - (dist - MINDISTANCE) / (MAXDISTANCE - MINDISTANCE)
    print "scaled distance", scaledDist
    if scaledDist < 0:
        return 0
    elif scaledDist > 1:
        return 1
    return scaledDist

def reverse(effectObjs, clip):
    return clip.fx(vfx.time_mirror)

#speeds up clips by up to a factor of 4 and slows down clips down to a factor of 0.25
def changeSpeed(effectObjs, clip):
    # 0 degrees indicates normal speed
    speed = 1
    val = scaledDistance(effectObjs[1], effectObjs[2])
    #slow down - 0, .16, and .33 vals are .25, .5, and .75 respectively
    if val < .5:
        speed = (val * 3 / 2) + .25
    #speed up - .66, .83, and 1 vals are 1.5, 2, and 4 respectively
    #note that between 1 and 2 it goes up by .5 per 45 degrees and between 2 and 4 it scales differently
    elif val < .83:
        speed = ((val - .5) / .33) + 1
    else:
        speed = (val - .83) / .17 * 2 + 2
    return clip.speedx(speed)

def changeBrightness(effectObjs, clip):
    val = scaledDistance(effectObjs[1], effectObjs[2])
    brightness = val * 1.5
    return clip.fx(vfx.colorx, brightness)

# could be replaced by fiducial glove
def trimClip(effectObjs, clip):
    startVal = scaledDistance(effectObjs[1], effectObjs[2])
    endVal = scaledDistance(effectObjs[1], effectObjs[3])
    return clip.subclip(startVal * clip.duration, endVal * clip.duration)

# currently adds text to bottom of video based on keyboard input
# ugh
def addText(effectObjs, clip):
    text = raw_input("Describe this scene: ")
    txtClip = TextClip(text, color='white', font="Amiri-Bold",
                                       kerning = 4, fontsize=20).set_pos('bottom').set_duration(clip.duration)
    return CompositeVideoClip([clip, txtClip])


'''
All effects have at least two fiducials associated with it. (For now, we assume all fiducials are unique)
Idea of what this looks like below. 1 and 2 are two different fiducials that don't move. 3 and 4 are 
optional extra fiducials that can slide.

Basic - for reverse      One slider          Two sliders
 _______________       _______________     _______________    
|1 ___________  |     |1 ___________  |   |1 ___________  |   
| |           | |     | |           | |   | |           | |   
| |           | |     | |           | |   | |           | |   
| |           | |     | |           | |   | |           | |   
| |           | |     | |           | |   | |           | |   
| |___________| |     | |___________| |   | |___________| |   
|              2|     |  --3-------- 2|   |  ---3----4-- 2|   
|_______________|     |_______________|   |_______________|   
'''

effectsFunctions = [reverse, changeSpeed, changeBrightness, trimClip, addText]
fiducialsPerFunction = [2, 3, 3, 4, 2]
numEffectsIds = sum(fiducialsPerFunction)

def findClipIndexInsideEffectBlock(currEffectObjs, clipObjs):
    top = currEffectObjs[0].ypos
    left = currEffectObjs[0].xpos
    bottom = currEffectObjs[1].ypos
    right = currEffectObjs[1].xpos

    #if the block has been rotated more than 180, make the lesser values top/left
    if top > bottom:
        top, bottom = bottom, top
    if left > right:
        left, right = right, left

    #if the blocks are rotated such that the fiducials are horizontal or vertical to each other,
    #allow some extra space to sense the clip object
    THRESHOLD = .02
    EXTRASPACE = .05
    if bottom - top < THRESHOLD:
        top -= EXTRASPACE
        bottom += EXTRASPACE
    if right - left < THRESHOLD:
        left -= EXTRASPACE
        right += EXTRASPACE

    for index in range(len(clipObjs)):
        clipObj = clipObjs[index]
        print top, clipObj.ypos, bottom, left, clipObj.xpos, right
        if top <= clipObj.ypos <= bottom and left <= clipObj.xpos <= right:
            return index
    return None

def updateEffects(effectObjs, clipObjs):
    effectObjIds = [effectObj.id for effectObj in effectObjs]
    print effectObjIds
    startId = 1 # tracks what's the first fiducial id associated with an effect, first effect fiducial is 1

    if len(effectsFunctions) != len(fiducialsPerFunction):
        print "Effect functions are not properly assigned fiducials"
        return

    for effectIndex in range(len(effectsFunctions)):
        currEffectObjs = []
        for fiducialId in range(startId, startId + fiducialsPerFunction[effectIndex]):
            #if not all fiducial Ids are 
            if fiducialId in effectObjIds:
                currEffectObjs.append(effectObjs[effectObjIds.index(fiducialId)])
            else:
                break
        else:
            # print "all clips on screen for effect ", effectIndex
            # print currEffectObjs
            clipIndex = findClipIndexInsideEffectBlock(currEffectObjs, clipObjs)
            # print "clipIndex", clipIndex, effectsForClips
            if clipIndex != None:
                fiducialId = clipObjs[clipIndex].id
                # print "applying ", effectIndex, " effect to clip id ", clipObjs[clipIndex].id
                if fiducialId not in effectsForClips:
                    effectsForClips[fiducialId] = {}
                effectsForClips[fiducialId][effectsFunctions[effectIndex]] = currEffectObjs
        startId += fiducialsPerFunction[effectIndex]

def applyEffects(clips, clipObjs):
    print "effectsForClips:", effectsForClips
    for clipIndex in range(len(clipObjs)):
        fiducialId = clipObjs[clipIndex].id
        if fiducialId in effectsForClips:
            effectDict = effectsForClips[fiducialId]
            for f in effectsFunctions:
                if f in effectDict:
                    effectObjs = effectDict[f]
                    print f, effectObjs, clips[clipIndex]
                    clips[clipIndex] = f(effectObjs, clips[clipIndex])

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
        prevxpos = 0
        prevypos = CANVAS_HEIGHT / 2.0

        for obj in objects:
            if obj.id == 0:
                startxpos = obj.xpos
            #if the fiducial has a clip associated with it
            elif obj.id <= numEffectsIds:
                effectObjs.append(obj)

                print "id", obj.id, "angle", obj.angle
            else:
                if obj.id <= len(importedClipNames) + numEffectsIds:
                    # the first imported clip is associated with fiducial 1 since 0 is the seeker
                    fileClip = VideoFileClip(importedClipNames[obj.id - 1 - numEffectsIds])
                    clips.append(fileClip)
                else:
                    txtClip = TextClip(str(obj.id),color='white', font="Amiri-Bold",
                                       kerning = 5, fontsize=100).set_pos('center').set_duration(2)
                    clips.append(CompositeVideoClip([txtClip], size=screensize).set_fps(25))
                clipObjs.append(obj)
                # draw to canvas
                video = g.Rectangle(g.Point(obj.xpos * CANVAS_WIDTH, obj.ypos * CANVAS_HEIGHT), g.Point(obj.xpos * CANVAS_WIDTH + 50, obj.ypos * CANVAS_HEIGHT + 50))
                video.setFill('bisque')
                video.draw(win)
                line = g.Line(g.Point(prevxpos + 50, prevypos + 25), g.Point(obj.xpos * CANVAS_WIDTH, obj.ypos * CANVAS_HEIGHT + 25))
                prevxpos = obj.xpos * CANVAS_WIDTH
                prevypos = obj.ypos * CANVAS_HEIGHT
                line.setArrow('last')
                line.setFill('gold')
                line.draw(win)

        #when playing, play starting from fiducial 0 if it's on the screen
        if clipFromPointer and startxpos != -1:
            clips = [clip for obj,clip in zip(clipObjs,clips) if obj.xpos > startxpos - POINTER_OFFSET]
        print len(clips)

        updateEffects(effectObjs, clipObjs)
        applyEffects(clips, clipObjs)

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
    if key.char == ' ':
        for item in win.items[:]:
            item.undraw()
        win.update()
        play()
    if key.char == '\x1b':
        # Stop listener
        print 'Goodbye!'
        sys.exit(0)
    print repr(key.char), 'pressed'
    # if hasattr(key, 'char'):
    if key.char == 's':
        save()
    if key.char == 'i':
        importClips()

# def on_release(key):
#     print key.char, 'released'
#     if repr(key.char) == "\'\x1b\'":
#         # Stop listener
#         print 'Goodbye!'
#         return False

tracking = tuio.Tracking()
print "loaded profiles:", tracking.profiles.keys()
print "list functions to access tracked objects:", tracking.get_helpers()

# listener = keyboard.Listener(
#         on_press=on_press,
#         on_release=on_release)
# listener.start()

win = g.GraphWin("prototype", 500, 500)
win.bind_all("<Key>", on_press)
g.root.mainloop()

