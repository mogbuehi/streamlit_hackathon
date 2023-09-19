
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
from dotenv import load_dotenv, find_dotenv
import eyed3
import pyaudio
import wave


#############--------------- ID and Surveys ------------########################
# Generate unique user ID
def generate_unique_id():
    return str(uuid.uuid4())

# Save survey answers to a file
def save_survey_answers(unique_id, answers):
    with open('survey_answers.json', 'w') as f:
        json.dump({unique_id: answers}, f)
        # f.write('\n')

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
# Take WAV file from downloads and save to converted audio folder


# Load API key from .env file
load_dotenv(find_dotenv()) 
openai.api_key = os.getenv('OPENAI_API_KEY')
# Load the API key



# Split long audio files into clips to be processed by Whisper API
def split_audio_pyaudio(audio_path, clip_duration_sec=30, overlap_duration_sec=3, output_folder='converted_audio/clips'):
    clip_list = []
    file_name = os.path.basename(audio_path)[:-4]
    
    # Determine the total duration of the audio file
    if audio_path.endswith('.mp3'):
        audio_file = eyed3.load(audio_path)
        total_duration = audio_file.info.time_secs
    elif audio_path.endswith('.wav'):
        with wave.open(audio_path, 'rb') as wf:
            n_frames = wf.getnframes()
            framerate = wf.getframerate()
            total_duration = n_frames / framerate
    else:
        raise ValueError("Unsupported audio format")
    
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 2
    RATE = 44100
    clip_duration_samples = clip_duration_sec * RATE
    overlap_samples = overlap_duration_sec * RATE
    
    wf = wave.open(audio_path, 'rb')
    p = pyaudio.PyAudio()

    clip_number = 1
    for start_sample in range(0, int(total_duration * RATE), clip_duration_samples - overlap_samples):
        frames = []

        for i in range(0, int(RATE / CHUNK * clip_duration_sec)):
            data = wf.readframes(CHUNK)
            if not data:
                break
            frames.append(data)

        clip_path = f"{output_folder}/{file_name}_clip_{clip_number}.wav"
        wf_clip = wave.open(clip_path, 'wb')
        wf_clip.setnchannels(CHANNELS)
        wf_clip.setsampwidth(p.get_sample_size(FORMAT))
        wf_clip.setframerate(RATE)
        wf_clip.writeframes(b''.join(frames))
        wf_clip.close()

        clip_list.append(clip_path)
        clip_number += 1

    wf.close()
    p.terminate()

    return clip_list

# Takes WAV audio clips and transcribes them and saves them to JSON
def transcribe(audio_path):
    clip_path_list = split_audio_pyaudio(audio_path)
    file_name = os.path.basename(audio_path)[:-4]
    transcribed_clips = []
    # Ensure the transcript file is empty to start with
    with open(f'{file_name}.txt', 'w') as txt_file:
        pass

    for clip in clip_path_list:
        with wave.open(clip, 'rb') as wf:
            n_frames = wf.getnframes()
            framerate = wf.getframerate()
            clip_duration = n_frames / framerate
            
            if clip_duration < 0.1:
                print(f"Skipping short clip (less than 0.1 sec): {clip}")
                continue  # Skip short clips
        
        with open(clip, 'rb') as audio_file:
            transcript = openai.Audio.transcribe(
                file=audio_file,
                model="whisper-1",
                response_format='text',
                temperature=0.0
            )
            transcribed_clips.append(transcript + '\n')

    full_transcript_str = ''.join(transcribed_clips)
   
    messages=[
    {'role':'system', 'content':'''You are a robot that is specifically designed to figure out what language a transcript is in. 
    When given a transcript, ONLY return the ISO-639-1 language code. Take your time and think this through.'''},
    {'role': 'user', 'content': 'je suis américain'},
    {'role': 'assistant', 'content': 'fr'},
    {'role': 'user', 'content': full_transcript_str}
    ]
    
    response = openai.ChatCompletion.create(
        model='gpt-3.5-turbo-0613',
        messages=messages,
        temperature=0
    )
    language = response['choices'][0]['message']['content']
    
    transcript_json = {'title': os.path.basename(audio_path)[:-4], 'transcript': full_transcript_str, 'language' : language}                   
    
    with open(f'transcript/{file_name}.json', 'w') as json_file:
        json.dump(transcript_json, json_file, indent=4)

    message = "Transcription process completed!"
    return transcript_json, message

#############--------------- Teacher ------------########################
# Function to get plain English word for language code
def get_language_word(language, openai_api_key=''):
    llm = OpenAI(model_name='gpt-3.5-turbo-0613', openai_api_key=st.session_state.api_key, temperature=0)

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
def create_lesson_outline(transcript_json, learning_goal='learn new languague', num_words='5', openai_api_key=''):
    try:
        with open('lesson_format.txt', 'r') as txt_file:
            lesson_format = txt_file.read()
    except FileNotFoundError:
        return "Error: 'lesson_format.txt' not found. Please make sure it's in the current working directory."

    chat = ChatOpenAI(temperature=0.2, model='gpt-3.5-turbo-0613', openai_api_key=st.session_state.api_key)
    template_string = '''Create a lesson based on this title ```{title}```, following this transcript ```{transcript_text}```, and following this format ```{lesson_format}```. Keep in mind the student's learning goal ```{learning_goal}``` and the number of words they want to learn```{num_words}```. For context you are making a lesson plan based on the title of an audio clip taken from a youtube video. Again the title of the video is {title}. Take this into account when making the title of the lesson plan and teaching the concept.
    Only output the lesson plan, nothing more'''
    
    
    prompt_template = ChatPromptTemplate.from_template(template_string)
    messages = prompt_template.format_messages(
        lesson_format=lesson_format,
        transcript_text=transcript_json['transcript'],
        title=transcript_json['title'],
        learning_goal=learning_goal,
        num_words=num_words
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
    
    if role == "user":  # If the message is from the user
        response = openai.ChatCompletion.create(
          model="gpt-3.5-turbo-0613", 
          prompt=message, 
          max_tokens=150  # Limit the response to 150 tokens
        )
        teacher_response = response.choices[0] # Extract the bot's response text
        st.session_state.messages.append({"role": "assistant", "content": teacher_response})

# Display the chatbox
def display_chatbox():
    st.markdown("<div id='chatbox-container'>", unsafe_allow_html=True)
    for msg in st.session_state.messages:
        st.chat_message(msg["role"]).write(msg["content"])
    st.markdown("</div>", unsafe_allow_html=True)


############################## Main Streamlit app #################################
#Main function
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
        'transcribe_clicked': False,
    }.items():
        if key not in st.session_state:
            st.session_state[key] = default_value
            
    st.title('Language Learning AI Tutor')

    # Handle API key at the very top
    if "api_key" not in st.session_state or not st.session_state.api_key:
        entered_api_key = st.text_input("Enter your API key:", type='password', key='api_key_input')
        if entered_api_key:
            st.session_state.api_key = entered_api_key
            openai.api_key = entered_api_key
            st.write("API key loaded successfully!")
    else:
        #st.write("API key already in session state.")
        openai.api_key = st.session_state.api_key
    
    
    if not st.session_state['access_granted']:
        
        # ID input and validation
        entered_id = st.text_input('Enter your unique ID to access the app:', key='unique_id_input')
        
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
        st.markdown(
            """
            ------------------------------------------------------------------------------
            **Instructions:**
            - **For All Students:** 
              - Please enter your API key.
            - **For First-Time Students:** 
              - Generate a new ID and keep it safe for future visits.
            - **For Returning Students:**
              - Use your existing ID to continue your learning journey.
            """
        )
    else:
        if not st.session_state['survey_done']:
            st.subheader('Survey Questions')
            learning_goal = st.text_input("What's your daily learning goal? (ex: 5 minutes, 10 minutes)", key='daily_learning_goal_input')
            num_words = st.text_input('How many words do you want to learn? (ex: 5, 10, 15)', key='num_words_input')

            if st.button('Submit Survey'):
                answers = {'learning_goal': learning_goal, 'num_words': num_words}
                save_survey_answers(st.session_state['unique_id'], answers)
                st.session_state['learning_goal'] = learning_goal
                st.session_state['num_words'] = num_words
                st.session_state['survey_done'] = True
                st.success('Survey answers submitted!')
                st.experimental_rerun()

    # Sidebar for Video Upload
    if st.session_state['access_granted'] and st.session_state['survey_done']:
        with st.sidebar:
            st.title('Video Upload')
            video_url = st.text_input('Paste your YouTube video link here')
            if st.button('Create Lesson'):
                st.session_state.video_url = video_url
                st.session_state.show_chat_window = True
                st.session_state.transcribe_clicked = True
                # st.sidebar.video(video_url)
                 # Save to session state that video should be displayed
                st.session_state.display_video = True

            # Check if video should be displayed in the sidebar
            if 'display_video' in st.session_state and st.session_state.display_video:
                st.sidebar.video(video_url)

            # Clears state/screen
            if st.button("Clear Messages"):
                if 'messages' in st.session_state:
                    st.session_state['messages']=[]

    # Main chat interface
    if st.session_state.get('show_chat_window', False):
        st.text('Please wait a few mins after hitting the "Create Lesson" button')
        # Initialize session state variables if not already initialized
        if "messages" not in st.session_state:
            st.session_state.messages = []
      
        # Display the previous chat history
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
      
        # Get user input
        user_input = st.chat_input("Begin lesson here and ask questions...")
      
        if user_input:
            # Append user's message to the session state
            st.session_state.messages.append({"role": "user", "content": user_input})
        
            # Display user's message immediately
            with st.chat_message("user"):
                st.markdown(user_input)

            # Generate assistant's response
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                full_response = ""
      
                # Make the API call and stream the response
                for response in openai.ChatCompletion.create(
                    model="gpt-3.5-turbo-0613",  # Replace with your model
                    messages=[
                        {"role": m["role"], "content": m["content"]}
                        for m in st.session_state.messages
                    ],
                    stream=True,
                ):
                    # Update the assistant's message as new content arrives
                    full_response += response.choices[0].delta.get("content", "")
                    message_placeholder.markdown(full_response + "▌")
            
                message_placeholder.markdown(full_response)
          
            # Append assistant's message to the session state
            st.session_state.messages.append({"role": "assistant", "content": full_response})




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
                    transcript_data, transcript_message = transcribe(audio_path)
                    st.session_state.messages.append({"role": "assistant", "content": transcript_message})

                    # if transcript_data is not None:
                    # Detect language
                    language = get_language_word(transcript_data['language'])
                    st.session_state.messages.append({"role": "assistant", "content": f"Detected language is {language}"})

                    # Create lesson from transcript                   
                    lesson_content, lesson_message = create_lesson_outline(transcript_data)
                    st.session_state.messages.append({"role": "assistant", "content": "Here's the transcript and the lesson plan"}) 
                    st.session_state.messages.append({"role": "assistant", "content": '**Transcript: **' + transcript_data['transcript']})
                    st.session_state.messages.append({"role": "assistant", "content": '**Lesson plan: **' + lesson_content})
                    # st.session_state.messages.append({"role": "assistant", "content": lesson_content})
                    st.session_state.messages.append(
                            {"role": "system", "content": f'Follow the lesson plan as outlined: {lesson_content} and try your best not to deviate. Teach each word one at at time and explain in detail, including writing system or other relavent details for a firt time learner. Think this out step by step'})
            st.experimental_rerun()

# Entry point
if __name__ == '__main__':
    main()






