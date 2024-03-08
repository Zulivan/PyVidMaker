from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageColor
from moviepy.editor import *
import os
import math


def get_font(name, size):
    if os.path.isfile(os.path.join("assets", "fonts", name + ".ttf")):
        return ImageFont.truetype(os.path.join("assets", "fonts", name + ".ttf"), size)

    return ImageFont.truetype(name, size)


def make_text_with_effects(text, font, font_size, color, output_file):
    font_size = int(font_size)

    # Create an ImageDraw object to measure text size
    dummy_image = Image.new('RGBA', (1080, 720), (255, 255, 255, 0))
    dummy_draw = ImageDraw.Draw(dummy_image)
    font = get_font(font, font_size)

    size_x, size_y = dummy_draw.textsize(text, font=font)
    # take offset into account for top and left margin
    offset_x, offset_y = font.getoffset(text)

    width1 = int(math.ceil(font_size * 0.13))
    width2 = int(math.ceil(1.4 * font_size * 0.13))

    size_x = size_x * 4
    size_y = size_y * 4

    position = (offset_x/2 + size_x/2.5, -offset_y/2 + size_y/2.5)

    text_image = Image.new('RGBA', (size_x, size_y), (255, 255, 255, 0))
    text_draw = ImageDraw.Draw(text_image)

    if not isinstance(color, tuple):
        if color in ImageColor.colormap:
            color = ImageColor.getrgb(color)

    color = color + (255,)

    text_draw.text(position, text, font=font, fill=color, stroke_width=width1, stroke_fill=(0, 0, 0, 255), align="center")

    blur_image = Image.new('RGBA', (size_x, size_y), (255, 255, 255, 0))
    blur_draw = ImageDraw.Draw(blur_image)

    blur_draw.text(position, text, font=font, fill=(0, 0, 0, 255), stroke_width=width2, stroke_fill=(0, 0, 0, 255), align="center")

    blurred_text_image = blur_image.filter(ImageFilter.BoxBlur(5))

    alpha = blurred_text_image.getchannel('A')

    new_alpha = alpha.point(lambda i: 200 if i > 0 else 0)

    blurred_text_image.putalpha(new_alpha)
    
    # Create a new image with the text and the blurred text

    new_image = Image.new('RGBA', (size_x, size_y), (255, 255, 255, 0))

    new_image.paste(blurred_text_image, (0, 0), blurred_text_image)

    new_image.paste(text_image, (0, 0), text_image)

    new_image.save(output_file, "PNG", quality=100, optimize=True)

    new_image = new_image.crop(new_image.getbbox())

    new_image.save(output_file, "PNG", quality=100, optimize=True)

def ModernTextClip(text, font, font_size, color):

    make_text_with_effects(text, font, font_size, color, "temp/temp.png")

    clip = ImageClip("temp/temp.png")

    return clip

#ModernTextClip("This is a test made to test the words", "KOMIKAX", 100, "white")