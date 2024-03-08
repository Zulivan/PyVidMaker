import os
import shutil
import configparser
import multiprocessing
from moviepy.editor import *
from core.image_utils import ModernTextClip
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip
from core import actor_background_generator, audio_generator, actions, gameplay_generator, utils, subtitles
import math
import time
import random

title = "result"

os.makedirs("results", exist_ok=True)
os.makedirs("temp", exist_ok=True)

config = configparser.ConfigParser()
config.read("config.ini", encoding="utf-8")

if config is None:
    raise Exception("config.ini not found")

def clean_story(story_file_path):
    with open(story_file_path, 'r', encoding="utf-8") as f:
        lines = f.readlines()
        lines = [line for line in lines if line.strip() != ""]

        lines = [line.replace("%", " pourcent") for line in lines]

        lines = [line.replace(" !", "!") for line in lines]
        lines = [line.replace(" ?", "?") for line in lines]
        lines = [line.replace(" .", ".") for line in lines]
        lines = [line.replace(" :", ":") for line in lines]


        with open(story_file_path, 'w', encoding="utf-8") as f:
            f.writelines(u"{}".format(line) for line in lines)

def make_video(story_file_path):
    print("Making video for "+story_file_path)
    global title
    with open(story_file_path, 'r', encoding="utf-8") as f:
        if len(f.readlines()) == 0:
            raise Exception(story_file_path+" is empty")

    clean_story(story_file_path)

    with open(story_file_path, 'r', encoding="utf-8") as f:

        lines = f.readlines()
        lines = [line for line in lines if line.strip() != ""]

        # Read first line
        first_line = lines[0].strip()

        # If first line contains CTX|
        if first_line.startswith("CTX|"):
            first_line = first_line.replace("CTX|", "").replace("\n", "")
            options = first_line.split("|")

            for opt in options:
                opt = opt.split(":")
                option = opt[0]
                value = opt[1]
            
                if option == "bg":
                    actor_background_generator.set_background(value)
                elif option == "title":
                    title = value
                elif option == "music":
                    audio_generator.set_music_path(value)
            lines.pop(0)

        if os.path.exists(os.path.join("results", title+".mp4")):
            print("Video already exists")
            if config.getboolean('General', 'debug') == False:
                f.close()
                shutil.rmtree('temp')
                shutil.move(story_file_path, os.path.join("results", os.path.basename(story_file_path)))
                # rename the file story filte to title.txt
                os.rename(os.path.join("results", os.path.basename(story_file_path)), os.path.join("results", title+".txt"))

            raise Exception("Video already exists")

        captions = audio_generator.render(lines)

        output_dir = 'temp/speeches'

        # If captions variable are not set or captions.txt is empty, then exit
        if captions is None or len(captions) == 0:
            with open(os.path.join(output_dir, "captions.txt"), "r", encoding="utf-8") as f:
                captions = eval(f.read())

        if captions is None or len(captions) == 0:
            raise Exception("FATAL: Captions are empty")

        # if actors background doesnt exist
        if os.path.exists(actor_background_generator.get_final_path()) == False:
            captions = actor_background_generator.render_composite_clip_from_captions(captions, lines)

        # Write captions to file
        with open(os.path.join(output_dir, "captions.txt"), "w", encoding="utf-8") as f:
            f.write(u"{}".format(captions))

        # if gameplay doesnt exist
        if config.getboolean("Video", "background_gameplay") and os.path.exists(gameplay_generator.get_gameplay_path()) == False:
            gameplay_generator.render_gameplay_video(audio_generator.get_final_audio_duration())

        output_dir = 'results'

        if len([f for f in os.listdir(output_dir) if os.path.isfile(os.path.join(output_dir, f)) and f == title+".mp4"]) == 0:
            print("Creating final video")
            compose_final_video(captions, lines)


def compose_final_video(captions, lines):
    global title
    temp_dir = 'temp'
    
    prefinal_video_path = os.path.join(temp_dir, "prefinal.mp4")
    prefinal_nosubs_video_path = os.path.join(temp_dir, "prefinal-nosubs.mp4")
    gwidth = config.getint('Video', 'width')
    gheight = config.getint('Video', 'height')

    if os.path.exists(prefinal_video_path) == False or os.path.exists(prefinal_nosubs_video_path) == False:
        gameplay = ColorClip((gwidth, gheight), color=(0, 0, 0)).set_duration(cvsecs(captions[-1][1][0][1]))
        if config.getboolean('Video', 'background_gameplay'):
            gameplay = VideoFileClip(gameplay_generator.get_gameplay_path())

        actors_video_clip = VideoFileClip(actor_background_generator.get_final_path()).set_position(("center", "top")).resize(width=gwidth)
        clips = [gameplay, actors_video_clip]

        if config.get('Video', 'add_bokeh_layer'):
            bokeh = VideoFileClip(os.path.join("assets", "bokeh.mp4")).set_position(("center", "center")).resize(width=gwidth).set_duration(gameplay.duration)
            bokeh = bokeh.fx(vfx.mask_color, color=[0, 0, 0], thr=1200, s=0.9)
            clips.append(bokeh)

        panorama_clips = actor_background_generator.get_panorama_clips(captions, lines)
        final_clip = CompositeVideoClip(clips + panorama_clips)
        final_clip = final_clip.set_audio(AudioFileClip(audio_generator.get_final_path()))
        
        utils.threaded_writefile(final_clip, prefinal_nosubs_video_path, 15)
        
        subtitles_position = actors_video_clip.h + config.getfloat("Subtitles", "position_offset")

        dynamic_subtitles_layer, dynamic_subtitles_layer_h = subtitles.dynamic_captions(captions, subtitles_position)

        # Setting up watermark
        watermark_position_y = config.get('General', 'watermark_position_y')
        
        watermark_position_x = config.get('General', 'watermark_position_x')

        if watermark_position_y.replace(".", "").isdigit():
            watermark_position_y = config.getfloat('General', 'watermark_position_y')
        elif watermark_position_y == "subtitles":
            watermark_position_y = subtitles_position + dynamic_subtitles_layer_h

        if watermark_position_x.replace(".", "").isdigit():
            watermark_position_x = config.getfloat('General', 'watermark_position_x')

        watermark_clip = ModernTextClip(config.get('General', 'watermark'), config.get("General", "watermark_font"), config.get("General", "watermark_size"), config.get("General", "watermark_color")).set_duration(gameplay.duration)
        watermark_clip = watermark_clip.set_position((watermark_position_x, watermark_position_y))
        watermark_clip = watermark_clip.set_opacity(config.getfloat("General", "watermark_opacity")).rotate(config.getfloat("General", "watermark_rotate"))

        # Render final video with assets
        final_clip = VideoFileClip(prefinal_nosubs_video_path)
        final_clip = CompositeVideoClip([final_clip, dynamic_subtitles_layer, watermark_clip])
       
        utils.threaded_writefile(final_clip, prefinal_video_path, 15)

    duration = VideoFileClip(actor_background_generator.get_final_path()).duration
    duration = duration - 0.2 if duration > 0.2 else duration

    ffmpeg_extract_subclip(prefinal_video_path, 0, duration, targetname=os.path.join("results", title+".mp4"))

    exit()

def run_story(path):
    """
    Select the oldest txt file in the defined path folder
    Then make a video from that script
    """

    if len(os.listdir(path)) == 0:
        raise Exception(f"FATAL ERROR : There is no story in folder: {path}")

    # Only list that files that are .txt
    story = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f)) and f.endswith(".txt")]

    # Sort them by date
    story = sorted(story, key=lambda x: os.path.getmtime(os.path.join(path, x)))[0]

    make_video(os.path.join(path, story))

# Read scripts from stories/to_run folder
run_story(os.path.join("stories", "to_run"))

#debug: show all fonts available for moviepy
#print(TextClip.list('font'))