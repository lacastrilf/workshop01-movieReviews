import numpy as np
import os
from dotenv import load_dotenv
from openai import OpenAI
from movie.models import Movie

# Cargar API Key
load_dotenv("openAI.env")
client = OpenAI(api_key=os.environ.get("openai_apikey"))

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def get_best_movie(prompt: str):
    # Generar embedding del prompt
    response = client.embeddings.create(
        input=[prompt],
        model="text-embedding-3-small"
    )
    prompt_emb = np.array(response.data[0].embedding, dtype=np.float32)

    best_movie = None
    max_similarity = -1

    for movie in Movie.objects.all():
        movie_emb = np.frombuffer(movie.emb, dtype=np.float32)
        similarity = cosine_similarity(prompt_emb, movie_emb)

        if similarity > max_similarity:
            max_similarity = similarity
            best_movie = movie

    return best_movie
