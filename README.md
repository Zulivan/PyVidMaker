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
* **Background Gameplay Embed:** PyVidMaker incorporates automatically selected and cropped gameplay video, embedding it at the video's bottom to potentially captivate the audience.

## Limitations
PyVidMaker has certain limitations and problems that users should be aware of:

* **Slow Rendering Times:** This is primarily attributed to the moviepy compositing process, which can be relatively slow, especially when handling complex video compositions. [threaded_writefile](https://github.com/Zulivan/PyVidMaker/blob/master/__INSTANCE__/core/utils.py) proved fruitless in its attempt at optimization.

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

- `ACTION|action_name|parameter|parameter`: Triggers a specific action called "action_name" with arbitrary parameters.
  - `ACTION|laugh|anotheractor`: Initiates laughter action that takes as parameter the actor "anotheractor".

## User Interface

The [video generator](https://github.com/Zulivan/PyVidMaker/tree/master/__INSTANCE__) was originally designed to operate autonomously. To execute the video generator without utilizing the user interface, you can simply place the script file into the "/stories/to_run" folder and run the "app.py" file. However, it's important to note that if the process crashes, you'll need to restart it.

![image](https://github.com/Zulivan/PyVidMaker/assets/39313759/92747a69-8cd5-48c5-ba87-f4a49a3c9264)

When initiating the video generation process through the UI, a specific folder named after the video generator is cloned from the "./generators" directory. This cloned folder is then copied into the "ui_runners" folder. Within this new folder, the "app.py" file of the cloned generator is executed as a separate thread.

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
git clone https://github.com/Zulivan/PyVidMaker.git
cd PyVidMaker
```

#### 2. Build the image

```bash
docker build -t pyvidmaker .
```

#### 3. Enjoy

The user interface can be accessed at port 80

[Learn more about PyVidMaker](https://github.com/Zulivan/PyVidMaker/wiki)
