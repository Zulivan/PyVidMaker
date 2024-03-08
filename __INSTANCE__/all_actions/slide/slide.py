from core import actor_background_generator
import os
from moviepy.editor import *
from moviepy.video.fx.mirror_x import mirror_x
from pydub import AudioSegment

def get_filename(path):
    before_extension = path.split(".")[0]

    if "/" in before_extension:
        before_extension = before_extension.split("/")[-1]

    return before_extension

def get_audio_path(path):
    filetype = path.split(".")[-1]
    path = path

    if filetype == "mp4":
        clip = VideoFileClip(path)
        audio = clip.audio

        if audio is not None:
            wav_file = os.path.join("temp", get_filename(path) + ".wav")
            audio.write_audiofile(wav_file)

            speed_up = AudioSegment.from_wav(wav_file)
            speed_up = speed_up.speedup(playback_speed=1.3)
            speed_up.export(wav_file, format="wav")

            return wav_file
    elif filetype == "png" or filetype == "jpg":
        path = os.path.join("temp", "silent.wav")
        AudioSegment.silent(duration=1).export(path, format="wav")
        return path
    else:
        return path


def get_duration(params = []):
    filetype = params[0].split(".")[-1]
    imagepath = params[0]

    if filetype == "mp4":
        clip = VideoFileClip(imagepath)

        return clip.duration
    elif filetype == "png" or filetype == "jpg":
        clip = ImageClip(imagepath)

        return 0

def handle_audio_generation(params = [], index=0):
    print('Panorama ran! success')
    if(len(params) == 0):
        raise Exception("No params provided for audio generation")

    return get_audio_path(params[0])

def handle_clip_generation(d=0, params = [], index=0):
    print('Clip generation ran! success')
    #make an image clip or a video clip depending on params[0] file extension
    filetype = params[0].split(".")[-1]
    imagepath = params[0]
    clip = None

    if filetype == "mp4":
        clip = VideoFileClip(imagepath)
        clip = clip.fx(vfx.speedx, clip.duration / d)
        #.fx(vfx.fadein, 0.1).fx(vfx.fadeout, 0.2)

    elif filetype == "png" or filetype == "jpg":
        clip = ImageClip(imagepath).set_duration(2)

        clip = clip.resize(height=1920*1.2)

        width, height = clip.size
        print(width, height)

        clip = clip.resize(lambda t: 0.9 + 0.03 * t)
        # set position to slighly go from left to right
        clip = clip.set_position(lambda t: (max((-width / 2 - 300), (-width / 2 + 300 - 19 * t)), "center"))
        #clip = clip.set_position(lambda t: ((10 * t), "center"))

    return clip, ""