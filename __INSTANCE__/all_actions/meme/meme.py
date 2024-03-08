from core import actor_background_generator
import os
from moviepy.editor import *
from moviepy.video.fx.mirror_x import mirror_x
from pydub import AudioSegment

def handle_audio_generation(params = [], index=0):
    if(len(params) == 0):
        raise Exception("No params provided for audio generation")
    
    meme = params[0]

    delay = float(params[1]) if len(params) > 1 else 0.01

    memepath = os.path.join("actions", "meme", "lib", "{}.wav".format(meme.lower()))

    silence = AudioSegment.silent(duration=delay)
    silence.export(os.path.join("temp", "blank.wav"), format="wav")
    if not os.path.exists(memepath):
        return os.path.join("temp", "blank.wav")

    decreased_audio = AudioSegment.from_wav(memepath) - 5

    if(delay > 0):
        decreased_audio = AudioSegment.silent(duration=delay * 1000) + decreased_audio

    memepath = os.path.join("temp", "meme_{}.wav".format(index))
    decreased_audio.export(memepath, format="wav")

    return [silence, memepath]

def handle_clip_generation(d=0, params = [], index=0):
    clip = ColorClip((1920, 1080), (0, 0, 0), duration=d).set_opacity(0)

    return clip, ""