from core import actor_background_generator
import os
from moviepy.editor import *
from moviepy.video.fx.mirror_x import mirror_x
import math
import wave
from pydub import AudioSegment

def handle_audio_generation(params = [], index = 0):
    
    silence = AudioSegment.silent(duration=10)

    silence.export(os.path.join("temp", "blank.wav"), format="wav")

    return os.path.join("temp", "blank.wav")

def handle_clip_generation(d=0, params = [], index=0):
    clip = ColorClip((1920, 1080), (0, 0, 0), duration=d).set_opacity(0)

    return clip, ""