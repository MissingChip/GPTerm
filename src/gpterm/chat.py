#!/usr/bin/env python3

from typing import List
import logging
from dotenv import load_dotenv
from gpterm.context import Context
import openai
from recordclass import dataobject

# Setup logging
logging.basicConfig(level=logging.DEBUG, filename="chat.log")
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
# Constants
# MODELS = ["gpt-3.5", "gpt-3.5-turbo", "gpt-4", "gpt-4-1106-preview"]
OPENAI_MODELS = {
    "3": "gpt-3.5",
    "4": "gpt-4-1106-preview",
    "gpt-3.5": "gpt-3.5",
    "gpt-3.5-turbo": "gpt-3.5-turbo",
    "gpt-4": "gpt-4",
    "gpt-4-turbo": "gpt-4-1106-preview",
}
SYSTEM = "You are helpful assistant. Respond with short, single sentence answers unless asked to elaborate."
# SYSTEM = "You are a thesaurus. Respond 'synonym1, synonym2, ... | antonym1, antonym2, ...'."
START_MESSAGE = {
    "role": "system",
    "content": SYSTEM,
}

class CompletionContext(dataobject):
    openai_client: openai.OpenAI
    messages: List[dict]

def complete_openai(context):
    """Complete the current message using OpenAI."""
    try:
        response = ""
        stream = context.openai_client.chat.completions.create(
            messages=context.messages,
            model="gpt-3.5-turbo",
            stream=True,
        )
        logger.info(stream)
        for part in stream:
            if part.choices[0].finish_reason == "stop":
                break
            content = part.choices[0].delta.content
            response += content
            print(content, end="", flush=True)
    except openai.OpenAIError as e:
        logger.error(f"An API error occurred: {e}")
    return response

COMPLETION = {v: complete_openai for v in OPENAI_MODELS.values()}
# Utilities

def chat() -> None:
    """Main chat function that interfaces with the OpenAI API."""

    # Initialize the OpenAI client with API key from the environment
    client = openai.OpenAI()

    messages = [START_MESSAGE]
    enabled = False
    model = "gpt-3.5-turbo"
    context = Context()

    try:
        while True:
            message = context.next("user:")

            if message is None:
                print("Goodbye!")
                context.save()
                break

            if message == "enable":
                enabled = True
                messages = [START_MESSAGE]
                continue
            if message == "disable":
                enabled = False
                continue
            if message == "quit":
                break
            if message in ("reset", "restart"):
                messages = [START_MESSAGE]
                print("Chat restarted.")
                continue
            if message in OPENAI_MODELS:
                model = OPENAI_MODELS[message]
                print(f"Model set to {model}.")
                continue
            if message.startswith("system "):
                messages.append({
                    "role": "system",
                    "content": message[7:],
                })
                continue

            logger.debug(f"Sending message: {message}")

            messages.append({
                "role": "user",
                "content": message,
            })

            print("\nAssistant:")
            if enabled:
                response = COMPLETION[model](CompletionContext(
                    openai_client=client,
                    messages=messages,
                ))
            else:
                print("OpenAI is disabled. Type 'enable' to enable.")
                print("You wrote:")
                print("```")
                print(message)
                print("```", end="\n\n")
                continue
            print("\n")
            messages.append({
                "role": "assistant",
                "content": response,
            })
            
    except KeyboardInterrupt:
        logger.info("Chat terminated by user.")

if __name__ == "__main__":
    chat()
