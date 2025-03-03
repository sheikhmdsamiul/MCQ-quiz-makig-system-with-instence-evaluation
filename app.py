import streamlit as st
import os
import re
import fitz  
import json
from gtts import gTTS
from dotenv import load_dotenv
from groq import Groq

# Load environment variables from .env file
load_dotenv()

# Initialize Groq for chat pdf
groq_api_key = os.getenv('GROQ_API_KEY')
if not groq_api_key:
    st.sidebar.error("GROQ_API_KEY is not set. Please set it in the .env file.")
    st.stop()


# Initialize Groq for quiz
client = Groq(
    api_key=os.environ.get("GROQ_API_KEY"),
)



# Define functions for file handling and processing
def save_uploaded_files(uploaded_files, save_dir):
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    for uploaded_file in uploaded_files:
        with open(os.path.join(save_dir, uploaded_file.name), "wb") as f:
            f.write(uploaded_file.getbuffer())
    return save_dir

def extract_text_from_pdf(file_path):
    doc = fitz.open(file_path)
    text = ""
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text += page.get_text()
    return text

def pdf_read(pdf_directory):
    text_content = []
    for file_name in os.listdir(pdf_directory):
        if file_name.endswith('.pdf'):
            file_path = os.path.join(pdf_directory, file_name)
            text = extract_text_from_pdf(file_path)
            text_content.append(text)
    return text_content



def text_to_speech(text, lang='en'):
    tts = gTTS(text=text, lang=lang)
    tts.save("output.mp3")
    return "output.mp3"


@st.cache_data
def fetch_questions(text_content, quiz_level):
    RESPONSE_JSON = '''{
    "mcqs": [
        {
            "mcq": "multiple choice question1",
            "options": {
                "a": "choice here1",
                "b": "choice here2",
                "c": "choice here3",
                "d": "choice here4"
            },
            "correct": "a"
        },
        {
            "mcq": "multiple choice question2",
            "options": {
                "a": "choice here1",
                "b": "choice here2",
                "c": "choice here3",
                "d": "choice here4"
            },
            "correct": "b"
        },
        {
            "mcq": "multiple choice question3",
            "options": {
                "a": "choice here1",
                "b": "choice here2",
                "c": "choice here3",
                "d": "choice here4"
            },
            "correct": "c"
        }
    ]
}'''

    PROMPT_TEMPLATE = """
    Text: {text_content}
    You are an expert in generating MCQ type quiz on the basis of provided content. 
    Given the above text, create a quiz of 10 multiple choice questions keeping difficulty level as {quiz_level}. 
    Make sure the questions are not repeated and check all the questions to be conforming the text as well.
    Make sure to keep the format of your response like RESPONSE_JSON below and use it as a guide, do not do anything extra. 
    Ensure to make an array of 3 MCQs referring the following response json.
    Here is the RESPONSE_JSON: 

    {RESPONSE_JSON}
    """

    formatted_template = PROMPT_TEMPLATE.format(text_content=text_content, quiz_level=quiz_level, RESPONSE_JSON=RESPONSE_JSON)

    # Make API request
    response = client.chat.completions.create(
        model="llama-3.1-70b-versatile",
        messages=[
            {
                "role": "user",
                "content": formatted_template
            }
        ]
    )

    # Extract response content
    extracted_response = response.choices[0].message.content
    print("Raw API response:", repr(extracted_response))  # Use print for console logging

    # Remove backticks and extra whitespace
    extracted_response = extracted_response.strip()

    # Use regex to extract JSON content between curly braces
    json_match = re.search(r"\{.*\}", extracted_response, re.DOTALL)

    if json_match:
        json_str = json_match.group(0).strip()  # Get matched JSON string
    else:
        print("No valid JSON found in the response.")
        st.write("No valid JSON found in the response.")
        return []

    # Attempt to parse the cleaned JSON string
    try:
        json_data = json.loads(json_str)
        print("JSON is valid.")
    except json.JSONDecodeError as e:
        print("Invalid JSON:", e)
        st.write("Invalid JSON response received.")
        return []

    return json_data.get("mcqs", [])



# Main app
def main():
    st.set_page_config("MCQ quiz📝")
    st.header("MCQ quiz📝")

    # Sidebar
    with st.sidebar:
        st.title("Menu:")
        pdf_files = st.file_uploader("Upload your PDF Files and Click on the Submit & Process Button", accept_multiple_files=True)
        save_dir = "uploaded_pdfs"

    if pdf_files:
        save_uploaded_files(pdf_files, save_dir)
        st.sidebar.success("PDF Uploaded and Processed")

        raw_text = pdf_read(save_dir)
            # Dropdown for selecting quiz level
        quiz_level = st.selectbox("Select quiz level:", ["Easy", "Medium", "Hard"])

            # Convert quiz level to lower casing
        quiz_level_lower = quiz_level.lower()

            # Check if quiz_generated flag exists in session_state, if not initialize it
        if 'quiz_generated' not in st.session_state:
            st.session_state.quiz_generated = False

            # Track if Generate Quiz button is clicked
        if not st.session_state.quiz_generated:
            st.session_state.quiz_generated = st.button("Generate Quiz")

        if st.session_state.quiz_generated:
                # Define questions and options
            save_uploaded_files(pdf_files, save_dir)
            raw_text = pdf_read(save_dir)
                
                # Storing raw text in session_state
            if 'raw_text' not in st.session_state:
                st.session_state.raw_text = raw_text

            questions = fetch_questions(text_content=st.session_state.raw_text, quiz_level=quiz_level_lower)

                # Display questions and radio buttons
            selected_options = []
            correct_answers = []
            for question in questions:
                options = list(question["options"].values())
                selected_option = st.radio(question["mcq"], options, index=None)
                selected_options.append(selected_option)
                correct_answers.append(question["options"][question["correct"]])

                # Submit button
            if st.button("Submit"):
                    # Display selected options
                marks = 0
                st.header("Quiz Result:")
                for i, question in enumerate(questions):
                    selected_option = selected_options[i]
                    correct_option = correct_answers[i]
                    st.subheader(f"{question['mcq']}")
                    st.write(f"You selected: {selected_option}")
                    st.write(f"Correct answer: {correct_option}")
                    if selected_option == correct_option:
                            marks += 1
                st.subheader(f"You scored {marks} out of {len(questions)}")

if __name__ == "__main__":
    main()