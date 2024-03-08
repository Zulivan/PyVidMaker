from pydub.silence import split_on_silence, detect_leading_silence
from pydub import AudioSegment, effects
from gradio_client import Client
from unidecode import unidecode
from . import actions
from .utils import get_huggingface_replica
import os
import re
import wave
import shutil
import random
import configparser
config = configparser.ConfigParser()
config.read('config.ini', encoding='utf-8')

output_dir = './temp/speeches'
bg_music_path = None

pronunciation_dict = {}

for key, value in config['Pronunciation'].items():
    pronunciation_dict[key] = value

if not os.path.exists(output_dir):
    os.makedirs(output_dir)

voice_generator_authorization = config.get('General', 'tts_service_approval')
voice_models = {}

options = config.options('VoiceModels')
for option in options:
    section, attribute = option.split('.')
    if section not in voice_models:
        voice_models[section] = {}
        voice_models[section]['boost'] = 0
    value = config.get('VoiceModels', option)
    result = None
    if value.lstrip('-').isdigit():
        result = int(value)
    else:
        try:
            result = float(value)
        except ValueError:
            result = str(value)
    voice_models[section][attribute] = result

voice_generator_url = None

def is_valid_actor(actor):
    global voice_models
    return actor in voice_models

def set_music_path(path):
    global bg_music_path
    bg_music_path = os.path.join("assets", "music", path)
    
    if os.path.isdir(bg_music_path):
        bg_music_path_dir = os.path.join("assets", "music", path)
        file = random.choice([f for f in os.listdir(bg_music_path_dir) if os.path.isfile(os.path.join(bg_music_path_dir, f)) and f.endswith(".mp3") and (f == f"0.mp3" or f.startswith(f"0-"))])
        bg_music_path = os.path.join("assets", "music", path, file)

def get_final_path():
    return os.path.join(output_dir, "final_bgm.wav")

def get_final_nomusic_path():
    return os.path.join(output_dir, "final.wav")

def get_voice_path():
    return os.path.join(output_dir, "voice_channel.wav")

def get_sound_path():
    return os.path.join(output_dir, "action_channel.wav")

def get_final_audio_duration():
    with wave.open(get_final_path()) as mywav:
        framerate = mywav.getframerate()
        frames = mywav.getnframes()
        duration = frames / float(framerate)
        return duration

def render(lines):
    render_audio(lines)

    captions = render_combined_audio(lines)

    render_music_background()

    match_audio_effects()

    return captions

def render_combined_audio(lines):
        captions = []
        voice_channel = AudioSegment.empty()
        sound_channel = AudioSegment.empty()
        combined_wav = AudioSegment.empty()
        wav_duration = -0.01
        i = 0
        if len([f for f in os.listdir(output_dir) if os.path.isfile(os.path.join(output_dir, f)) and f == "final.wav"]) == 0 or len([f for f in os.listdir(output_dir) if os.path.isfile(os.path.join(output_dir, f)) and f == "captions.txt"]) == 0:
            for wav_file in sorted([f for f in os.listdir(output_dir) if f.endswith(".wav") and "_main_" in f], key=lambda x: int(x.split("_")[0]) if x.split("_")[0].isdigit() else float('inf')):
                i += 1
                data = lines[int(wav_file.split("_")[0])].split("|")
                actor = data[0]
                text = data[1]

                wav_file_path = os.path.join(output_dir, wav_file)

                behavior = []
                
                if i == len([f for f in os.listdir(output_dir) if f.endswith(".wav")]):
                    proc = AudioSegment.from_wav(wav_file_path) + AudioSegment.silent(duration=100)
                    proc.export(wav_file_path, format="wav")

                with wave.open(wav_file_path) as mywav:
                    framerate = mywav.getframerate()
                    frames = mywav.getnframes()
                    duration = float(frames / float(framerate))

                # Upgrade captions
                if actor == "ACTION" or actor == "PANORAMA":
                    text = ""
                elif len(data) == 3:
                    # Set the behavior so that actor image can be changed accordingly
                    behavior = [data[2].strip()]

                if config.getboolean('Subtitles', 'strip_accents'):
                    text = unidecode(text)

                # Seperate voice and sound channels for post processing
                if actor == "ACTION" or actor == "PANORAMA":
                    sound_channel += AudioSegment.from_wav(wav_file_path)
                    voice_channel += AudioSegment.silent(duration=duration*1000)
                else:
                    sound_channel += AudioSegment.silent(duration=duration*1000)
                    voice_channel += AudioSegment.from_wav(wav_file_path)

                # Combine all the wav files into one final wav file
                # Add 0.01 seconds to the duration to avoid overlapping
                # Writing the captions to a file
                duration_added = wav_duration+duration
                captions.append((actor, ((wav_duration+0.01, duration_added), text), behavior))
                wav_duration = duration_added
                combined_wav += AudioSegment.from_wav(wav_file_path)

                with open(os.path.join(output_dir, "captions.txt"), "w", encoding='utf-8') as f:
                    f.write(u""+str(captions))

                if config.getboolean('General', 'debug'):
                    print("Combined wav duration: " + str(wav_duration))

            # add background overlay
            print("Adding background sounds...")

            for wav_file in sorted([f for f in os.listdir(output_dir) if f.endswith(".wav") and "_background_" in f], key=lambda x: int(x.split("_")[0]) if x.split("_")[0].isdigit() else float('inf')):
                # find a wave file that starts with the same index as the current one and is named "background"
                # if it exists, add it to the combined wav file
                wav_pos = int(wav_file.split("_")[0])
                wav_start = captions[wav_pos][1][0][1]

                wav_start = round(wav_start, 2)
                
                background_wav_file = AudioSegment.from_wav(os.path.join(output_dir, wav_file))
                background_wav_file = AudioSegment.silent(duration=wav_start*1000) + background_wav_file
                
                combined_wav = combined_wav.overlay(background_wav_file)
                
            combined_wav.export(os.path.join(output_dir, f"final.wav"), format="wav")
            voice_channel.export(os.path.join(output_dir, f"voice_channel.wav"), format="wav")
            sound_channel.export(os.path.join(output_dir, f"action_channel.wav"), format="wav")


def render_music_background():
    global bg_music_path
    if bg_music_path is None or not os.path.exists(bg_music_path) or not config.getboolean('Audio', 'enable_background_music'):
        #Make a silent audio file
        silence = AudioSegment.silent(duration=1000)
        silence.export(os.path.join(output_dir, f"bgm_edit.wav"), format="wav")
        return False
    else:

        # Reading captions of the audio for time stamps
        captions = []
        with open(os.path.join(output_dir, "captions.txt"), "r", encoding='utf-8') as f:
            captions = eval(f.read())

        # Get the audio parameters generated by the actions to match the background music
        audio_params = []
        for index, caption in enumerate(captions):
            path = os.path.join(output_dir, f"{index}_audio_params.txt")
            if os.path.exists(path):
                with open(path, "r", encoding='utf-8') as f:
                    audio_params.append(f.read().split("|"))
            else:
                audio_params.append([])
        
        bgm = AudioSegment.from_file(bg_music_path, format="mp3")
        bgm_followup = bgm
        increase = 0

        for i, caption in enumerate(captions):
            params = audio_params[i]
            start_time = caption[1][0][0]
            end_time = caption[1][0][1]
            silence = AudioSegment.silent(duration=(end_time-start_time)*1000)

            if "pause" in params:
                bgm = bgm[:start_time*1000] + silence + bgm_followup
            
            if "increase" in params or "intensify" in params:
                bg_music_path_dir = os.path.dirname(bg_music_path)
                
                increase += 1

                files = [f for f in os.listdir(bg_music_path_dir) if os.path.isfile(os.path.join(bg_music_path_dir, f)) and f.endswith(".mp3") and (f == f"{increase}.mp3" or f.startswith(f"{increase}-"))]

                if len(files) > 0:

                    increase_path = os.path.join(bg_music_path_dir, random.choice(files))

                    if os.path.exists(increase_path):
                        bgm_followup = AudioSegment.from_file(increase_path, format="mp3")

                        bgm = bgm[:end_time*1000] + bgm_followup
                else:
                    increase -= 1

            if "decrease" in params or "reduce" in params:
                bg_music_path_dir = os.path.dirname(bg_music_path)
                
                increase -= 1

                files = [f for f in os.listdir(bg_music_path_dir) if os.path.isfile(os.path.join(bg_music_path_dir, f)) and f.endswith(".mp3") and (f == f"{increase}.mp3" or f.startswith(f"{increase}-"))]

                if len(files) > 0:

                    increase_path = os.path.join(bg_music_path_dir, random.choice(files))

                    if os.path.exists(increase_path):
                        bgm_followup = AudioSegment.from_file(increase_path, format="mp3")

                        bgm = bgm[:end_time*1000] + bgm_followup
                else:
                    increase += 1
    
        bgm.export(os.path.join(output_dir, f"bgm_edit.wav"), format="wav")


def match_audio_effects():
    global bg_music_path
    if len([f for f in os.listdir(output_dir) if os.path.isfile(os.path.join(output_dir, f)) and f == "final_bgm.wav"]) > 0:
        return
    
    if config.getboolean('Audio', 'enable_background_music'):
        print("Rendering voices with music background...")
                
        bgm = AudioSegment.from_file(os.path.join(output_dir, f"bgm_edit.wav"), format="wav")
        bgm = bgm - 9

        speeches = AudioSegment.from_file(os.path.join(output_dir, f"final.wav"), format="wav")


        overlay = speeches.overlay(bgm, position=0)
        overlay.export(os.path.join(output_dir, f"final_bgm.wav"), format="wav")
    else:
        print("Rendering voices without music background...")
        speeches = AudioSegment.from_file(os.path.join(output_dir, f"final.wav"), format="wav")
        speeches.export(os.path.join(output_dir, f"final_bgm.wav"), format="wav")

    if config.getboolean('Audio', 'enable_hook'):
        hook = AudioSegment.from_file(os.path.join("core", "hooks", random.choice(os.listdir(os.path.join("core", "hooks")))), format="wav")
        hook = hook - 7

        speeches = AudioSegment.from_file(os.path.join(output_dir, f"final_bgm.wav"), format="wav")
        overlay = speeches.overlay(hook, position=0)
        overlay.export(os.path.join(output_dir, f"final_bgm.wav"), format="wav")


def render_audio(lines):
    os.makedirs(output_dir, exist_ok=True)
    for index, line in enumerate(lines):
            if len([f for f in os.listdir(output_dir) if os.path.isfile(os.path.join(output_dir, f)) and f.startswith(f"{str(index)}_")]) > 0:
                continue
            actor = line.strip().split("|")[0]
            text = line.strip().split("|")[1]
            result = None
            ap = None
            wav_files = []
            if actor == "ACTION" or actor == "PANORAMA":
                # Identify the action and call the appropriate function
                actionName = text.lower()
                params = line.strip().split("|")[2:]

                if len(params) == 0:
                    print("Handling action: " + actionName +" without params")
                
                result = actions.handle_audio_generation(actionName, params, index)

                if isinstance(result, tuple):
                    result, ap = result
                
                if isinstance(result, str):
                    result = [result]

                if result == None:
                    print("Action not found: " + actionName)
                    raise Exception("Action not found: " + actionName)
    
                for wav_file in result:
                    if isinstance(wav_file, AudioSegment):
                        # Fall back if the action unexpectedly returns an AudioSegment instead of a file path
                        # Consider rendering the audio segment to a file before finishing action
                        wav_file.export(os.path.join(output_dir, f"unexpected_audio_segment.wav"), format="wav")
                        wav_file = os.path.join(output_dir, f"unexpected_audio_segment.wav")

                    file_name = f"audio_{os.path.basename(wav_file)}"
                    file_path = os.path.join(output_dir, file_name)

                    shutil.copy(wav_file, file_path)
                    
                    wav_files.append(file_path)

            else:
                custom_audio = os.path.join("stories", "to_run")
                if os.path.isfile(os.path.join(custom_audio, f"{index}.wav")):
                    custom_audio = os.path.join(custom_audio, f"{index}.wav")
                else:
                    custom_audio = ""
                wav_files = [tts(actor, text, custom_audio)]
            
            for i_wf, wav_file in enumerate(wav_files):
                specs = ["main", "background"]

                wav_type = specs[i_wf] if i_wf < len(specs) else "main"

                wav_filename = f"{index}_{actor}_{wav_type}_{os.path.basename(wav_file)}"

                if wav_type == "main":
                    segment = AudioSegment.from_wav(wav_file)

                    normalized_segment = effects.normalize(segment)
                    normalized_segment.export(wav_file, format="wav")

                shutil.move(wav_file, os.path.join(output_dir, wav_filename))

            audio_params = []

            if ap != None:
                ap = ap.lower()
                if len(ap.split("|")) == 0:
                    ap = [ap]
                else:
                    ap = ap.split("|")
                audio_params = ap

            if len(audio_params) > 0:
                with open(os.path.join(output_dir, f"{index}_audio_params.txt"), "w", encoding="utf-8") as f:
                    f.write(u"|".join(audio_params))

            print(f"[\r{index+1}/{len(lines)}] Downloading all MP3 files...")
    return True

def remove_silence(wav_file_path):
    # Read the wav file
    sound = AudioSegment.from_wav(wav_file_path)

    # Split track where the silence is 2 seconds or more and get chunks
    chunks = split_on_silence(sound, min_silence_len=200, silence_thresh=-40)

    silence_removed = chunks[0]
    for segment in chunks[1:]:
        silence_removed += segment

    silence_removed.export(wav_file_path, bitrate='192k', format="wav")

def is_ipaddr(chaine):
    # Expression régulière pour détecter une adresse IP
    pattern = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')

    # Chercher les correspondances dans la chaîne
    resultats = re.findall(pattern, chaine)

    if resultats:
        return True
    else:
        if not "hf.space" in chaine:
            return True

        return False

def tts(actor, text = "error", custom_audio = ""):
    global voice_models
    global voice_generator_url
    global voice_generator_authorization

    # The actor given as parameter is not fully correct, we need to find the closest one
    if actor not in voice_models:
        raise Exception(f"Actor {actor} not found in the voice models list in config.ini")

    if voice_generator_url == None:
        if is_ipaddr(config.get('General', 'tts_service_url')):
            voice_generator_url = config.get('General', 'tts_service_url')
        else:
            voice_generator_url = get_huggingface_replica(config.get('General', 'tts_service_url'))

    current_model = voice_models[actor]

    for word in pronunciation_dict:
        text = text.lower().replace(word, pronunciation_dict[word])

    client = Client(voice_generator_url)
    result = client.predict(
            current_model['actor'],	
            current_model['speed'],	
            text,
            current_model['tts_voice'],
            current_model['tune'],
            "rmvpe",
            current_model['index_rate'],
            current_model['protect'],
            custom_audio,
            voice_generator_authorization,
            fn_index=0
    )

    # Destination directory is the current working directory
    destination_directory = '.'

    # Skip the first member of the array starting with "Success"
    result = result[1:]

    destination_path = None

    # Copy the last two items from the result
    for source_path in result[-2:]:
        if os.path.isfile(source_path):
            # Get the file name from the source path
            file_name = os.path.basename(source_path)
            
            # Create the destination path by joining the current directory and the file name
            destination_path = os.path.join(destination_directory, file_name)
            
            shutil.copy(source_path, destination_path)

            if destination_path.endswith(".wav"):
                remove_silence(source_path)

                trim_leading_silence = lambda x: x[detect_leading_silence(x) :]
                trim_trailing_silence = lambda x: trim_leading_silence(x.reverse()).reverse()
                strip_silence = lambda x: trim_trailing_silence(trim_leading_silence(x))

                combined_wav = AudioSegment.from_wav(source_path)

                stipped_audio = strip_silence(combined_wav)

                stipped_audio = stipped_audio + current_model['boost']

                stipped_audio.export(destination_path, format="wav")

    # Return the files copied
    return destination_path

