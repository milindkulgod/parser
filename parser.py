from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
import requests
from pydantic import BaseModel
import json
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Allow frontend to access backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (Change this for production)
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)
# Define request body model
class RequestBody(BaseModel):
    content: str

# External API URL
EXTERNAL_API_URL = "https://www.tallite.com/api_uat/icrweb/home/tallite_gpt_prompt"

# Required headers (replace with actual values)
HEADERS = {
    "Accept": "*/*",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "clientid": "2d1007980f49215311f7",  # Replace with correct client ID if dynamic
    "timestamp": "1739047420122",  # Generate dynamically if required
    "hash": "8eacc07f7c5c2cdaa567d82d7cdbc46bca27e952e4f7a836b34d761002db9930c84dbc36136fcf29f054034d6bead1cb207209a662e8adef72c59c371033fb63",  # Replace with the actual hash
}

@app.post("/call-api")
async def call_external_api(data: RequestBody):
    payload = {"content": data.content}
    response_text = ""

    try:
        response = requests.post(EXTERNAL_API_URL, json=payload, headers=HEADERS)
        
        # Process the response data
        for line in response.text.split("\n"):
            if line.startswith("data: "):  # Ensure we process only valid JSON lines
                try:
                    json_data = json.loads(line[6:])  # Remove "data: " prefix and parse JSON
                    if "choices" in json_data and json_data["choices"]:
                        delta = json_data["choices"][0].get("delta", {})
                        if "content" in delta:
                            response_text += delta["content"]  # Append content fragments
                except json.JSONDecodeError:
                    continue  # Skip any malformed JSON lines

        if response.status_code == 200:
            return PlainTextResponse(response_text)
        else:
            return {
                "status_code": response.status_code,
                "error": "Request failed",
                "details": response.text
            }
    
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))
