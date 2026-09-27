from harness.llm_client import groq_client, GROQ_MODEL
resp = groq_client.chat.completions.create(
    model=GROQ_MODEL,
    messages=[{"role": "user", "content": "say hi"}],
)
print(resp.choices[0].message.content)