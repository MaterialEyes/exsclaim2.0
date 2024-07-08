# -*- coding: utf-8 -*-
import json
import logging
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
    output_string = completion.choices[0].message.content.strip()

    # Replace single quotes with double quotes to make the string valid JSON
    output_string = output_string.replace("\\", "\\\\").replace("'", "\"")
    return remove_control_characters(output_string)


def retry(max_tries=5, delay_seconds=2, logger:logging.Logger=logging.getLogger(__name__)):
    """
    Retries a function if a failure occurs.
    :param int max_tries: The maximum number of tries the system should attempt before throwing an error.
    :param float delay_seconds: The number of seconds between tries.
    :param logging.Logger logger: The logger to use if an error occurs.
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
                    logger.exception(f"Error: {e}. Retrying in {wait_time} seconds...")
                    tries += 1
                    if tries == max_tries:
                        logger.exception("Max retries reached. Skipping this caption.")
                        return None
                        # raise e
                    sleep(wait_time)

        return retry_wrapper
    return retry_decorator


@retry()
def separate_captions(caption:str, api:str, llm:str) -> dict:
    output_dict = dict()
    if llm == "gpt-3.5-turbo":
        caption_prompt = f"Please separate the given full caption into the exact subcaptions and format as a syntactically valid Python dictionary with keys the letter of each subcaption. If there is no full caption then return an empty dictionary. Do not hallucinate\n{caption}"

        output_string = create_openai_completion(api, caption_prompt)

        # Parse the string into a dictionary
        try:
            output_dict = json.loads(output_string) # , cls=CustomEncoder)
        except json.decoder.JSONDecodeError as e:
            logging.error(f"Could not decode the JSON response given.\n`{output_string}`")
            raise e
    else:
        logging.exception(f"Unsupported llm type: {llm}, returning an empty dictionary.")

    return output_dict


@retry()
def get_keywords(caption:str, api:str, llm:str) -> str:
    caption_prompt = f"You are an experienced material scientist. Summarize the text in a less than three keywords separated by comma. The keywords should be a broad and general description of the caption and can be related to the materials used, characterization techniques or any other scientific related keyword. Do not hallucinate or create content that does not exist in the provided text: {caption}"

    return create_openai_completion(api, caption_prompt, llm)
