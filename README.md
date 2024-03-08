# PyVidMaker

PyVidMaker is a providing users with a simple yet effective automated video editing tool. It is designed to facilitate the creation of video content through scripted dialogues, allowing users to effortlessly generate dynamic videos. By specifying actors, emotions, and actions within a script.

Incorporating the advancements in Large Language Models (LLMs), this project aspires to craft quick video scripts that are ready to be rendered.

## Features
* **Mature User Interface:** PyVidMaker boasts a mature user interface facilitated by the integration of Gradio. This allows users to easily handle video generation and potential API calls.
* **Automated Audio Rendering with Voice Cloning:** The tool incorporates automated audio rendering, leveraging voice cloning technology. This feature adds a personalized touch to the generated videos.
* **Background Music with Audio Management:** Users can dynamically control the audio by pausing, changing music intensity, and seamlessly blending background music with the video content.
* **Automated Actor Rendering:** This includes the automatic combination of actor images, reducing the manual effort required for visual elements in the videos.
* **Actions/Panorama Features:** Developers can add their own actions, making PyVidMaker modular and customizable according to specific needs and creative requirements.
* **Automatic Subtitles:** PyVidMaker automatically generates animated subtitles synchronized with the actors' speech. The tool also supports custom fonts, providing users with flexibility in designing subtitles that align with their creative vision.

## Example script

```
myactor|Hello who's there?|think
anotheractor|I'm here!|smile
myactor|I've got a joke for you|cunning
myactor|What do you call a gamer who works at an abortion clinic?|smile
anotheractor|Emm, I don't know!|angry
myactor|Spawn camper|smile
ACTION|laugh|anotheractor
```

The script format is a simple and structured way to define, in this case, a conversation for automated video editing. Each line represents an action or dialogue in the video, and it follows this pattern:

- `actor|dialogue|emotion`: Specifies an actor, their spoken dialogue, and the corresponding emotion. For example:
  - `myactor|Hello who's there?|think`: The actor "myactor" says "Hello who's there?" while thinking.

- `ACTION|action_type|parameter`: Triggers a specific action. For example:
  - `ACTION|laugh|anotheractor`: Initiates laughter action that takes as parameter the actor "anotheractor".

## User Interface

When you initiate the video generation process through the UI, a specific folder named after the video generator is cloned from the "./generators" directory. This cloned folder is then copied into the "ui_runners" folder. Within this new folder, the "app.py" file of the cloned generator is executed as a separate thread.

```
+---------------------+       +-------------------------+       +--------------------------+
|   User Interface    |       |       User Interface    |       |    Video Generator       |
|       (Front)       |       |           (Logic)       |       |         (Folder)         |
+----------+----------+       +-------------+-----------+       +-------------+------------+
           |                                |                                 |
           | Start Video Generation          |                                |
           |   for generator "generator id"  |                                |
           |       with script "script"      |                                |
           | -----------------------------> |                                 |
           |                                |                                 |
           |                                |                                 |
           |                                |  Clone Generator Folder         |
           |                                | ------------------------------> |
           |                                |                                 |
           |                                |                                  |
           |                                |                                   |
           |                                |                                    |
           |                                |  Add script contents to             |
           |                                |  ./stories/to_run/script_to_run.txt |
           |                                | ----------------------------------> | 
           |                                |                                     |
           |                                |                                    |
           |                                |                                   |
           |                                |  Run app.py as Thread             |
           |                                | --------------------------------> |
           |                                |                                  |
           |                                |                                  |
           |                                |                                  |
           |                                |                                  |
           | <------------------------------|                                  |
           |  Video Generation Completed    |                                  |
           +--------------------------------|                                  |
                                            |                                  |
                                            +----------------------------------+
```

## Getting started

### Docker Usage

#### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/PyVidMaker.git
cd PyVidMaker
```

#### 2. Build the image

```bash
docker build -t pyvidmaker .
```

#### 3. Enjoy

The user interface can be accessed at port 80

[See the wiki](https://github.com/Zulivan/PyVidMaker/wiki)
