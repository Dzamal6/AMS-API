import requests

from config import VERSION_ID, DIALOG_API_KEY, PROJECT_API_KEY
from voiceflow_functions import handle_response

DIALOG_HEADERS = {
  "accept": "application/json",
  "versionID": f'{VERSION_ID}',
  "content-type": "application/json",
  "Authorization": f"Bearer {DIALOG_API_KEY}"
}

PROJECT_HEADERS = {
    "accept": "application/json",
    "content-type": "application/json",
    "Authorization": f"{PROJECT_API_KEY}"
}


def post_launch_request(user_id: str) -> dict:
  url = f"https://general-runtime.voiceflow.com/state/user/{user_id}/interact?logs=off"
  payload = {
    "action": {
      "type": "launch"
    },
    "config": {
      "tts": False,
      "stripSSML": True,
      "stolAll": True,
      "excludeTypes": ["block", "debug", "flow"]
    }
  }

  response = requests.post(url, json=payload, headers=DIALOG_HEADERS)
  return handle_response(response)

def fetch_state(user_id: str) -> dict:
  url = f"https://general-runtime.voiceflow.com/state/user/{user_id}"
  
  response = requests.get(url, headers=DIALOG_HEADERS)
  return response.json()

def delete_state(user_id: str) -> dict:
  url = f"https://general-runtime.voiceflow.com/state/user/{user_id}"

  response = requests.delete(url, headers=DIALOG_HEADERS)
  return response.json()

def post_text(user_id: str, text: str) -> dict:
  url = f"https://general-runtime.voiceflow.com/state/user/{user_id}/interact?logs=off"
  payload = {"action": {"type": "text", "payload": text}}

  response = requests.post(url, json=payload, headers=DIALOG_HEADERS)
  return handle_response(response)


def post_button(user_id: str, button_id: str) -> dict:
  url = f"https://general-runtime.voiceflow.com/state/user/{user_id}/interact?logs=off"
  payload = {"action": {"type": button_id}}

  response = requests.post(url, json=payload, headers=DIALOG_HEADERS)
  return handle_response(response)

def update_variable(user_id: str, key: str, value: str):
  url = f"https://general-runtime.voiceflow.com/state/user/{user_id}/variables"
  payload = {key: value}
  requests.patch(url, json=payload, headers=DIALOG_HEADERS)
  return "Variable succesfully updated"

def create_transcript(sessionID: str, projectID, device, oss,
  browser):
  url = "https://api.voiceflow.com/v2/transcripts"
  payload = {
  "versionID": VERSION_ID,
  "sessionID": sessionID,
  }
  optional_params = {
  "projectID": projectID,
  "device": device,
  "os": oss,
  "browser": browser
  }
  payload.update({k: v for k, v in optional_params.items() if v is not None})
  print(url, payload, DIALOG_HEADERS)
  response = requests.put(url, json=payload, headers=PROJECT_HEADERS)
  return response.json()
