from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
import requests
import json
import asyncio
import re
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import logging
from requests.exceptions import ChunkedEncodingError, ReadTimeout, RequestException

# Initialize FastAPI app
app = FastAPI()
logging.basicConfig(level=logging.INFO)

# Allow frontend to access backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, restrict origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define request body model
class RequestBody(BaseModel):
    content: str

# External API URL and headers (replace with actual values as needed)
EXTERNAL_API_URL = "https://www.tallite.com/api_uat/icrweb/home/tallite_gpt_prompt"
HEADERS = {
    "Accept": "*/*",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "clientid": "2d1007980f49215311f7",
    "timestamp": "1739047420122",
    "hash": "8eacc07f7c5c2cdaa567d82d7cdbc46bca27e952e4f7a836b34d761002db9930c84dbc36136fcf29f054034d6bead1cb207209a662e8adef72c59c371033fb63",
}

def clean_text(text: str) -> str:
    """
    Cleans and formats the text to match the desired Markdown output.
    Ensures proper spacing for headings and paragraphs.
    """
    # Remove extra spaces at the end of lines
    text = re.sub(r"[ \t]+(\n)", r"\1", text)
    # Ensure headings have a blank line after them
    text = re.sub(r"^(#+ .+)$", r"\1\n", text, flags=re.MULTILINE)
    # Ensure there is a blank line before headings if not already present
    text = re.sub(r"\n(#+ )", r"\n\n\1", text, flags=re.MULTILINE)
    # Normalize paragraph breaks to exactly two newlines
    text = re.sub(r"\n\s*\n", "\n\n", text)
    return text.strip()

async def stream_response(content: str):
    
    payload = {"content": content}
    buffer = ""
    try:
        # Set a connect timeout of 3 seconds and a read timeout of 60 seconds
        with requests.post(EXTERNAL_API_URL, json=payload, headers=HEADERS, stream=True, timeout=(3, 60)) as response:
            if response.status_code != 200:
                yield "data: [ERROR] Request failed with status code {}\n\n".format(response.status_code)
                return

            try:
                for line in response.iter_lines():
                    if line:
                        decoded_line = line.decode("utf-8").strip()
                        # Process only lines starting with "data: "
                        if decoded_line.startswith("data: "):
                            try:
                                json_data = json.loads(decoded_line[6:].strip())
                                if "choices" in json_data and json_data["choices"]:
                                    delta = json_data["choices"][0].get("delta", {})
                                    if "content" in delta:
                                        buffer += delta["content"]
                                        words = buffer.split(" ")
                                        if len(words) > 1:
                                            cleaned_text = clean_text(" ".join(words[:-1]))
                                            yield f"data: {cleaned_text}\n\n"
                                            buffer = words[-1]
                                        await asyncio.sleep(0.05)
                            except json.JSONDecodeError:
                                logging.warning("Malformed JSON received: %s", decoded_line)
                                continue
            except (ChunkedEncodingError, ReadTimeout) as e:
                logging.warning("Stream ended unexpectedly: %s", e)
            if buffer:
                cleaned_text = clean_text(buffer)
                yield f"data: {cleaned_text}\n\n"
    except RequestException as e:
        logging.error("Request to external API failed: %s", e)
        yield "data: [ERROR] The request has timed out. Please try again later.\n\n"

@app.post("/call-api", response_class=StreamingResponse)
async def call_external_api(data: RequestBody):
    if not data.content.strip():
        raise HTTPException(status_code=400, detail="Content cannot be empty.")
    return StreamingResponse(stream_response(data.content), media_type="text/event-stream")
