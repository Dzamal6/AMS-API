import openai.assistants as opa

def create_assistants(client):
  ta_objections_id = opa.create_ta_objections(client)
  ta_recommend_id = opa.create_ta_recommend(client)
  ta_analysis_01_id = opa.create_ta_analysis_01(client)
  ta_analysis_02_id = opa.create_ta_analysis_02(client)
  ta_analysis_03_id = opa.create_ta_analysis_03(client)

def chat_ta(assistant_id, assistant_name, thread_id, user_input):
# Token Counting Input
encoding = tiktoken.get_encoding("cl100k_base")
encoding = tiktoken.encoding_for_model("gpt-4")

inp_tokens = len(encoding.encode(user_input))
inp_cost_tok = (0.01 / 1000) * inp_tokens
print(
    f"Number of tokens input: {inp_tokens}\nCost of tokens: {inp_cost_tok}")

if not thread_id:
  print('Error: Missing thread_id')
  return jsonify({'error': 'missing thread_id'}), 400

print(f"Received message: '{user_input}' for thread ID: {thread_id}")

client.beta.threads.messages.create(thread_id=thread_id,
                                    role="user",
                                    content=user_input)
run = client.beta.threads.runs.create(thread_id=thread_id,
                                      assistant_id=assistant_id)
start_time = time.time()
while True:
  run_status = client.beta.threads.runs.retrieve(thread_id=thread_id,
                                                 run_id=run.id)

  if run_status.status == "completed":
    break

  if time.time() - start_time > 55:
    print("Timeout reached")
    return jsonify({'error': 'timeout'}), 400

messages = client.beta.threads.messages.list(thread_id=thread_id)
response = messages.data[0].content[0].text.value

print(f"Assistant Response: {response}")

# Token Counting Response
out_tokens = len(encoding.encode(response))
out_cost_tok = (0.03 / 1000) * out_tokens
print(
    f"Number of tokens response: {out_tokens}\nCost of tokens: {out_cost_tok}"
)

# Token Updates
update_assistant_tokens(assistant_name, inp_tokens, inp_cost_tok, out_tokens,
                        out_cost_tok)

return jsonify({'response': response})