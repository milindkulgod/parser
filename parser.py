from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
import requests
import json
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from typing import AsyncGenerator

app = FastAPI()

# Allow frontend to access backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RequestBody(BaseModel):
    content: str

EXTERNAL_API_URL = "https://www.tallite.com/api_uat/icrweb/home/tallite_gpt_prompt"

HEADERS = {
    "Accept": "*/*",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "clientid": "2d1007980f49215311f7",
    "timestamp": "1739047420122",
    "hash": "8eacc07f7c5c2cdaa567d82d7cdbc46bca27e952e4f7a836b34d761002db9930c84dbc36136fcf29f054034d6bead1cb207209a662e8adef72c59c371033fb63",
}

async def stream_response(data: RequestBody) -> AsyncGenerator[str, None]:
    payload = {"content": data.content}

    try:
        response = requests.post(EXTERNAL_API_URL, json=payload, headers=HEADERS, stream=True)
        response.raise_for_status()

        for line in response.iter_lines(decode_unicode=True):
            if line and line.startswith("data: "):
                try:
                    json_data = json.loads(line[6:])
                    if "choices" in json_data and json_data["choices"]:
                        delta = json_data["choices"][0].get("delta", {})
                        if "content" in delta:
                            yield delta["content"]  
                except json.JSONDecodeError:
                    continue  

    except requests.exceptions.RequestException as e:
        yield f"Error: {str(e)}"

@app.post("/call-api")
async def call_external_api(data: RequestBody):
    return StreamingResponse(stream_response(data), media_type="text/event-stream")
