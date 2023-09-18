
import streamlit as st
from streamlit import elements
import json
import uuid
import os
from pytube import YouTube
from moviepy.editor import VideoFileClip
import openai
from langchain.llms import OpenAI
from langchain.chat_models import ChatOpenAI
from langchain import PromptTemplate
from langchain.prompts import ChatPromptTemplate
import time 


# Load the API key
openai.api_key = OPENAI_API_KEY

#############--------------- ID and Survers ------------########################
# Generate unique user ID
def generate_unique_id():
    return str(uuid.uuid4())

# Save survey answers to a file
def save_survey_answers(unique_id, answers):
    with open('survey_answers.json', 'a') as f:
        json.dump({unique_id: answers}, f)
        f.write('\n')

# Load all stored unique IDs
def load_unique_ids():
    try:
        with open('unique_ids.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

# Save a unique ID
def save_unique_id(unique_id):
    ids = load_unique_ids()
    ids.append(unique_id)
    with open('unique_ids.json', 'w') as f:
        json.dump(ids, f)
        

#############--------------- Video transcription ------------########################

# Download video from URL
def download_video(url, output_directory='./downloads'):
    try:
        yt = YouTube(url)
        video = yt.streams.get_highest_resolution()
        if not os.path.exists(output_directory):
            os.makedirs(output_directory)
        video.download(output_path=output_directory)
        return os.path.join(output_directory, video.default_filename), 'Video downloaded successfully.'
    except Exception as e:
        message = f'An error occurred: {e}'
        return None, message

# Convert video to audio
def convert_to_audio(video_path, output_directory='./converted_audio'):
    try:
        video = VideoFileClip(video_path)
        audio_filename = f"{os.path.basename(video_path).split('.')[0]}.wav"
        audio_path = os.path.join(output_directory, audio_filename)
        if not os.path.exists(output_directory):
            os.makedirs(output_directory)
        video.audio.write_audiofile(audio_path)
        message = 'Audio converted successfully.'
        return audio_path, message
    except Exception as e:
        message = f"An error occurred: {e}"
        return None, message
    
# Transcribe audio
def transcribe_audio(audio_path):
    try:
        audio_file = open(audio_path, 'rb')
        v1_transcript = openai.Audio.transcribe(
            file=audio_file,
            model="whisper-1",
            response_format='json',
            temperature=0.2
        )

        # Detect language
        messages = [
            {'role': 'system', 'content': 'You are a robot that is specifically designed to figure out what language a transcript is in. When given a transcript, ONLY return the ISO-639-1 language code. Take your time and think this through.'},
            {'role': 'user', 'content': v1_transcript['text'][:1000]}
        ]
        response = openai.ChatCompletion.create(
            model='gpt-3.5-turbo-0613',
            messages=messages,
            temperature=0
        )
        language = response['choices'][0]['message']['content']
        v1_transcript['language'] = language

        # Display in chat box
        message = "Transcription successful."
        return v1_transcript, message
    except Exception as e:
        message = f"An error occurred: {e}"
        return None, message


# Save the transcript
def save_transcript(transcript, audio_path, output_directory='./transcripts'):
    try:
        transcript_filename = f"{os.path.basename(audio_path).split('.')[0]}"
        if not os.path.exists(output_directory):
            os.makedirs(output_directory)
        json_path = os.path.join(output_directory, f'{transcript_filename}.json')
        with open(json_path, 'w') as json_file:
            json.dump(transcript, json_file)
        message = 'Transcript saved successfully.'
        return json_path, message
    except Exception as e:
        message = f"An error occurred: {e}"
        return None, message

#############--------------- Teacher ------------########################
# Function to get plain English word for language code
def get_language_word(language, openai_api_key):
    llm = OpenAI(model_name='gpt-3.5-turbo-0613', openai_api_key=openai_api_key, temperature=0)
    template = '''Convert the ISO-639-1 language code into the plain english word for the language. ONLY return the english word for that language, nothing more.
    Here is the language code: {language}  
    Take your time and think this through. Remember only respond with one word, the english word for the language.'''
    prompt = PromptTemplate(
        input_variables=['language'],
        template=template,
    )
    final_prompt = prompt.format(language=language)
    return llm(final_prompt)

# Function to create lesson outline
def create_lesson_outline(transcript_text, openai_api_key):
    try:
        with open('lesson_format.txt', 'r') as txt_file:
            lesson_format = txt_file.read()
    except FileNotFoundError:
        return "Error: 'lesson_format.txt' not found. Please make sure it's in the current working directory."

    chat = ChatOpenAI(temperature=0.0, model='gpt-3.5-turbo-0613', openai_api_key=openai_api_key)
    template_string = '''Create a lesson based on this transcript {transcript_text} following this format {lesson_format}. 
    Only output the lesson plan, nothing more'''
    
    prompt_template = ChatPromptTemplate.from_template(template_string)
    messages = prompt_template.format_messages(
        lesson_format=lesson_format,
        transcript_text=transcript_text
    )
    response = chat(messages)
    message = 'Lesson outline created successfully.'
    return response.content, message

#############--------------- Chat bot ------------########################

# Initialize the chatbox state
def initialize_chatbox():
    if "messages" not in st.session_state:
        st.session_state["messages"] = []

# Add a message to the chatbox
def add_to_chatbox(role, message):
    st.session_state.messages.append({"role": role, "content": message})

# Display the chatbox
def display_chatbox():
    st.markdown("<div id='chatbox-container'>", unsafe_allow_html=True)
    for msg in st.session_state.messages:
        st.chat_message(msg["role"]).write(msg["content"])
    st.markdown("</div>", unsafe_allow_html=True)


        

############################## Main Streamlit app #################################
# Main function
def main():
    
    # Initialize all session_state variables
    for key, default_value in {
        'access_granted': False,
        'survey_done': False,
        'unique_id': '',
        'show_chat_window': False,
        'video_url': '',
        'chat_history': [],
        'messages': [],
        'transcribe_clicked': False
    }.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

    st.title('Language Learning AI Tutor')

    # Access Control
    if not st.session_state['access_granted']:
        entered_id = st.text_input('Enter your unique ID to access the app:')

        if st.button('Submit ID'):
            unique_ids = load_unique_ids()
            if entered_id in unique_ids:
                st.session_state['access_granted'] = True
                st.session_state['survey_done'] = True
                st.session_state['unique_id'] = entered_id
                st.success("Access granted.")
                st.experimental_rerun()
            else:
                st.warning('Invalid ID. Access denied.')

        if st.button('Generate New ID'):
            new_id = generate_unique_id()
            save_unique_id(new_id)
            st.session_state['access_granted'] = True
            st.session_state['unique_id'] = new_id
            st.session_state['survey_done'] = False
            st.success(f"New ID generated: {new_id}")

    else:
        if not st.session_state['survey_done']:
            st.subheader('Survey Questions')
            learning_goal = st.text_input("What's your daily learning goal?")
            num_words = st.text_input('How many words do you want to learn?')

            if st.button('Submit Survey'):
                answers = {'learning_goal': learning_goal, 'num_words': num_words}
                save_survey_answers(st.session_state['unique_id'], answers)
                st.session_state['survey_done'] = True
                st.success('Survey answers submitted!')
                st.experimental_rerun()

    # Sidebar for Video Upload
    if st.session_state['access_granted'] and st.session_state['survey_done']:
        with st.sidebar:
            st.title('Video Upload')
            video_url = st.text_input('Paste your YouTube video link here')
            if st.button('Transcribe'):
                st.session_state.video_url = video_url
                st.session_state.show_chat_window = True
                st.session_state.transcribe_clicked = True

    # Main chat interface
    if st.session_state.get('show_chat_window', False):
        # Display previous chat messages
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        user_input = st.chat_input("Type your message here...")
        if user_input:
            st.session_state.messages.append({"role": "user", "content": user_input})

        # Perform transcription if Transcribe button is clicked
        if st.session_state.get('transcribe_clicked', False):
            st.session_state.transcribe_clicked = False

            # Download video
            video_path, video_message = download_video(st.session_state['video_url'])
            st.session_state.messages.append({"role": "assistant", "content": video_message})

            if video_path:
                # Convert to audio
                audio_path, audio_message = convert_to_audio(video_path)
                st.session_state.messages.append({"role": "assistant", "content": audio_message})

                if audio_path:
                    # Transcribe audio
                    transcript_data, transcript_message = transcribe_audio(audio_path)
                    st.session_state.messages.append({"role": "assistant", "content": transcript_message})

                    if transcript_data is not None:
                        # Detect language
                        language = transcript_data.get('language', 'Unknown')
                        st.session_state.messages.append({"role": "assistant", "content": f"Detected language is {language}"})

                        # Create lesson from transcript
                        lesson_content, lesson_message = create_lesson_outline(transcript_data['text'], OPENAI_API_KEY)
                        st.session_state.messages.append({"role": "assistant", "content": f"Here's your lesson:"})
                        st.session_state.messages.append({"role": "assistant", "content": lesson_content})
            
            st.experimental_rerun()

# Entry point
if __name__ == '__main__':
    main()






