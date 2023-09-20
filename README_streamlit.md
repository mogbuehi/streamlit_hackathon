
# YT Language Tutor Application

Welcome to the YT Language Tutor Application! This tool is designed to help users learn foreign languages while watching YouTube clips! Foreign dramas, skits or anime, you can now make language learning fun and make the lessons stick. With this application, you can receive explanations for any unclear parts of a clip, ensuring that language is no longer a barrier to your learning and enjoyment.

## Features

- **YouTube Video Handling**
    - Download YouTube videos given a URL.
    - Convert downloaded videos to audio for processing.


- **Audio Processing**
    - Split audio files for easier transcription.
    - Transcribe audio to text.

- **Survey Handling**
    - Generate unique user IDs.
    - Save and retrieve survey answers.

- **Language Processing**
    - Detect the language of the given content.
    - Create a lesson outline based on the transcript.

- **Interactive Chat Interface**
    - Initialize and display a chatbox for user interactions.
    - Add messages to the chatbox.
    - Can ask questions to the AI Tutor

## How to Operate

1. Clone this repository or download the source code.
2. Navigate to the project directory in your terminal.
3. Install the required packages:

```bash
pip install -r requirements.txt
```

4. Start the Streamlit app:

```bash
streamlit run app.py
```

5. Navigate to the provided URL in your web browser.
6. Enter the URL of the YouTube clip you'd like to understand.
7. Follow the prompts in the chat interface to get explanations for the clip in your native language.

## Note on Tokens

Please be mindful of the token usage. If you exceed the token limit, kindly reset the application. We are aware of the token management challenges and are working on integrating better memory management in future versions to enhance your experience.

Enjoy using the YT Language Tutor Application! Feedback and contributions are always welcome.

## Note on YT videos

Please be mindful to avoid age-restricted videos. This is also part of future improvements to be able to download any YT video.
