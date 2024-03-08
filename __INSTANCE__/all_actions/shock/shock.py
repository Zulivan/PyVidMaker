from core import actor_background_generator
import os
import random

def handle_audio_generation(params = [], index=0):
    
    shock = random.choice(["shock1.wav", "shock2.wav", "shock3.wav"])

    return os.path.join("actions", "shock", shock), "pause|intensify"

def handle_clip_generation(d=0, params = [], index=0):
    return actor_background_generator.make_clip(params, d, False, ["shock"]), ""