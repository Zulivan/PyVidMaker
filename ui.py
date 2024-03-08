import gradio as gr
import subprocess
import importlib
import smtplib
import random
import time
import sys
import os
import re
from threading import Thread
from queue import Queue, Empty
from shutil import copytree, copy, rmtree, move
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
load_dotenv()

os.makedirs("generators", exist_ok=True)

generators = os.listdir("./generators")
actors_bg_path = os.path.join("assets", "bg")
actors_path = os.path.join("assets", "actors")
music_path = os.path.join("assets", "music")
actions_path = os.path.join("actions")

transformers = {}
for generator in generators:
    generator_path = os.path.abspath(os.path.join("./generators/", generator))
    transformer_path = os.path.join(generator_path, "transformer.py")
    if os.path.exists(transformer_path):
        sys.path.append(generator_path)

        spec = importlib.util.spec_from_file_location("transformer", transformer_path)
        tr = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(tr)

        transformers[generator] = tr

        sys.path.remove(generator_path)

rmtree("__ui_runners__", ignore_errors=True)
os.makedirs("__ui_runners__", exist_ok=True)

def send_email_notification(receiver, subject, content):
    """Send email notification to the receiver."""
    
    receiver = receiver if isinstance(receiver, str) and "@" in receiver else os.getenv("SMTP_RECEIVER")
    # Gmail SMTP server configuration
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = os.getenv("SMTP_PORT")
    smtp_username = os.getenv("SMTP_SENDER")
    smtp_password = os.getenv("SMTP_PASSWORD")

    message = MIMEMultipart()
    message['From'] = smtp_username
    message['To'] = receiver
    message['Subject'] = subject
    message['X-Priority'] = '2'

    message.attach(MIMEText(content, 'plain'))

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.sendmail(smtp_username, receiver, message.as_string())

    print("Email sent successfully!")

def split_text_into_lines(sentences=[], max_line_length=250):
    lines = []

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        # Split the sentence at commas
        parts = sentence.split(',')

        current_line = ""
        for part in parts:
            if not part:
                continue

            if len(current_line) + len(part) <= max_line_length:
                # Add the part to the current line if it fits
                if current_line:
                    current_line += "," + part
                else:
                    current_line += part
            else:
                # Start a new line if adding the part exceeds the max_line_length
                lines.append(current_line)
                current_line = part

        # Add the last line
        if current_line:
            lines.append(current_line)

    return lines


def split_sentence(sentence):
    # Define the pointer characters
    pointer = r"[.!?]"

    # Use re.split to split the sentence based on the pointer characters
    sentences = re.split(f'({pointer})', sentence)

    # Combine each pair of sentence and punctuation mark
    result = ["".join(pair).strip() for pair in zip(sentences[0::2], sentences[1::2])]

    # Check if there's a remaining portion after the last punctuation mark
    if sentences[-1]:
        result.append(sentences[-1].strip())

    # If length of each sentence is 2 or less, combine it with the previous sentence
    for i in range(len(result) - 1, 0, -1):
        if len(result[i]) <= 2:
            result[i - 1] += result[i]
            result.pop(i)

    # remove space before punctuation
    result = [re.sub(r'\s+([.!?])', r'\1', s) for s in result]

    # remove period or : from the end of the sentence
    result = [re.sub(r'([.:])$', '', s) for s in result]

    # remove html tags
    result = [re.sub(r'<[^>]*>', '', s) for s in result]

    # remove empty lines
    result = [s for s in result if s != ""]

    result = split_text_into_lines(result)

    return result

def levenshtein_distance(s1, s2):
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]

def custom_close_matches(word, possibilities):
    closest_word = min(possibilities, key=lambda x: levenshtein_distance(word, x))
    return closest_word

def check_text(text):
    # Check if text does not contain a period and is not equal to "__pycache__"
    if '.' not in text and text != "__pycache__":
        return True
    else:
        return False

def remove_punctuation(text):
    """
    Removes punctuation from text, commas, periods, exclamation marks, question marks, colons, semi-colons, and hyphens
    
    """
    return re.sub(r'[^\w\s]','',text)

def sanitize_script(generator, script, actors_bg, music_bg, video_title, files):
    #loop through each line
    result = []
    script = script.split("\n")
    error_count = 0
    time_estimate = 0

    generator_path = os.path.join("./generators/", generator)

    actors_bg_list = [file for file in os.listdir(os.path.join(generator_path, actors_bg_path)) if check_text(file)]
    actors_list = [file for file in os.listdir(os.path.join(generator_path, actors_path)) if check_text(file)]
    actions_list = [file for file in os.listdir(os.path.join(generator_path, actions_path)) if check_text(file)]
    music_bg_list = os.listdir(os.path.join(generator_path, music_path))

    if actors_bg is not None and music_bg is not None and video_title != "":
        video_title = video_title.replace(":", "_")
        video_title = video_title.replace("|", "_")

        result.append("CTX|bg:{actors_bg}|music:{music_bg}|title:{title}".format(actors_bg=actors_bg_list[actors_bg], title=video_title, music_bg=music_bg_list[music_bg]))

    for lineid, line in enumerate(script):
        if line == "" or "CTX" in line:
            continue
        lines_out = []
        error = ""
        line = line.replace("[", "|").replace("]", "|")
        if "|" in line:
            action_actor = line.split("|")[0].strip()
            identifier = line.split("|")[1].strip()
            if action_actor == "ACTION" or action_actor == "PANORAMA":
                if identifier not in actions_list:
                    error = "Action/panorama not found: "+identifier+", Refer to the list of actions/panoramas available"
                else:
                    action_folder = os.path.join(generator_path, actions_path, identifier)
                    action_file = [file for file in os.listdir(action_folder) if file.endswith(".py")][0]
                    
                    # read the file and store lines starting with "from core" in a list and remove them
                    with open(os.path.join(action_folder, action_file), "r", encoding="utf-8") as f:
                        content = f.read()
                        f.close()
                    lines = content.split("\n")
                    core_lines = []
                    for idx, ln in enumerate(lines):
                        if "from core" in ln:
                            core_lines.append(ln)
                            lines[idx] = ""
                    content = "\n".join(lines)
                    with open(os.path.join(action_folder, action_file), "w", encoding="utf-8") as f:
                        f.write(content)
                        f.close()

                    sys.path.append(action_folder)
                    try:
                        action_import = __import__(action_file.split(".")[0])

                        if hasattr(action_import, "run_validator"):
                            try:
                                params = line.split("|")[2:] if len(line.split("|")) > 2 else []
                                rv = action_import.run_validator(params, actors_list)
                            except Exception as e:
                                error = str(e)
                    except Exception as e:
                        error = "Interal error, see console output for more details"
                        print("Error while importing action/panorama: {}".format(e))
                    sys.path.remove(action_folder)

                    # Restore core lines
                    with open(os.path.join(action_folder, action_file), "r", encoding="utf-8") as f:
                        content = f.read()
                        f.close()
                    lines = content.split("\n")
                    for idx, ln in enumerate(lines):
                        if ln == "" and len(core_lines) > 0:
                            lines[idx] = core_lines.pop(0)
                    content = "\n".join(lines)
                    with open(os.path.join(action_folder, action_file), "w", encoding="utf-8") as f:
                        f.write(content)
                        f.close()

                    time_estimate += 0.5
            else:
                action_actor = action_actor.lower()
                if action_actor not in actors_list:
                    if custom_close_matches(action_actor, actors_list) != "":
                        error = "Actor not found: "+action_actor+". Did you mean "+custom_close_matches(action_actor, actors_list)+"?"
                    else:
                        error = "Actor not found: "+action_actor+", Refer to the list of actors available"
                elif action_actor in actors_list:
                    emotion = line.split("|")[2].strip() if len(line.split("|")) > 2 else "neutral"

                    if identifier == "":
                        error = "Text to read must be added after actor name"

                    time_estimate += len(identifier.split(" ")) * 0.21

                    lines = split_sentence(identifier)

                    for l in lines:
                        error = ""
                        if len(l) > 255:
                            error = "Line too long:" + str(len(l)) + " > 255 characters"

                        lines_out.append(action_actor+"|"+l+"|"+emotion+"    [ERROR: "+error+"]" if error else action_actor+"|"+l+"|"+emotion)
                        
        else:
            continue

        error_count += 1 if error else 0

        if lines_out == []:
            result.append(line+"    [ERROR: "+error+"]" if error else line)
        else:
            result.extend(lines_out)

    result = (["[ERROR: "+str(error_count)+" errors found in the script]"] + result) if error_count > 0 else result
    return result, error_count, time_estimate

def check_script(generator, script, actors_bg, music_bg, video_title, files):
    result, error_count, time_estimate = sanitize_script(generator, script, actors_bg, music_bg, video_title, files)
    generator_path = os.path.join("./generators/", generator)

    transformer_path = os.path.join(generator_path, "transformer.py")

    if error_count == 0 and os.path.exists(transformer_path):
        transformer = transformers[generator]

        try:
            result = transformer.apply_transformations(result, files) 
        except Exception as e:
            raise Exception("apply_transformations function not found in transformer.py")

        result, error_count, time_estimate = sanitize_script(generator, "\n".join(result), actors_bg, music_bg, video_title, files)
    
    result = "\n".join(result)

    return result, "{} seconds".format(round(time_estimate, 2)), gr.update(interactive=(error_count == 0 and time_estimate > 1))

def use_ai(generator, script, video_title, ai_params):
    print("Using AI to generate script for {}".format(generator))
    generator_path = os.path.abspath(os.path.join("./generators/", generator))
    transformer_path = os.path.join(generator_path, "transformer.py")

    ai_params = list(filter(lambda x: x != "", ai_params.split("|")))

    result = script
    images = []
    title = video_title

    if os.path.exists(transformer_path):

        transformer = transformers[generator]

        result = transformer.generate_script(ai_params)  
        try: 
            if isinstance(result, tuple):
                images, result, title = result
        except Exception as e:
            images, result = result
    
    return title, images, result


with gr.Blocks(title="Video generator") as demo:

    md = gr.Markdown(
        """
        # Select a generator and write a script to generate a video
        """)
    
    email_input = gr.Textbox(label="Email notification", lines=1, placeholder="Email address", info="Enter your email address to receive a notification when your video is ready", value="")

    for generator in generators:
        print(generator)
        generator_path = os.path.join("./generators/", generator)

        actors_bg_list = [file for file in os.listdir(os.path.join(generator_path, actors_bg_path)) if check_text(file)]
        actors_list = [file for file in os.listdir(os.path.join(generator_path, actors_path)) if check_text(file)]
        actions_list = [file for file in os.listdir(os.path.join(generator_path, actions_path)) if check_text(file)]
        music_bg_list = os.listdir(os.path.join(generator_path, music_path))
        transformer_path = os.path.join(generator_path, "transformer.py")
        with gr.Tab(generator):
            with gr.Row():
                config_file = gr.File(
                    label="Custom config file",
                    file_count="single",
                    value=os.path.join(generator_path, "config.ini"),
                    file_types=["ini"],
                )
            with gr.Row():
                images = gr.File(
                    label="Suggested images",
                    file_count="multiple",
                    file_types=["png", "jpg", "jpeg", "gif"],
                )
            with gr.Row():
                generator_in = gr.Textbox(label="Generator name (identical to the generator's folder name)", visible=False, lines=1, placeholder="Generator name", info="Name of the generator to use", value=generator)
                actors_bg = gr.Dropdown(label="Actors background", choices=actors_bg_list, type="index", info="Background behind the actors' images", value=0, allow_custom_value=True)
                music_bg = gr.Dropdown(label="Background music", choices=music_bg_list, type="index", info="Music being played in the background", value=0, allow_custom_value=True)
                video_title = gr.Textbox(
                    label="Video title",
                    info="Name of the video file after generation",
                    lines=1,
                    placeholder="A new video with a unique name",
                    value="result"
                )
            with gr.Accordion(open=False, label="See actors and actions/panoramas available"):
                actor_dataset = gr.Dataset(components=[gr.Textbox(visible=False)],
                    label="Actors available",
                    samples=[[actor] for actor in actors_list],
                    samples_per_page=20
                )
                action_dataset = gr.Dataset(components=[gr.Textbox(visible=False)],
                    label="Actions available",
                    samples=[["ACTION|" + action] for action in actions_list],
                    samples_per_page=20
                )
                panorama_dataset = gr.Dataset(components=[gr.Textbox(visible=False)],
                    label="Panoramas available",
                    samples=[["PANORAMA|" + panorama] for panorama in actions_list],
                    samples_per_page=20
                )
            with gr.Row():
                with gr.Column():

                    script = gr.Textbox(
                        label="Script",
                        info="Enter your script here and verify it",
                        lines=3,
                        placeholder="""
                        actor_name|speech|image_emotion
                        PANORAMA|action_name|param1|param2
                        actor_name|speech|image_emotion
                        actor_name|speech|image_emotion
                        ACTION|action_name|param1|param2|param3|param4
                        actor_name|speech|image_emotion
                        actor_name|speech|image_emotion
                        PANORAMA|action_name|param1|param2|param3
                        actor_name|speech|image_emotion
                        ACTION|action_name|param1|param2
                        """,
                        interactive=True,
                    )

                    if os.path.exists(transformer_path):

                        tr = transformers[generator]

                        if hasattr(tr, "generate_script"):
                            with gr.Group():
                                ai_params = gr.Textbox(
                                    label="Script Generation Assistant",
                                    info="(Optional) Parameters to use for script generation, separated by pipes (|)",
                                    lines=1,
                                    placeholder="",
                                )

                                use_ai_btn = gr.Button("Generate script", interactive=True)
                                use_ai_btn.click(fn=use_ai, inputs=[generator_in, script, video_title, ai_params], outputs=[video_title, images, script], api_name="use_ai_for_{}".format(generator))
                with gr.Column():
                    script_validator = gr.Textbox(
                        label="Script validator",
                        info="The script validator will check if the script is valid and give hints whenever something wrong is found. The output of the validator will be used for video generation. Check your script before generation",
                        lines=3,
                        value="Results of checking the script will be displayed here.",
                        show_copy_button=True,
                        interactive=True,
                    )
                    with gr.Group():
                        time_estimate = gr.Textbox(
                            label="Speech time estimate",
                            lines=1,
                            value="0 seconds",
                            interactive=False,
                        )
            with gr.Row():
                submit_btn = gr.Button("Submit validated script to generator", interactive=False)
                cancel_btn = gr.Button("Cancel", interactive=True)
            with gr.Row():
                output_video = gr.Video(label="Video generated", visible=True)
            with gr.Row():
                output_list = gr.Dataset(
                    components=[gr.Video(visible=False)],
                    label="Videos previously generated",
                    samples=[],
                    samples_per_page=5,
                    min_width="300",
                )
            with gr.Row():
                load_results = gr.Button("Load videos previously generated", interactive=True)

            def get_samples(generator):
                samples = []
                for file in os.listdir("__ui_runners__"):
                    if file.startswith(generator) and os.path.isdir(os.path.join("__ui_runners__", file)):
                        for result_file in os.listdir(os.path.join("__ui_runners__", file, "results")):
                            if result_file.endswith(".mp4"):
                                samples.append([os.path.join("__ui_runners__", file, "results", result_file)])
               
                
                return samples

            script.change(fn=check_script, inputs=[generator_in, script, actors_bg, music_bg, video_title, images], outputs=[script_validator, time_estimate, submit_btn], api_name="script_validator", concurrency_limit=50)
            
            def execute_script(email_input, generator, config_path, files, script, progress=gr.Progress()):

                if script == "":
                    progress(0.0, desc="Check the script beforehand!")
                    time.sleep(3)
                    return None
                
                destination_path =  "__ui_runners__/"+generator+"_"+str(int(time.time()))+"_"+str(random.randint(0, 99999))

                progress(0.1, desc="Building a dedicated workspace for the generator")

                #copy generator to runners folder
                copytree(os.path.join("./generators/", generator), destination_path)

                progress(0.15, desc="Sanitizing the workspace")

                #remove folders
                rmtree(os.path.join(destination_path, "temp"), ignore_errors=True)
                rmtree(os.path.join(destination_path, "results"), ignore_errors=True)
                rmtree(os.path.join(destination_path, "historique"), ignore_errors=True)
                rmtree(os.path.join(destination_path, "stories"), ignore_errors=True)
                os.makedirs(os.path.join(destination_path, "stories", "to_run"), exist_ok=True)
                os.makedirs(os.path.join(destination_path, "temp", "speeches"), exist_ok=True)
                os.makedirs(os.path.join(destination_path, "results"), exist_ok=True)

                #check if config file exists
                if config_path == "" or config_path == None:
                    progress(0.2, desc="No config file found, using default config.ini")
                    config_path = os.path.join(destination_path, "config.ini")

                if os.path.exists(config_path):
                    move(config_path, os.path.join(destination_path, "config.ini"))

                if files is not None:
                    for file in files:
                        copy(file, destination_path)

                with open(os.path.join(destination_path, "stories", "to_run", "script_from_ui.txt"), "w", encoding="utf-8") as f:
                    f.write(script)
                    f.close()
                
                lines = script.split("\n")

                status_updater_queue = Queue()
                video_generator_queue = Queue()

                def update_progress():
                        while True:
                                desc = "Loading status"
                                value = 0
                                time.sleep(2)
                                mp3_count = len([name for name in os.listdir(os.path.join(destination_path, "temp", "speeches")) if name.endswith(".wav")])
                                mp3_total = len([line for line in lines if not line.startswith("CTX")])
                                prefinalcheck = os.path.exists(os.path.join(destination_path, "temp", "prefinal-nosubs.mp4"))
                                if mp3_count < mp3_total:
                                    value = mp3_count / mp3_total
                                    desc="Generating audio file for: {}".format([line for line in lines if not line.startswith("CTX")][mp3_count])
                                    mp3_count = len([name for name in os.listdir(os.path.join(destination_path, "temp", "speeches")) if name.endswith(".wav")])
                                elif not os.path.exists(os.path.join(destination_path, "temp", "actors-video.mp4")):
                                    value = 0.4
                                    desc="Generating actors video"
                                elif not os.path.exists(os.path.join(destination_path, "temp", "gameplay-temp.mp4")) and not prefinalcheck:
                                    value = 0.6
                                    desc="Selecting gameplay video at random timestamps"
                                elif not os.path.exists(os.path.join(destination_path, "temp", "gameplay.mp4")) and not prefinalcheck:
                                    value = 0.7
                                    desc="Cropping gameplay video accordingly to video format and actors video"
                                elif prefinalcheck:
                                    value = 0.8
                                    desc="Generating final video"
                                elif len([name for name in os.listdir(os.path.join(destination_path, "results")) if name.endswith(".mp4")]) == 0:
                                    value = 0.9
                                    desc="Adding animated subtitles to final video"
                                else:
                                    break
                                status_updater_queue.put((value, desc))
                        return True
                                
                def run_generator():
                        os.environ['PYTHONIOENCODING'] = 'utf-8'
                        command = [sys.executable, "app.py"]
                        process = subprocess.Popen(command, cwd=destination_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8", text=True)

                        while True:
                            # Read a line from the standard output
                            output_line = process.stdout.readline()

                            # Read a line from the standard error
                            error_line = process.stderr.read()

                            # Check if there are no more lines to read and the process has finished
                            if not output_line and not error_line and process.poll() is not None:
                                break

                            if error_line:
                                video_generator_queue.put(error_line)

                status_updater_thread = Thread(target=update_progress)
                status_updater_thread.daemon = True
                status_updater_thread.start()
                finished = False
                progress(0.2, desc="Initializing video generator")
                while not finished:
                    try:
                        generator_error = None
                        video_generator_thread = Thread(target=run_generator)
                        video_generator_thread.daemon = True
                        video_generator_thread.start()

                        while video_generator_thread.is_alive():
                            try:
                                value, desc = status_updater_queue.get(block=False)
                                progress(value, desc=desc)
                            except Empty:
                                pass

                            try:
                                generator_error = video_generator_queue.get(block=False)
                                break
                            except Empty:
                                pass
                        
                        if generator_error is not None:
                            raise Exception(generator_error)
                        elif len([name for name in os.listdir(os.path.join(destination_path, "results")) if name.endswith(".mp4")]) == 0:
                            raise Exception("Generator stopped unexpectedly, please verify if ACTION/PANORAMA follow conventions and try again")
                        else:
                            finished = True
                            break
                    except Exception as e:
                        print("error!")
                        print(f"An error occurred: {e}")
                        #get message after Exception: if any or return full error
                        error = str(e).split("Exception: ")[1] if len(str(e).split("Exception: ")) > 1 else str(e)
                        time.sleep(1)
                        progress(0.0, desc="[GENERATOR ERROR] {}".format(error))
                        time.sleep(5)
                        progress(0.01, desc="Restarting...")
                        time.sleep(0.1)

                print("============== {} ==============".format(generator))
                print("Finished producing video: {}".format(generator))
                print(destination_path)
                print("=====================================")

                subject = "[VidMaker] {}: Video generated successfully!".format(generator)
                content = "Your video has been generated and is ready to be downloaded. You can find it by clicking the button at the bottom of the generator page"
                send_email_notification(email_input, subject, content)

                path = os.path.join(destination_path, "results", [name for name in os.listdir(os.path.join(destination_path, "results")) if name.endswith(".mp4")][0])
                return path
            
            submit_event = submit_btn.click(fn=execute_script, inputs=[email_input, generator_in, config_file, images, script_validator], outputs=output_video, api_name="run_video_generation", concurrency_limit=3)
            cancel_btn.click(lambda s: s, cancel_btn, output_video, cancels=[submit_event], api_name="cancel_video_generation_for_{}".format(generator))
            load_results.click(fn=get_samples, outputs=[output_list], api_name="get_videos_generated_for_{}".format(generator), inputs=[generator_in])

if __name__ == "__main__":
    demo.queue().launch(inbrowser=True, server_name="0.0.0.0", allowed_paths=["./__ui_runners__"])