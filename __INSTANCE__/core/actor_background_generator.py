import random
import math
import shutil
import configparser
import skimage
from moviepy.editor import *
from moviepy.video.fx.mirror_x import mirror_x
from gradio_client import Client
from . import actions, audio_generator, utils
from requests.exceptions import ConnectTimeout

config = configparser.ConfigParser()
config.read('config.ini')

output_dir = os.path.join(os.getcwd(), "temp")
assets_dir = os.path.join(os.getcwd(), "assets")
actors_dir = os.path.join(assets_dir, "actors")
bg_dir = os.path.join(assets_dir, "bg")
bg_dir = os.path.join(bg_dir, random.choice(os.listdir(bg_dir)))

def set_background(bg):
    global bg_dir
    bg_dir = os.path.join(assets_dir, "bg", bg)
    if not os.path.isdir(bg_dir):
        raise Exception("Background directory is not valid")

def get_final_path():
    return os.path.join(output_dir, "actors-video.mp4")

def get_actors_positions(i, actors, clip):
    num_actors = len(actors)

    resize_coefficient = 1 - num_actors * 0.05 - i * 0.03
    
    if num_actors <= 1:
        return clip.set_position(("center", "bottom")), 1

    width = 1080
    padding = 200 - (num_actors - 1) * 20

    clip = clip.set_position(("center", "bottom")).resize(resize_coefficient)

    placement_width = width - padding*2

    position = (i / (num_actors - 1)) * placement_width - clip.w / 2 + padding

    clip = clip.set_position((position, "bottom"))

    return (clip, position)

def tuple_to_dict(data_tuple):
    result_dict = {}
    key = 0
    for item in data_tuple:
        if isinstance(item, tuple):
            result_dict[key] = tuple_to_dict(item)
        else:
            result_dict[key] = item
        key += 1
    return result_dict

def dict_to_tuple(data_dict):
    result_list = []
    for key, value in data_dict.items():
        if isinstance(value, dict):
            result_list.append(dict_to_tuple(value))
        else:
            result_list.append(value)
    return tuple(result_list)


def animate_mouth(video_path, audio_path):
            audio_path = audio_generator.get_final_nomusic_path()
            
            try:
                client = Client(config.get('General', 'wav2lip_url'))
                result = client.predict(
                    video_path,	# str (filepath on your computer (or URL) of file) in 'Video or Image' File component
                    audio_path,	# str (filepath on your computer (or URL) of file) in 'Audio' File component
                    "wav2lip_gan",	# str  in 'Checkpoint' Radio component
                    True,	# bool  in 'No Smooth' Checkbox component
                    1,	# int | float (numeric value between 1 and 4) in 'Resize Factor' Slider component
                    0,	# int | float (numeric value between 0 and 50) in 'Pad Top' Slider component
                    20,	# int | float (numeric value between 0 and 50) in 'Pad Bottom (Often increasing this to 20 allows chin to be included' Slider component
                    0,	# int | float (numeric value between 0 and 50) in 'Pad Left' Slider component
                    0,	# int | float (numeric value between 0 and 50) in 'Pad Right' Slider component
                    fn_index=0
                )
            except ConnectTimeout as e:
                if os.path.exists(video_path):
                    os.remove(video_path)

                raise Exception("The wav2lip server is not responding. Please check if the server is running.")
            except Exception as e:
                if os.path.exists(video_path):
                    os.remove(video_path)

                raise Exception("Error in mouth animation:" + str(e))

            return result

def get_panorama_clips(captions, lines):
        panorama_clips = []

        for index, caption in enumerate(captions):
            composite_clip = None
            actor = caption[0]
            duration = caption[1][0][1] - caption[1][0][0]

            if index == len(captions) - 1:
                duration = duration + 1

            if actor == "PANORAMA":
                combine = len(lines) - len(captions)
                line = lines[index+combine]
                actionName = line.split("|")[1].replace("\n", "").strip().lower()
                params = line.split("|")[2:]
                params = [param.strip().replace("\n", "") for param in params]
                
                composite_clip, ct = actions.handle_clip_generation(actionName, duration, params)
                if composite_clip:
                    composite_clip = composite_clip.set_start(caption[1][0][0]-0.01) # .set_position(("center", "bottom"))
                    if composite_clip.duration > duration and composite_clip.duration >= 9999:
                        composite_clip = composite_clip.set_duration(captions[-1][1][0][1] - caption[1][0][0])

                        next_caption = None
                        for i in range(index+1, len(captions)):
                            if captions[i][0] == "PANORAMA":
                                next_caption = captions[i]
                                break
                        
                        if next_caption is not None:
                            composite_clip = composite_clip.set_duration(next_caption[1][0][0] - caption[1][0][0])
                    panorama_clips.append(composite_clip)
        
        return panorama_clips

def render_composite_clip_from_captions(captions, lines):
    upgraded_captions = tuple_to_dict(captions)

    if len([f for f in os.listdir(output_dir) if os.path.isfile(os.path.join(output_dir, f)) and f == "actors-video.mp4"]) == 0:
        
        # read through the captions and create the actors' compilation
        clips = []

        for index, caption in enumerate(captions):
            composite_clip = None

            # Get caption data
            actor = caption[0]
            behaviors = captions[index][2]

            # Get duration
            next_caption = captions[index+1] if index < len(captions) - 1 else None
            duration = caption[1][0][1] - caption[1][0][0]
            if next_caption is not None:
                duration = next_caption[1][0][0] - caption[1][0][0]

            # Some pieces of information are not available in caption data, reading from the script.txt file
            lineIndex = index + (len(lines) - len(captions))
            line = lines[lineIndex]

            # Adding a one frame 
            if index == len(captions) - 1:
                duration = duration + 1

            if actor == "ACTION" or actor == "PANORAMA":
                print('Custom action or panorama')
                params = line.split("|")[2:]
                params = [param.strip().replace("\n", "") for param in params]
                
                actionName = line.split("|")[1].replace("\n", "").strip().lower()

                try:
                    composite_clip, caption_text = actions.handle_clip_generation(actionName, duration, params, lineIndex)
                except Exception as e:
                    raise Exception(actionName + " FATAL ERROR: " + str(e))

                upgraded_captions[index][1][1] = caption_text
                print(upgraded_captions[index][1][1])

                if actor == "PANORAMA":
                    if len(clips) > 0:
                        clips[-1] = clips[-1].set_duration(duration + clips[-1].duration)
                        print('more duration for last clip')
                    continue
            else:
                duration += 1
                keepBackground = False
                if index > 0 and captions[index-1][0] == actor:
                    keepBackground = True
                
                print('Actor clip of ' + actor + ' ' + str(duration) + ' ' + str(keepBackground) + ' ' + str(behaviors))
                composite_clip = make_clip(actor, duration, keepBackground, behaviors, index)
                composite_clip = composite_clip.set_duration(duration)

            if composite_clip is None:
                print("No clip made for actor " + str(actor) + " with line " + str(line))
                composite_clip = ColorClip((1080, 1920), color=(0, 0, 0), ismask=True).set_duration(0)

            composite_clip = composite_clip.set_start(caption[1][0][0]).resize(width=1080)
            clips.append(composite_clip)

        clips = CompositeVideoClip(clips).set_duration(captions[-1][1][0][1]).resize(width=1080)

        actors_video_path = get_final_path()

        num_of_threads = math.ceil(clips.duration / 5)

        utils.threaded_writefile(clips, actors_video_path, num_of_threads)

        if config.getboolean('Video', 'animate_actors_mouth'):
            source_path = animate_mouth(actors_video_path, audio_generator.get_voice_path())
            if os.path.isfile(source_path):
                shutil.move(source_path, actors_video_path)


    return dict_to_tuple(upgraded_captions)

last_background = None

def blur(image):
    return skimage.filters.gaussian(image.astype(float), sigma=4)

def compile_image(clip):

    # render the clip as an image
    clip = clip.save_frame(os.path.join(output_dir, "temp.png"), t=0, withmask=True)

    #remove black background

    # load the image
    image = ImageClip(os.path.join(output_dir, "temp.png"))
    #add green screen
    image = image.on_color(size=(image.w, image.h), color=(0, 255, 0))

    return image


def get_random_background():
    global last_background
    global bg_dir

    bg_image = random.choice([f for f in os.listdir(bg_dir) if os.path.isfile(os.path.join(bg_dir, f)) and (f.endswith(".jpg") or f.endswith(".png"))])
    return bg_image

def resize_func(animation, t, duration, speed):
    size = 1

    animations = ["zoom-in", "zoom-out", "quick-zoom-in", "quick-zoom-out"]

    animation = animations[int(animation) - 1]

    if animation == "bounce":
    
        angle = 2.5 * math.pi * t * speed
        
        sine_value = math.sin(angle)

        size = 1 + sine_value * 0.01 + 0.01

    elif animation == "zoom-in":
        starting_size = 1
        final_size = 1.02
        speed = t / duration

        size = starting_size + (final_size - starting_size) * speed
    elif animation == "zoom-out":
        starting_size = 1.05
        final_size = 1
        speed = t / duration

        size = starting_size + (final_size - starting_size) * speed
    elif animation == "quick-zoom-in":
        starting_size = 1
        final_size = 1.1
        speed = (10 * t) / duration

        size = min(starting_size + (final_size - starting_size) * speed, final_size)
    elif animation == "quick-zoom-out":
        starting_size = 1.1
        final_size = 1
        speed = (10 * t) / duration

        size = max(starting_size + (final_size - starting_size) * speed, final_size)

    return size

def select_random_media(actors_dir, actor, media_list, behaviors):
    if isinstance(behaviors, list) and len(behaviors) > 0:
        behaviors = [behavior.replace(".", "") for behavior in behaviors]
        filtered_media = [item for item in media_list if any(behavior in item for behavior in behaviors)]
        if filtered_media:
            return os.path.join(actors_dir, actor, random.choice(filtered_media))
    
    if media_list:
        return os.path.join(actors_dir, actor, random.choice(media_list))
    
    return None

def make_clip(actors, d = 0, keepBackground=False, behaviors=[], index=0):
        global last_background
        global bg_dir
        d = d + 0.1
        duration = 999999
        clips = []
        
        if isinstance(behaviors, str):
            behaviors = [behaviors]
        if isinstance(actors, str):
            actors = [actors]

        bg_image = random.choice([f for f in os.listdir(bg_dir) if os.path.isfile(os.path.join(bg_dir, f)) and (f.endswith(".jpg") or f.endswith(".png"))])

        if keepBackground and last_background is not None:
            bg_image = last_background

        last_background = bg_image

        bg_clip = ImageClip(os.path.join(bg_dir, bg_image)).set_position(("center", "center"))
        bg_clip = bg_clip.set_duration(duration).resize(width=1080)

        for i, actor in enumerate(actors):

            actor_images = [f for f in os.listdir(os.path.join(actors_dir, actor)) if os.path.isfile(os.path.join(os.path.join(actors_dir, actor), f)) and f.endswith(".png")]
            actor_videos = [f for f in os.listdir(os.path.join(actors_dir, actor)) if os.path.isfile(os.path.join(os.path.join(actors_dir, actor), f)) and f.endswith(".mp4")]

            actor_image = None
            actor_video = None

            for behavior in behaviors:
                if os.path.isfile(behavior):
                    if behavior.endswith(".mp4"):
                        actor_video = behavior
                    elif behavior.endswith(".png"):
                        actor_image = behavior

            if actor_video is None and actor_videos:
                actor_video = select_random_media(actors_dir, actor, actor_videos, behaviors)

            if actor_image is None and actor_images:
                actor_image = select_random_media(actors_dir, actor, actor_images, behaviors)
 
            if actor_video is not None:
                actor_clip = VideoFileClip(actor_video).without_audio()
                # start at random time in the video and end at the end of clip

                start_time = random.uniform(0, actor_clip.duration - d)
                actor_clip = actor_clip.subclip(start_time, start_time + d)
                actor_clip = actor_clip.resize(height=bg_clip.h)
                actor_clip = actor_clip.set_position(("center", "bottom"))

                #actor_clip = actor_clip.fx(vfx.mask_color, color=[0,255,0], s=30, thr=50)
                clips.append((actor_clip, "center"))
            elif actor_image is not None:
                auto_rotate = len(actors) == 1 and d > 3
                auto_rotate_times = random.randint(2, int(int(d/2.6) + 2))
                auto_rotate_duration = d / (auto_rotate_times + 1)

                actor_clip = ImageClip(actor_image).set_duration(auto_rotate_duration if auto_rotate else duration)
                if random.choice([True, False]):
                    actor_clip = mirror_x(actor_clip, apply_to=["mask"])

                actor_clip, pos = get_actors_positions(i, actors, actor_clip)

                clips.append((actor_clip, pos))

                if auto_rotate:
                    for j in range(auto_rotate_times):
                        rot_duration_start = (j + 1) * auto_rotate_duration
                        rot_duration = auto_rotate_duration if j < auto_rotate_times - 1 else duration - rot_duration_start

                        actor_clip2 = actor_clip.copy().set_duration(rot_duration).set_start(rot_duration_start)
                        actor_clip2 = mirror_x(actor_clip2, apply_to=["mask"])
                        actor_clip2 = actor_clip2.resize(1+0.05*j)

                        clips.append((actor_clip2, pos))
            else:
                raise Exception("No image or video found for actor " + str(actor))


        #set the item in the middle of the array to the last one
        if len(clips) > 1:
            clips[1], clips[-1] = clips[-1], clips[1]

        iteration = 0
        for i, (clip, pos) in enumerate(clips):
            if config.getboolean('Video', 'animate_actors'):
                clipd = clip.duration

                if isinstance(clip, VideoClip):
                    # extend the last frame to the end of the clip
                    clip = clip.fx(vfx.freeze, t=clipd, freeze_duration=duration)

                # if clip is an image clip
                if isinstance(clip, ImageClip):
                    clip = compile_image(clip).set_start(clip.start).set_duration(clipd)
                    clip = clip.fx(vfx.mask_color, color=[0,255,0], s=30, thr=50)
                
                interval = config.getint('Video', 'animate_actors_interval')
    
                if interval != 0 and iteration % interval == 0:
                    speed = random.uniform(1, 2.7)
                    animation = random.randint(1, 4)

                    print("interval" + str(iteration) + " inv " +str(i%interval) + " speed " + str(speed) + " animation " + str(animation) + " duration " + str(clipd))

                    clip = clip.resize(lambda t : resize_func(animation, t, clipd, speed))
                
                clip = clip.set_position((pos, "bottom"))
                iteration += 1

            clips[i] = clip

        clips.insert(0, bg_clip)

        composite_clip = CompositeVideoClip(clips).set_duration(duration)

        return composite_clip