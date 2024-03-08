from core import actor_background_generator, audio_generator
import os
import random
import shutil
import time
import math
import wave
from pydub import AudioSegment
import time

def sortByAudioLength(files):
    try:
        files.sort(key=lambda f: wave.open(f,'r').getnframes(), reverse=False)
    except:
        time.sleep(1)
        return sortByAudioLength(files)

    return files

def handle_audio_generation(params = [], index=0):
    if len(params) == 0:
        raise Exception("FATAL LAUGH ACTION ERROR: We need at least an actor to perform the action")

    laughter_files = [f for f in os.listdir(os.path.join("actions", "laugh", "laughters")) if f.endswith(".wav")]
    files = [os.path.join("actions", "laugh", "init.wav")]

    actors = []
    default_laughter = random.choice(laughter_files)
    for param in params:
        if audio_generator.is_valid_actor(param):
            actors.append(param)
        else:
            default_laughter = param + ".wav"

    # loop through each actor and get their audio
    for actor in actors:
        audio_file = os.path.join("actions", "laugh", "laughters", default_laughter)

        if os.path.exists(audio_file) == False:
            default_laughter = random.choice(laughter_files)
            audio_file = os.path.join("actions", "laugh", "laughters", default_laughter)

        files.append(audio_file)
        laughter_files.remove(default_laughter)
        default_laughter = random.choice(laughter_files)

    for file in files:
        try:
            wave.open(file,'r').getnframes()
        except:
            print("FILE MIGHT BE IN USE OR CORRUPT: " + file)
            return handle_audio_generation(params, index)

    files = sortByAudioLength(files)
    
    wav = AudioSegment.from_wav(files[0])

    rep = str(index)
    for i, file in enumerate(files):
        if i == len(files) - 1:
            break
        wav = wav.overlay(AudioSegment.from_wav(files[i+1],'r'), position=0)

    final_path = os.path.join("temp", "laugh-"+rep+".wav")

    wav.export(final_path, format="wav")

    audio_param = random.choice(["pause", ""])
    return final_path, audio_param

def handle_clip_generation(d=0, params = [], index=0):
    actors = []
    #print(params)
    for param in params:
        if audio_generator.is_valid_actor(param):
            actors.append(param)

    return actor_background_generator.make_clip(actors, d, False, ["laugh"]), ""