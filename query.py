import ollama

def query(query):
    response = ollama.chat(model='qwen2', messages=[
        {
            'role':'user',
            'content': query + "-- answer in less than 25 words",  
        },
    ])

    return response['message']['content']

