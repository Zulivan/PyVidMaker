from moviepy.editor import *
import os
from .image_utils import ModernTextClip
from moviepy.video.VideoClip import ImageClip
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
import string
import configparser
import random
import ast
from progress.bar import Bar

config = configparser.ConfigParser()
config.read('config.ini')

def get_dynamic_subtitles(captions):
    dynamic_subtitles = []
    for (start, end), txt in captions:
        words = txt.split()
        #count the total number of letters in the words array
        total_letters = 0
        one_char_time = 0
        for w in words:
            if w not in string.punctuation:
                total_letters += len(w)
        
        # avoid division by zero
        if total_letters > 0:
            one_char_time = (cvsecs(end) - cvsecs(start)) / total_letters

        previous_start_time = cvsecs(start)

        for id, w in enumerate(words):

            wlength = one_char_time * len(w)

            dynamic_subtitles.append(((previous_start_time, previous_start_time + wlength), w))
            previous_start_time += wlength
    return dynamic_subtitles

def perceive_word_size(word):
    character_thickness = {
            'i': 0.5,
            "'": 0.3,
            '.': 0.5,
            ':': 0.5,
            ';': 0.5,
            '!': 0.5,
            'l': 0.5,
            '(': 0.5,
            ')': 0.5,
            '[': 0.5,
            ']': 0.5,
            '{': 0.5,
            '}': 0.5,
    }
    perceived_size = 0
    for c in word:
        if c.lower() in character_thickness:
            perceived_size += character_thickness[c.lower()]
        else:
            perceived_size += 1

    return perceived_size


def word_by_word_captions(captions, def_pos):
    dynamic_subtitles = get_dynamic_subtitles(captions)
    clips = []
    y_size = 0
    for index, caption in enumerate(dynamic_subtitles):
        text = caption[1]
        text = text.upper().replace(",", "").replace(".", "")

        clr = ast.literal_eval(config.get("Subtitles", "color"))
        if isinstance(clr, list):
            clr = random.choice(clr)

        perceived_size = perceive_word_size(text) + 1

        base_size = config.getfloat("Subtitles", "wbw_size")
        base_size = (base_size*8) / perceived_size if perceived_size > 11 else base_size
        base_size = base_size if base_size > 60 else 60

        txt_clip = ModernTextClip(text, config.get("Subtitles", "font"), base_size, clr) #TextClip(text, font=config.get("Subtitles", "font"), stroke_width=12, stroke_color="black", fontsize=base_size, color=clr).
        
        if txt_clip.h > y_size:
            y_size = txt_clip.h
        
        position = def_pos - txt_clip.h / 2
        txt_clip = txt_clip.set_position(("center", position)).set_duration(caption[0][1] - caption[0][0])
        txt_clip = txt_clip.set_start(caption[0][0]).resize(lambda t: (0.85 + 0.15 * min(t*16 , 1))).rotate(lambda t : -2 + min(40*t, 2))

        if config.getboolean("Subtitles", "enable_emojis"):
            emoji = None
            for file in os.listdir(os.path.join("assets", "emojis")):
                
                substr = text.lower().replace(" ", "").replace("l'", "").replace("d'", "").replace(",", "").replace(".", "").replace("!", "").replace("?", "").replace("*", "").replace("é", "e").replace("è", "e").replace("ê", "e").replace("à", "a").replace("â", "a").replace("î", "i").replace("ô", "o").replace("û", "u").replace("ù", "u").replace("ç", "c")
                if substr.endswith("s"):
                    substr = substr[:-1]
                
                # if file name without extension equals to the text
                if file.lower().replace(".png", "").replace(".jpg", "").replace(".jpeg", "") == substr:
                    print("Found emoji for " + text + " : " + substr + " in " + file + " (" + str(file.count(substr)) + ")")
                    emoji = os.path.join("assets", "emojis", file)
                    break

            if emoji is not None:
                emoji_clip = ImageClip(emoji).set_duration(caption[0][1] - caption[0][0]).set_start(caption[0][0]).resize(lambda t: (0.7 + 0.2 * min(t*18, 1)))
                
                starting_point = 1080 * 0.2
                ending_point = 1080 * 0.5
                
                emoji_clip = emoji_clip.set_position(lambda t: ((starting_point + min((ending_point),(t) * 750 ), position + txt_clip.h/1.1)))
                clips.append(emoji_clip)
                
        clips.append(txt_clip)

    if(len(clips) == 0):
        print("WARNING : There is not in a single word to display in the video.")
        # append invisible clip to avoid error
        clips.append(ColorClip((1080, 1980), color=(0,0,0), duration=1).set_start(0).set_opacity(0))
    return clips, y_size

def group_captions(captions, position, chars=12, lines=2):
    threshold = 0.5
    captions = get_dynamic_subtitles(captions)
    dynamic_subtitles = []
    loop_start = 0
    loop_end = 0
    caption_line = ""
    y_size = 0
    lines = int(lines)
    # Make sentce captions
    for i, ((start, end), word) in enumerate(captions):
        start = cvsecs(start)
        end = cvsecs(end)

        if len(caption_line) + len(word) < chars and i != len(captions) - 1 and start - loop_end < threshold:
            caption_line += word + " "
            loop_end = end
        else:
            dynamic_subtitles.append(((loop_start, loop_end), caption_line.strip()))
            caption_line = word + " "
            loop_start = start
            loop_end = end

            if i == len(captions) - 1:
                dynamic_subtitles.append(((loop_start, loop_end), caption_line.strip()))
    
    subtitles_grapes = []
    in_subtitles_grapes = []

    cascade = False

    #Adapt to the amount of lines we want
    for i in range(0, len(dynamic_subtitles), 1):

        if i not in in_subtitles_grapes:
            (start, end), _t = dynamic_subtitles[i]
            final_start = start
            final_end = end
            inner_captions = []
            inner_captions.append(dynamic_subtitles[i])
            in_subtitles_grapes.append(i)

            for p in range(i, i + lines, 1):
                if p < len(dynamic_subtitles):
                    (next_start, next_end), text = dynamic_subtitles[p]
                    if next_start - final_end < threshold and p not in in_subtitles_grapes:
                        inner_captions.append(dynamic_subtitles[p])
                        in_subtitles_grapes.append(p)
                        final_end = next_end

            subtitles_grapes.append((final_start, final_end, inner_captions))

    clips = []

    with Bar('Generating animated subtitles', suffix='%(percent).1f%% - %(eta)ds', max=len(captions)*lines) as bar:
        for grape_index, grape in enumerate(subtitles_grapes):
            ref_start, ref_end, inner_captions = grape
            for inner_index, caption in enumerate(inner_captions):
                # Gat captions of a grape
                (start, end), text = caption
                index = inner_index + grape_index * lines

                sentence_captions = get_dynamic_subtitles([caption])

                dummy = (0, sentence_captions[0][0][0]), "°"
                sentence_captions.insert(0, dummy)
                final_dummy = (sentence_captions[-1][0][1], ref_end), "°"
                sentence_captions.append(final_dummy)


                fontsize = 105 - perceive_word_size(text) * 1.2
                fontsize = max(75, fontsize)

                # Loop through each word
                for i, word_data in enumerate(sentence_captions):
                    (word_start, word_end), word = word_data
                    word = word.strip().upper()

                    if i == 0:
                        word_start = ref_start
                    elif i == len(sentence_captions) - 1:
                        word_end = ref_end

                    word_end = word_end - ref_start
                    word_start = word_start - ref_start

                    x_pos = 0
                    y_pos = 0
                    size_y = 0
                    size_x = 0
                    size_x_temp = 0

                    inner_clips = []

                    final_y_pos = y_pos+fontsize*inner_index

                    for i2, word_data2 in enumerate(sentence_captions):
                        (ws2, we2), word_to_display = word_data2
                        word_to_display = word_to_display.strip().upper()
                        if word_to_display == "°":
                            continue

                        clr = ast.literal_eval(config.get("Subtitles", "color"))
                        if isinstance(clr, list):
                            clr = random.choice(clr)

                        clr = clr if word_to_display == word else "white"
                        fs = fontsize * 1.2 if word_to_display == word else fontsize

                        clip = ModernTextClip(word_to_display, config.get("Subtitles", "font"), fs, clr).set_start(word_start).set_position((x_pos, final_y_pos)).set_duration(word_end-word_start)
                        
                        s_x, s_y = clip.size
                        
                        size_x_temp += s_x + 20
                        x_pos = size_x_temp

                        if size_x_temp > size_x:
                            size_x = size_x_temp

                        if s_y > size_y:
                            size_y = s_y

                        inner_clips.append(clip)

                    for clipi, clip in enumerate(inner_clips):

                        s_x, s_y = clip.size

                        final_pos = final_y_pos + size_y/2 - s_y/2

                        p_x, p_y = clip.pos(0)

                        clip = clip.set_position((p_x, final_pos))

                        inner_clips[clipi] = clip


                    size_x -= 20

                    clips.append(CompositeVideoClip(inner_clips, size=(size_x, size_y*lines)).set_start(ref_start).set_position(("center", position)).set_duration(ref_end-ref_start))
                    
                    if size_y > y_size:
                        y_size = size_y

                    bar.next()

    return clips, y_size*lines

def dynamic_captions(captions, position):
    print("Creating dynamic captions")

    captions_normalized = [(c[1][0], c[1][1]) for c in captions]

    mode = config.get('Subtitles', 'mode')

    y_size = 0
    if mode == "group":
        clips, y_size = group_captions(captions_normalized, position, 12, config.getint('Subtitles', 'lines'))
    elif mode == "wordbyword":
        clips, y_size = word_by_word_captions(captions_normalized, position)

    final_clip = CompositeVideoClip(clips, size=(1080,1980)).set_duration(cvsecs(captions[-1][1][0][1]))

    return final_clip, y_size
