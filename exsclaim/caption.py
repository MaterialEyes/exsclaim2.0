# -*- coding: utf-8 -*-
import json
from functools import wraps
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.chat_models import ChatOpenAI
# from langchain_community.llms import HuggingFacePipeline
from langchain_community.vectorstores import Chroma
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
from re import sub
from time import sleep
from openai import OpenAI


__all__ = ["CustomEncoder", "get_context", "remove_control_characters", "create_openai_completion", "separate_captions",
           "get_keywords"]


def get_context(query, documents, embeddings):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=2048, chunk_overlap=100)
    texts = text_splitter.split_documents(documents)

    db = Chroma.from_documents(texts, embeddings)

    docs = db.similarity_search_with_score(query, k=1)
    # Get context strings
    context = ""
    for i in range(1): # TODO: Hardcode this if possible
        context += docs[i][0].page_content + "\n"
    return context


def remove_control_characters(s:str) -> str:
    return sub(r'[\x00-\x1F\x7F-\x9F]', '', s)


class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, str):
            return obj.encode('utf-8', 'ignore').decode('utf-8')
        return super().default(obj)


def create_openai_completion(api_key:str, caption_prompt:str, model:str="gpt-3.5-turbo") -> str:
    client = OpenAI(api_key=api_key)

    # TODO: Continue working on updating the ChatGPT interface
    completion = client.chat.completions.create(
        model=model,
        messages=[{"role": "assistant", "content": caption_prompt}],
        temperature=0
    )
    output_string = completion['choices'][0]['message']['content'].strip()

    # Replace single quotes with double quotes to make the string valid JSON
    output_string = output_string.replace(r"\", r"\\").replace("'", "\"")
    return remove_control_characters(output_string)


def retry(max_tries=5, delay_seconds=2):
    """
    Retries a function if a failure occurs.
    :param int max_tries: The maximum number of tries the system should attempt before throwing an error.
    :param float delay_seconds: The number of seconds between tries.
    :return: The returned value from the function.
    """
    def retry_decorator(func):
        @wraps(func)
        def retry_wrapper(*args, **kwargs):
            tries = 0
            while tries < max_tries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    wait_time = delay_seconds * (2 ** tries)
                    print(f"Error: {e}. Retrying in {wait_time} seconds...")
                    tries += 1
                    if tries == max_tries:
                        print("Max retries reached. Skipping this caption.")
                        return None
                        # raise e
                    sleep(wait_time)

        return retry_wrapper

    return retry_decorator


@retry
def separate_captions(caption, api, llm):
    if llm == "gpt-3.5-turbo":
        caption_prompt = f"Please separate the given full caption into the exact subcaptions and format as a dictionary with keys the letter of each subcaption. If there is no full caption then return an empty dictionary. Do not hallucinate\n{caption}"

        output_string = create_openai_completion(api, caption_prompt)

        # Parse the string into a dictionary
        output_dict = json.loads(output_string) # , cls=CustomEncoder)
    else:
        output_dict = {}

    # else:
    #     import os
    #     # Create a local tokenizer copy the first time
    #     if os.path.isdir("./tokenizer/"):
    #         tokenizer = AutoTokenizer.from_pretrained("./tokenizer/")
    #     else:
    #         tokenizer = AutoTokenizer.from_pretrained("model_name")
    #         os.mkdir("./tokenizer/")
    #         tokenizer.save_pretrained("./tokenizer/")
    #
    #     model = AutoModelForCausalLM.from_pretrained("eachadea/vicuna-13b-1.1")  # , device_map="auto") #, load_in_8bit=True)
    #     pipe = pipeline(
    #         "text-generation",
    #         model=model,
    #         tokenizer=tokenizer,
    #         max_length=2048,
    #         temperature=0.6,
    #         top_p=0.95,
    #         repetition_penalty=1.2
    #     )
    #     # llm = HuggingFacePipeline(pipeline=pipe)
    #
    #     template = """Answer the question based on the context below. If the
    # question cannot be answered using the information provided answer
    # with "I don't know".
    #
    # Context: {context}
    #
    # Question: {query}
    #
    # Answer: """
    #
    #     prompt_template = PromptTemplate(
    #         input_variables=["context","query"],
    #         template=template
    #     )
    #
    #     # conversation = LLMChain(
    #     #     prompt=prompt_template,
    #     #     llm=llm)
    #
    #     query = "Can you separate the given text into the exact subcaptions and format as a dictionary with keys the letter of each subcaption?"

    return output_dict


@retry()
def get_keywords(caption, api, llm):
    caption_prompt = f"You are an experienced material scientist. Summarize the text in a less than three keywords separated by comma. The keywords should be a broad and general description of the caption and can be related to the materials used, characterization techniques or any other scientific related keyword. Do not hallucinate or create content that does not exist in the provided text: {caption}"

    return create_openai_completion(api, caption_prompt, llm)
