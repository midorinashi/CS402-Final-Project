import imageio
imageio.plugins.ffmpeg.download()
import threading
import numpy as np
import graphics as g

import matplotlib
matplotlib.use('TkAgg')
import pygame as pg
from moviepy.editor import *
import moviepy.video.fx.all as vfx

import tuio
from pynput import keyboard

import os, glob, math, time, sys, copy

# all screen sizes for testing, can play with this later
CANVAS_WIDTH = 720
CANVAS_HEIGHT = 460

# define colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GOLD = (255, 223, 0)
GRAY = (70,70,70)

POINTER_OFFSET = 0.036
screensize = (CANVAS_WIDTH, CANVAS_HEIGHT)
previewsize = (720, 210)

importedClipNames = [] # clip names in the import folder from oldest to newest add date
fiducialIdForClips = [] # fiducial id at index of the imported clip name that it is associated with
effectsForClips = {} # each index in the form of fiducialid: [{func: func, effectObjs: [array of effectObjs]]}]
imagesForClips = {} # cache that maps fiducial IDs to image previews

# initialize screen
pg.init()
screen = pg.display.set_mode(screensize)
pg.display.set_caption("VideoBlox")

def initScreen():
    screen.fill(BLACK)
    pg.display.flip()
    pg.display.toggle_fullscreen()

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
colorForFunction = [(255,255,100), (255, 100, 255), (200, 200, 200), (100, 255, 255), (100, 100, 255)]
numEffectsIds = sum(fiducialsPerFunction)
SPECIAL_FIDUCIALS = 3 # 0 for seek, 1-2 for preview

def updateVideoClips(clipObjs, clips):
    for obj in clipObjs:
        if obj.id in fiducialIdForClips:
            # the first imported clip is associated with fiducial 1 since 0 is the seeker
            fileClip = VideoFileClip(importedClipNames[fiducialIdForClips.index(obj.id)])
            clips.append(fileClip)
        elif len(fiducialIdForClips) < len(importedClipNames):
            # associate a new clip with this fiducial
            fiducialIdForClips.append(obj.id)
            fileClip = VideoFileClip(importedClipNames[fiducialIdForClips.index(obj.id)])
            clips.append(fileClip)
        else:
            imgClip = ImageClip("no-video-icon.jpg", duration=1.5).on_color()
            clips.append(CompositeVideoClip([imgClip]).set_fps(25))

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
        for fiducialId in range(startId + SPECIAL_FIDUCIALS - 1, 
                                startId + SPECIAL_FIDUCIALS - 1 + fiducialsPerFunction[effectIndex]):
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
                    effectsForClips[fiducialId] = []
                for index in range(len(effectsForClips[fiducialId])):
                    if effectsForClips[fiducialId][index]['func'] == effectsFunctions[effectIndex]:
                        del effectsForClips[fiducialId][index]
                        break
                effectsForClips[fiducialId].append({'func': effectsFunctions[effectIndex],
                                                    'effectObjs': currEffectObjs})
        startId += fiducialsPerFunction[effectIndex]

ONE_INCH = 35 #also equal to the video radius
VIDEO_WIDTH = 50
def applyEffects(clips, clipObjs):
    print "effectsForClips:", effectsForClips
    for clipIndex in range(len(clipObjs)):
        clipObj = clipObjs[clipIndex]
        fiducialId = clipObj.id
        if fiducialId in effectsForClips:
            effectArray = effectsForClips[fiducialId]
            effectIndex = len(effectArray)
            for entry in effectArray:
                f = entry['func']
                effectObjs = entry['effectObjs']
                # print f, effectObjs, clips[clipIndex]
                clips[clipIndex] = f(effectObjs, clips[clipIndex])
                print "applying effect:", f, effectObjs, clipIndex

                functionIndex = effectsFunctions.index(f)
                circleSize = ONE_INCH / 2 * effectIndex + 2 * ONE_INCH # one inch for the video radius, one inch for the video border
                color = colorForFunction[functionIndex]
                pg.draw.circle(screen, color, (int(clipObj.xpos * CANVAS_WIDTH), int(clipObj.ypos * CANVAS_HEIGHT)), circleSize)

                #border.draw(win)

                effectIndex -= 1

def drawArrow(startx, starty, endx, endy, color=WHITE):
    pg.draw.polygon(screen, color, ((startx, starty - 5), (startx, starty + 5), (endx - 10, endy + 5), (endx - 10, endy + 10), (endx, endy), (endx - 10, endy - 10), (endx - 10, endy - 5)))
    pg.draw.polygon(screen, BLACK, ((startx, starty - 5), (startx, starty + 5), (endx - 10, endy + 5), (endx - 10, endy + 10), (endx, endy), (endx - 10, endy - 10), (endx - 10, endy - 5)), 1)

def imdisplay(imarray, width=VIDEO_WIDTH, height=VIDEO_WIDTH, x=0, y=0):
    """Splashes the given image array on the given pygame screen """
    a = pg.surfarray.make_surface(imarray.swapaxes(0, 1))
    a = pg.transform.scale(a, (width, height))
    screen.blit(a, (x, y))

def drawVideoBoxesAndLines(clipObjs, clips, startxpos):
    """draws interface for screen"""
    prevxpos =  -ONE_INCH
    prevypos = CANVAS_HEIGHT / 2.0
    for i in range(len(clipObjs)):
        obj = clipObjs[i]
        if clips:
            video = clips[i].get_frame(0)
            imagesForClips[obj.id] = video
        else:
            video = imagesForClips[obj.id]
        pg.draw.circle(screen, BLACK, (int(obj.xpos * CANVAS_WIDTH), int(obj.ypos * CANVAS_HEIGHT)), 2 * ONE_INCH) # one inch for the video radius, one inch for the video border
        imdisplay(video, x=obj.xpos * CANVAS_WIDTH - VIDEO_WIDTH / 2, y=obj.ypos * CANVAS_HEIGHT - VIDEO_WIDTH / 2)
        if obj.xpos < startxpos:
            drawArrow(prevxpos + 2 * ONE_INCH, prevypos, 
                      obj.xpos * CANVAS_WIDTH - 2 * ONE_INCH, obj.ypos * CANVAS_HEIGHT, 
                      GRAY)
        else:
            drawArrow(prevxpos + 2 * ONE_INCH, prevypos,
                      obj.xpos * CANVAS_WIDTH - 2 * ONE_INCH, obj.ypos * CANVAS_HEIGHT)

        prevxpos = obj.xpos * CANVAS_WIDTH
        prevypos = obj.ypos * CANVAS_HEIGHT

    pg.display.flip() # limit calls to this b/c it takes hella long (refreshes display)

def fetchClips(clipFromPointer=False, objects=None, updated=True):
    importClips()
    try:
        #haxx to ensure the TUIO message is fresh - sometimes it's not??
        if not objects:
            for i in range(50):
                tracking.update()

            print sum(1 for _ in tracking.objects()),'blocks found!'
            objects = sorted(tracking.objects(), key=lambda x: x.id)
            print 'blocks order:', [obj.id for obj in objects]

        clips = []
        clipObjs = []
        effectObjs = []
        startxpos = -1 # 0 indicates which clip to start with
        previewObj = None

        for objIndex in range(len(objects)):
            obj = objects[objIndex]
            if obj.id == 0:
                startxpos = obj.xpos
            #if the fiducial has a clip associated with it
            elif obj.id == 2:
                prevObj = objects[objIndex - 1]
                if prevObj.id == 1:
                    obj.xpos = (obj.xpos + prevObj.xpos) / 2
                    obj.ypos = (obj.ypos + prevObj.ypos) / 2
                    previewObj = obj
            elif obj.id < numEffectsIds + SPECIAL_FIDUCIALS:
                effectObjs.append(obj)

                print "id", obj.id, "angle", obj.angle
            else:
                prevObj = objects[objIndex - 1]
                if obj.id == prevObj.id + 1 and obj.id % 2 == 0:
                    obj.xpos = (obj.xpos + prevObj.xpos) / 2
                    obj.ypos = (obj.ypos + prevObj.ypos) / 2
                    clipObjs.append(obj)

        clipObjs = sorted(clipObjs, key=lambda x: x.xpos)
        if updated:
            updateVideoClips(clipObjs, clips)
            updateEffects(effectObjs, clipObjs)
            applyEffects(clips, clipObjs)

        drawVideoBoxesAndLines(clipObjs, clips, startxpos)

        #when playing, play starting from fiducial 0 if it's on the screen
        if clipFromPointer and startxpos != -1:
            clips = [clip for obj,clip in zip(clipObjs,clips) if obj.xpos > startxpos - POINTER_OFFSET]

        #concatenate all clips
        if len(clips) > 0:
            print '# clips', len(clips)
            return clips, previewObj, clipObjs

    except KeyboardInterrupt:
        tracking.stop()
    return None, None, None

def concatenate(clips):
    cvc = concatenate_videoclips(clips, method="compose")
    #hack to get the audio working, apparently it doesn't copy audio fps properly
    if cvc.audio != None:
        cvc.audio.fps = 44100
    return cvc

#returns True if preview ended, False if the preview was interrupted
def playClipAtBlock(clip, block, fps=15, audio=True, audio_fps=22050,
             audio_buffersize=3000, audio_nbytes=2):
    """ 
    Displays the clip in a window, at the given frames per second
    (of movie) rate. It will avoid that the clip be played faster
    than normal, but it cannot avoid the clip to be played slower
    than normal if the computations are complex. In this case, try
    reducing the ``fps``.
    
    Parameters
    ------------
    
    fps
      Number of frames per seconds in the displayed video.
        
    audio
      ``True`` (default) if you want the clip's audio be played during
      the preview.
        
    audiofps
      The frames per second to use when generating the audio sound.
      
    """
    audio = audio and (clip.audio is not None)
    
    if audio:
        # the sound will be played in parrallel. We are not
        # parralellizing it on different CPUs because it seems that
        # pygame and openCV already use several cpus it seems.
        
        # two synchro-flags to tell whether audio and video are ready
        videoFlag = threading.Event()
        audioFlag = threading.Event()
        # launch the thread
        audiothread = threading.Thread(target=clip.audio.preview,
            args = (audio_fps,audio_buffersize, audio_nbytes,
                    audioFlag, videoFlag))
        audiothread.start()
    
    img = clip.get_frame(0)

    width = VIDEO_WIDTH
    height = VIDEO_WIDTH
    if block.id == 2:
        width = 300
        height = clip.h * 300 / clip.w
    xpos = block.xpos * CANVAS_WIDTH - width / 2
    ypos = block.ypos * CANVAS_HEIGHT - height / 2
    imdisplay(img, width=width, height=height, x=xpos, y=ypos)
    print block.xpos
    pg.display.flip()
    if audio: # synchronize with audio
        videoFlag.set() # say to the audio: video is ready
        audioFlag.wait() # wait for the audio to be ready
    
    t0 = time.time()
    for t in np.arange(1.0 / fps, clip.duration-.001, 1.0 / fps):
        
        img = clip.get_frame(t)
        
        for event in pg.event.get():
            if event.type == pg.KEYDOWN:
                if (event.key == pg.K_ESCAPE):
                    
                    if audio:
                        videoFlag.clear()
                    print( "Keyboard interrupt" )
                    return False
                    
        t1 = time.time()
        time.sleep(max(0, t - (t1-t0)) )
        imdisplay(img, width=width, height=height, x=xpos, y=ypos)
        pg.display.flip()
    return True

# reimplementing preview so video plays on same screen
def preview(clips, previewObj, clipObjs):
    print "previewing:", clips, previewObj, clipObjs
    if previewObj == None:
        for index in range(len(clips)):
            result = playClipAtBlock(clips[index], clipObjs[len(clipObjs) - len(clips) + index])
            if result == False:
                break
    else:
        clip = concatenate(clips)
        playClipAtBlock(clip, previewObj)

def play():
    clips, previewObj, clipObjs = fetchClips(clipFromPointer=True)
    print clips, previewObj
    if clips != None:
        preview(clips, previewObj, clipObjs)


def save():
    clips, previewObj, clipObjs = fetchClips()
    if clips != None:
        clip = concatenate(clips)
        #the default video file encodes audio in a way quicktime won't play, so we add these params
        clip.write_videofile("video.mp4", codec="libx264", temp_audiofile='temp-audio.m4a', remove_temp=True, audio_codec='aac')


def on_press(key):
    if key == 'space':
        initScreen()
        play()
    if key == 'escape':
        # Stop listener
        print 'Goodbye!'
        sys.exit(0)
    print key, 'pressed'
    if key == 's':
        save()

def trackingChanged(one, two):
    for i in range(len(one)):
        if (one[i].id != two[i].id or
            one[i].xpos != two[i].xpos or
            one[i].ypos != two[i].ypos):
            return True
    return False

tracking = tuio.Tracking()
print "loaded profiles:", tracking.profiles.keys()
print "list functions to access tracked objects:", tracking.get_helpers()

initScreen()
importClips()
prevObjects = []
while True:
    #haxx to ensure the TUIO message is fresh - sometimes it's not??
    for i in range(50):
        tracking.update()

    objects = sorted(tracking.objects(), key=lambda x: x.id)
    # update display whenever tracking changes
    if len(prevObjects) != len(objects):
        # clip or effect block added, re-load all videos
        print len(objects),'blocks found!'
        print 'blocks order:', [obj.id for obj in objects]
        initScreen()
        fetchClips(objects=objects)
        prevObjects = copy.deepcopy(objects)
    elif trackingChanged(prevObjects, objects):
        # same blocks but moved around, use cached images
        initScreen()
        fetchClips(objects=objects, updated=False)
        prevObjects = copy.deepcopy(objects)
    for event in pg.event.get():
        if event.type == pg.KEYDOWN:
            on_press(pg.key.name(event.key))

# all of our old key listener code lol
# listener = keyboard.Listener(
#         on_press=on_press,
#         on_release=on_release)
# listener.start()

# win = g.GraphWin("prototype", 500, 500)
# win.setBackground('black')
# win.bind_all("<Key>", on_press)
# g.root.mainloop()

