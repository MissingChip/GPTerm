#!/usr/bin/env python3

from typing import List
import logging
from dotenv import load_dotenv
from gpterm.entry import get_input
import openai

# Setup logging
logging.basicConfig(level=logging.WARN)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
# Constants
# MODELS = ["gpt-3.5", "gpt-3.5-turbo", "gpt-4", "gpt-4-1106-preview"]
MODELS = {
    "gpt-3.5": "gpt-3.5",
    "gpt-3.5-turbo": "gpt-3.5-turbo",
    "gpt-4": "gpt-4",
    "gpt-4-turbo": "gpt-4-1106-preview",
}
SYSTEM = "You are helpful assistant. Respond with short, single sentence answers unless asked to elaborate."
START_MESSAGE = {
    "role": "system",
    "content": SYSTEM,
}

# Utilities

def chat() -> None:
    """Main chat function that interfaces with the OpenAI API."""

    # Initialize the OpenAI client with API key from the environment
    client = openai.OpenAI()

    messages = [START_MESSAGE]
    enabled = True
    model = "gpt-3.5-turbo"

    try:
        while True:
            message = get_input()

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
            if message in MODELS:
                model = MODELS[message]
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

            if enabled:
                try:
                    response = ""
                    stream = client.chat.completions.create(
                        messages=messages,
                        model=model,
                        stream=True,
                    )
                    logger.info(stream)
                    for part in stream:
                        if part.choices[0].finish_reason == "stop":
                            break
                        content = part.choices[0].delta.content
                        response += content
                        print(content, end="")
                except openai.OpenAIError as e:
                    logger.error(f"An API error occurred: {e}")
            else:
                response = "OpenAI is disabled. Type 'enable' to enable."
                print(response, end="")
            print("\n")
            messages.append({
                "role": "assistant",
                "content": response,
            })
    except KeyboardInterrupt:
        logger.info("Chat terminated by user.")

if __name__ == "__main__":
    chat()