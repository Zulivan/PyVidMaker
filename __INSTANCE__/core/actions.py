from moviepy.editor import *
from core import actor_background_generator
import importlib

def bootstrap():
    addon_functions = {}

    # Find all .py files in the 'actions' directory and its subdirectories
    addon_dir = 'actions'
    for root, dirs, files in os.walk(addon_dir):
        for file in files:
            if file.endswith('.py'):
                addon_path = os.path.join(root, file)
                module_name = os.path.splitext(os.path.basename(addon_path))[0]
                module_path = os.path.relpath(addon_path).replace(os.path.sep, '.')[:-3]
                addon_module = importlib.import_module(module_path)

                if hasattr(addon_module, 'handle_audio_generation') and hasattr(addon_module, 'handle_clip_generation'):
                    addon_functions[module_name] = {
                        'handle_audio_generation': addon_module.handle_audio_generation,
                        'handle_clip_generation': addon_module.handle_clip_generation
                    }

    return addon_functions


def handle_audio_generation(action, params = [], index = 0):

    print("[AUDIO] Handling action: {}-{} with params: {}".format(action, index, str(params)))

    loaded_actions = bootstrap()
    if action in loaded_actions:
        try:
            return loaded_actions[action]['handle_audio_generation'](params, index)
        except TypeError:
            raise Exception("The action {} audio generation method doesn't take into account the following arguments: (params, index)".format(action))

def handle_clip_generation(action, duration=0, params = [], index = 0):

    print("[CLIP] Handling action: {}-{} with params: {}".format(action, index, str(params)))

    loaded_actions = bootstrap()
    if action in loaded_actions:
        try:
            return loaded_actions[action]['handle_clip_generation'](duration, params, index)
        except TypeError:
            raise Exception("The action {} clip generation method doesn't take into account the following arguments: (duration, params, index)".format(action))
    