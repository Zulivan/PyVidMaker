from core import actor_background_generator, audio_generator
import os
import random
import shutil
# get unix current time
import time
import math
import wave
from pydub import AudioSegment


# Make two characters say the same sentence

def handle_audio_generation(params = [], index=0):
    if len(params) <= 2:
        raise Exception("FATAL DUO ACTION ERROR: We need at least two actors and one sentence to make them say the same thing.")

    actors = []
    sentence = ""

    #for each param value, we need to get the actor
    for param in params:
        if audio_generator.is_valid_actor(param):
            actors.append(param)
        else:
            sentence = param

    if len(actors) < 2:
        raise Exception("FATAL DUO ACTION ERROR: We need at least two actors")

    if sentence == "":
        raise Exception("FATAL DUO ACTION ERROR: We need a sentence to make them say the same thing.")
    
    print("Generating audio for duo action with actors: " + str(actors) + " saying sentence: " + sentence)

    rep = str(math.floor(time.time()))

    files = []

    for actor in actors:
        audio_file = audio_generator.tts(actor, sentence)
        npath = os.path.join("temp", "duo-"+rep+"-"+ actor + ".wav")
        shutil.move(audio_file, npath)
        files.append(npath)

    #order files by length
    files.sort(key=lambda f: wave.open(f,'r').getnframes(), reverse=True)
    
    wav = AudioSegment.from_wav(files[0])

    for i, file in enumerate(files):
        if i == len(files) - 1:
            break
        wav = wav.overlay(AudioSegment.from_wav(files[i+1],'r'), position=0)

    final_path = os.path.join("temp", "duo-"+rep+".wav")

    wav.export(final_path, format="wav")

    return final_path

def handle_clip_generation(d=0, params = [], index=0):
    actors = []
    sentence = ""
    print(params)
    for param in params:
        if audio_generator.is_valid_actor(param):
            actors.append(param)
        else:
            sentence = param

    return actor_background_generator.make_clip(actors, duration, False, ["smile"]), sentence