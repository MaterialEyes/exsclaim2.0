# -*- coding: utf-8 -*-
import json
from langchain.vectorstores import Chroma
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
from langchain.llms import HuggingFacePipeline
from langchain import PromptTemplate, LLMChain
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import Chroma
from langchain import PromptTemplate
from langchain.chat_models import ChatOpenAI
import openai
import re
import os
import time

def get_context(query, documents, embeddings):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=2048, chunk_overlap=100)
    texts = text_splitter.split_documents(documents)

    db = Chroma.from_documents(texts, embeddings)

    docs = db.similarity_search_with_score(query, k=1)
    #Get context strings
    context=""
    for i in range(1):
        context += docs[i][0].page_content +"\n"
    return context

def remove_control_characters(s):
    return re.sub(r'[\x00-\x1F\x7F-\x9F]', '', s)

class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, str):
            return obj.encode('utf-8', 'ignore').decode('utf-8')
        return super().default(obj)


def separate_captions(caption, api, llm):
  if llm=='gpt-3.5-turbo':
    openai.api_key=api
    caption_prompt = f"Please separate the given full caption into the exact subcaptionsand format as a dictionary with keys the letter of each subcaption. If there is no full caption then return an empty dictionary. Do not hallucinate \n{caption}"

    completion = openai.ChatCompletion.create(
      model = 'gpt-3.5-turbo',
      messages = [
        {'role': 'assistant', 'content': caption_prompt}
      ],
      temperature = 0
    )
    output_string = completion['choices'][0]['message']['content']
    output_string = output_string.strip()

    # Replace single quotes with double quotes to make the string valid JSON
    output_string = output_string.replace("\\", "\\\\")
    output_string = output_string.replace("'", "\"")
    output_string = remove_control_characters(output_string)

    # Parse the string into a dictionary
    output_dict = json.loads(output_string)#, cls=CustomEncoder)

  else:
    #Create a local tokenizer copy the first time
    if os.path.isdir("./tokenizer/"):
        tokenizer = AutoTokenizer.from_pretrained("./tokenizer/")
    else:
        tokenizer = AutoTokenizer.from_pretrained("model_name")
        os.mkdir("./tokenizer/")
        tokenizer.save_pretrained("./tokenizer/")

    model = AutoModelForCausalLM.from_pretrained("eachadea/vicuna-13b-1.1")#, device_map="auto")#, load_in_8bit=True)
    pipe = pipeline(
        "text-generation",
        model=model,
        tokenizer=tokenizer,
        max_length=2048,
        temperature=0.6,
        top_p=0.95,
        repetition_penalty=1.2
    )
    llm = HuggingFacePipeline(pipeline=pipe)

    template = """Answer the question based on the context below. If the
    question cannot be answered using the information provided answer
    with "I don't know".

    Context: {context}

    Question: {query}

    Answer: """

    prompt_template = PromptTemplate(
        input_variables=["context","query"],
        template=template
    )

    conversation = LLMChain(
            prompt=prompt_template,
            llm=llm )

    query = 'Can you separate the given text into the exact subcaptions and format as a dictionary with keys the letter of each subcaption?'

  return output_dict


def get_keywords(caption, api, llm):
  llm = ChatOpenAI(model_name='gpt-3.5-turbo', openai_api_key=api)
  caption_prompt = f"You are an experienced material scientist. Summarize the text in a less than three keywords separated by comma. The keywords should be a broad and general description of the caption and can be related to the materials used, characterization techniques or any other scientific related keyword. Do not halucinate or create content that does not exist in the provided text: {caption}"
  openai.api_key=api
  completion = openai.ChatCompletion.create(
      model = 'gpt-3.5-turbo',
      messages = [
        {'role': 'assistant', 'content': caption_prompt}
      ],
      temperature = 0
    )
  output_string = completion['choices'][0]['message']['content']
  output_string = output_string.strip()
  output_string = output_string.replace("\\", "\\\\")
  output_string = output_string.replace("'", "\"")
  output_string = remove_control_characters(output_string)
  return output_string

  
def safe_summarize_caption(*args, **kwargs):
    """Safely call the get_keywords function with exponential backoff."""
    max_retries = 5
    base_wait_time = 2  # starting with 2 seconds

    for attempt in range(max_retries):
        try:
            # Attempt to call the get_keywords function
            return get_keywords(*args, **kwargs)
        except Exception as e:
            if attempt < max_retries - 1:  # if it's not the last attempt
                wait_time = base_wait_time * (2 ** attempt)  # double the wait time with every retry
                print(f"Error: {e}. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                # If we've reached the maximum retries, raise the exception
                print("Max retries reached. Skipping this caption.")
                return None  # or return a default value, or raise the exception
            
def safe_separate_captions(*args, **kwargs):
    """Safely call the get_keywords function with exponential backoff."""
    max_retries = 5
    base_wait_time = 2  # starting with 2 seconds

    for attempt in range(max_retries):
        try:
            # Attempt to call the get_keywords function
            return separate_captions(*args, **kwargs)
        except Exception as e:
            if attempt < max_retries - 1:  # if it's not the last attempt
                wait_time = base_wait_time * (2 ** attempt)  # double the wait time with every retry
                print(f"Error: {e}. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                # If we've reached the maximum retries, raise the exception
                print("Max retries reached. Skipping this caption.")
                return None  # or return a default value, or raise the exception