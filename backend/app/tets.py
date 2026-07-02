from google import genai

client = genai.Client(
    api_key="AIzaSyBf8Ktlu_Wlx9yjXyd7PovHMjuPhCk-dss"
)

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="Hello"
)

print(response.text)