from playwright.sync_api import sync_playwright
from moviepy.editor import VideoFileClip, concatenate_videoclips, CompositeVideoClip, AudioFileClip, CompositeAudioClip
import threading
import os
import multiprocessing
import shutil
import time
import random
import math
import concurrent.futures
import numpy as np
from PIL import Image

def get_huggingface_replica(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        page.goto(url)
        page.wait_for_load_state("domcontentloaded")
        link_tag = None
        while not link_tag:
            link_tag = page.locator('link[href*="'+url+'/--replicas/"]')
            if link_tag:
                # Get the full href attribute of the <link> tag
                link_tag_href = link_tag.get_attribute("href")
                #keep the link but remove the file name
                link_tag_href = link_tag_href[:-10]
                browser.close()
                return link_tag_href
            page.wait_for_timeout(1000)

class VideoFileClipInstancer(VideoFileClip):
    def __init__(self, instance, video_clip, filename, has_mask=False,
                 audio=True, audio_buffersize=200000,
                 target_resolution=None, resize_algorithm='bicubic',
                 audio_fps=44100, audio_nbytes=2, verbose=False,
                 fps_source='tbr'):
    
        # Creating a copy of the filename with unique name to avoid conflicts
        instance_filename = filename.replace(".mp4", "-{instance}.mp4".format(instance=str(instance), timestamp=math.floor(time.time())))
        shutil.copyfile(filename, instance_filename)

        time.sleep(1)

        VideoFileClip.__init__(self, filename=instance_filename, has_mask=has_mask,
                 audio=audio, audio_buffersize=audio_buffersize,
                 target_resolution=target_resolution, resize_algorithm=resize_algorithm,
                 audio_fps=audio_fps, audio_nbytes=audio_nbytes, verbose=verbose,
                 fps_source=fps_source)
        
        self.duration = video_clip.duration
        self.end = video_clip.end
        self.fps = video_clip.fps
        self.size = video_clip.size
        self.rotation = video_clip.rotation
        self.mask = video_clip.mask
        self.audio = video_clip.audio
        self.pos = video_clip.pos

def is_image_corrupt(file_path):
    try:
        img = Image.open(file_path)
        img.verify()
        return False  # Image is not corrupt
    except (IOError, SyntaxError):
        return True   # Image is corrupt

def render_frame(subclip, index, t):
    i = int(t * subclip.fps)
    if os.path.exists("temp/chunk-{index}/{i}.png".format(index=index, i=i)):
        return

    subclip.save_frame("temp/chunk-{index}/{i}.png".format(index=index, i=i), t=t)

    while is_image_corrupt("temp/chunk-{index}/{i}.png".format(index=index, i=i)):
        print("Image is corrupt. Retrying...")
        subclip.save_frame("temp/chunk-{index}/{i}.png".format(index=index, i=i), t=t)

def list_of_frames_not_rendered(index, subclip):
    """
    Returns a list of frames that are not rendered yet in format [0, 1, 2, 3, 4, 5, 6, 7, 8, 9] etc.
    """
    return [i for i in range(int(subclip.duration * subclip.fps)) if not os.path.exists("temp/chunk-{index}/{i}.png".format(index=index, i=i))]


def render_frame_retry(subclip, index, num_frames, sub_threads):
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=sub_threads)
    try:
        # Use ThreadPoolExecutor to parallelize frame rendering
        futures = [executor.submit(render_frame, subclip, index, i) for i in np.arange(0, subclip.duration, 1.0 / subclip.fps)]

        # Wait for all threads to finish
        concurrent.futures.wait(futures)
    finally:
        # Explicitly shutdown the executor
        executor.shutdown()

def render_chunk(index, clip, path, start_time, end_time, num_process):
    first_run = True
    sub_threads = 10 # num_process
    while True:
        try:
            if first_run:
                if clip.audio is not None:
                    # Remove audio from clip
                    clip.audio = None

                # Create clones of videos to avoid conflicts
                if isinstance(clip, CompositeVideoClip):
                    # loop through all clips and create instances
                    for i in range(len(clip.clips)):
                        if isinstance(clip.clips[i], VideoFileClip):
                            filename = str(clip.clips[i].filename)
                            previous_instance = clip.clips[i]
                            print("Creating instance of {filename}".format(filename=filename))
                            clip.clips[i].close()
                            # Wait one second to avoid conflicts
                            time.sleep(1)
                            clip.clips[i] = VideoFileClipInstancer(index, previous_instance, filename)
                            print("Successfully created instance of {filename}".format(filename=clip.clips[i].filename))
            first_run = False
            # Extract the subclip
            subclip = clip.subclip(start_time, end_time)
            
            print("Rendering chunk {index}...".format(index=index))

            if not os.path.exists("temp/chunk-{index}".format(index=index)):
                os.makedirs("temp/chunk-{index}".format(index=index))

            while list_of_frames_not_rendered(index, subclip) != []:
                print("Some frames are missing. Retrying...")
                print("Progress {progress}%".format(progress=round(len([f for f in os.listdir("temp/chunk-{index}".format(index=index)) if os.path.isfile(os.path.join("temp/chunk-{index}".format(index=index), f))]) / (int(subclip.duration * subclip.fps)) * 100, 2)))
                
                render_frame_retry(subclip, index, int(subclip.duration * subclip.fps), sub_threads)

            print("All frames rendered successfully. Compiling video...")
            # Compile the frames into a video with ffmpeg
            os.system("ffmpeg -y -r {fps} -i temp/chunk-{index}/%d.png -c:v libx264 -vf fps={fps} -pix_fmt yuv420p -an {path}".format(fps=subclip.fps, index=index, path=path))

            # loop through all clips and close instances
            if isinstance(clip, CompositeVideoClip):
                for i in range(len(clip.clips)):
                    if isinstance(clip.clips[i], VideoFileClipInstancer):
                        print("Closing instance of {filename}".format(filename=clip.clips[i].filename))
                        clip.clips[i].close()
                        print("Seccessfully closed instance of {filename}".format(filename=clip.clips[i].filename))

            # Delete chunk folder
            shutil.rmtree("temp/chunk-{index}".format(index=index))

            break
        except BaseException as e:
            print("Error while rendering chunk {index}: {error}".format(index=index, error=str(e)))
            time.sleep(1)
            # Delete chunk if it exists
            if os.path.exists(path):
                os.remove(path)
            pass

def valid_video_file(filename):
    try:
        clip = VideoFileClip(filename)
        if clip.duration > 0.1:
            return True
        clip.close()
    except Exception as e:
        return False

def threaded_writefile(clip, clip_path, num_process=multiprocessing.cpu_count()):
    num_chunks = max(1, 1)
    # Calculate the duration of each chunk

    if num_chunks > 1:
        clip.fps = 30
        total_duration = clip.duration
        chunk_duration = total_duration / num_chunks

        print("Rendering {num_chunks} chunks of {chunk_duration} seconds each.".format(num_chunks=num_chunks, chunk_duration=chunk_duration))

        # Remove all chunk videos if they exist
        for i in range(num_chunks):
            if os.path.exists(f"temp/chunk-{i + 1}.mp4"):
                os.remove(f"temp/chunk-{i + 1}.mp4")

        while True:
            # Create threads for rendering chunks
            threads = []
            generated_chunks = []

            for i in range(num_chunks):
                if valid_video_file(f"temp/chunk-{i + 1}.mp4"):
                    continue
                start_time = i * chunk_duration
                end_time = (i + 1) * chunk_duration
                path = f"temp/chunk-{i + 1}.mp4"
                thread = threading.Thread(target=render_chunk, args=((i + 1), clip, path, start_time, end_time, num_process))
                threads.append(thread)

            for thread in threads:
                thread.start()

            for thread in threads:
                thread.join()

            for i in range(num_chunks):
                if valid_video_file(f"temp/chunk-{i + 1}.mp4"):
                    generated_chunks.append(f"temp/chunk-{i + 1}.mp4")

            # Check if all chunks were successfully rendered
            if len(generated_chunks) == num_chunks:
                print("All chunks rendered successfully.")
                break
            else:
                print("Some chunks failed. Retrying...")
                time.sleep(1)  # Add a delay before retrying
        
        # Concatenate the rendered chunks if needed
        final_clip = concatenate_videoclips([VideoFileClip(f"temp/chunk-{i + 1}.mp4") for i in range(num_chunks)])
        final_clip.write_videofile(clip_path,
                                    audio_codec="aac",
                                    codec="libx264",
                                    fps=30,
                                    audio_bitrate="192k",
                                    verbose=False,
                                    remove_temp=True,
                                    threads=multiprocessing.cpu_count(),
                                    logger=None,
                                    preset="medium")

        final_clip.close()
        time.sleep(1)
        for i in range(num_chunks):
            os.remove(f"temp/chunk-{i + 1}.mp4")
    else:
        clip.write_videofile(clip_path,
                                audio_codec="aac",
                                codec="libx264",
                                fps=30,
                                audio_bitrate="192k",
                                verbose=False,
                                remove_temp=True,
                                threads=multiprocessing.cpu_count(),
                                logger=None,
                                preset="medium")
        clip.close()

    return clip_path