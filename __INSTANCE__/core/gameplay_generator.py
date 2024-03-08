from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip
from moviepy.editor import *
import math
import random
import configparser
import multiprocessing
from . import actor_background_generator, audio_generator
import shutil

config = configparser.ConfigParser()
config.read('config.ini')

temp_dir = os.path.join(os.getcwd(), "temp")

def prepare_background(path, W: int, H: int) -> VideoFileClip:
    actors_clip = VideoFileClip(actor_background_generator.get_final_path()).resize(width=W)
    clip_height = H-actors_clip.h

    if clip_height <= 0:
        raise Exception("Background clip generation is pointless, because the actors clip is taking up the final video's whole height. Consider setting background_gameplay to false in the config.ini file.")

    clip = (
        VideoFileClip(path)
        .without_audio()
        .resize(height=clip_height)
    )

    bg_clip = ColorClip((1080, 1920), color=(0, 0, 255)).set_duration(clip.duration)

    clip = CompositeVideoClip([bg_clip, clip.set_position(("center", "bottom"))])

    # calculate the center of the background clip
    c = clip.w // 2

    # calculate the coordinates where to crop
    half_w = W // 2
    x1 = c - half_w
    x2 = c + half_w

    return clip.crop(x1=x1, y1=0, x2=x2, y2=H)

def render_gameplay_video(duration):

    gameplay_file = os.path.join("assets", "gameplay", random.choice(os.listdir(os.path.join("assets", "gameplay"))))

    gameplay = VideoFileClip(gameplay_file)

    end_time = math.floor(gameplay.duration-duration-5)
    start_time = random.randint(5, end_time)

    ffmpeg_extract_subclip(gameplay_file, start_time, start_time+math.floor(duration+1), targetname="temp/gameplay-temp.mp4")


    gameplay = prepare_background(os.path.join(temp_dir, "gameplay-temp.mp4"), 1080, 1920)

    fps = 1 if config.getboolean('General', 'debug') else 30

    gameplay.write_videofile(os.path.join(temp_dir, "gameplay.mp4"),
                audio_codec="aac",
                codec="libx264",
                fps=fps,
                audio_bitrate="192k",
                verbose=False,
                remove_temp=True,
                logger=None,
                threads=multiprocessing.cpu_count(),
                preset="ultrafast",)

    audio_path = audio_generator.get_final_nomusic_path()
    gameplay_path = os.path.join(temp_dir, "gameplay.mp4")

    if config.getboolean('Video', 'animate_background_mouth'):
        source_path = actor_background_generator.animate_mouth(gameplay_path, audio_path)
        if os.path.isfile(source_path):
            shutil.move(source_path, gameplay_path)


def get_gameplay_path():
    return os.path.join(temp_dir, "gameplay.mp4")