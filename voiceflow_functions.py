def handle_response(response) -> dict:
  response = response.json()
  print(response)
  if isinstance(response, dict) and response.get('name') and response.get('name') == 'verror':
    print(f'---------ERROR: {response}---------')
    
  respond_text = response
  final_text = ""
  final_json = {}
  buttons = None
  for i, response in enumerate(respond_text):
    if response['type'] == 'choice':
      final_json[f'block-{i}'] = {'buttons': handle_buttons(response)}
      final_json[f'block-{i}']['type'] = response['type']

    elif response['type'] == "text":
      final_json[f'block-{i}'] = {"text": response['payload']['message']}
      final_json[f'block-{i}']['type'] = response['type']

    elif response['type'] == "visual":
      final_json[f'block-{i}'] = {"image": response['payload']['image']}
      final_json[f'block-{i}']['type'] = response['type']

    elif response['type'] == "cardV2":
      final_json[f'block-{i}'] = {"buttons": handle_buttons(response)}
      final_json[f'block-{i}']["image"] = {
          "title": response["payload"]["title"],
          "description": response["payload"]['description']['text'],
          "image": response["payload"]["imageUrl"]
      }
      final_json[f'block-{i}']['type'] = response['type']

  return final_json

def handle_buttons(buttons_response):
  buttons = buttons_response['payload']['buttons']
  buttons_array = []
  print(buttons)
  for button in buttons:
    buttons_array.append({
        "id": button['request']['type'],
        "name": button['name']
    })
  return buttons_array