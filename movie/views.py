from django.shortcuts import render
from django.http import HttpResponse
from .models import Movie 

import matplotlib.pyplot as plt
import matplotlib
import io 
import urllib,base64

import io
import base64
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from collections import Counter
from django.shortcuts import render
from movie.models import Movie


# Create your views here.

def home(request):
    #return HttpResponse("<h1>Welcome to the Movie Reviews Home Page!</h1>")
    #return render(request, 'home.html')
    #return render(request, 'home.html', {'name': 'Laura Andrea Castrillón Fajardo'})
    #searchTerm = request.GET.get('searchMovie')
    #movies = Movie.objects.all()
    #return render(request, 'home.html', {'searchTerm': searchTerm, 'movies': movies})
    searchTerm = request.GET.get('searchMovie')
    if searchTerm:
        movies = Movie.objects.filter(title__icontains=searchTerm)
    else:
        movies = Movie.objects.all()
    return render(request, 'home.html', {'searchTerm': searchTerm, 'movies': movies})

def about(request):
    return render(request, 'about.html')

def signup(request):
    email = request.GET.get('email')
    return render(request, 'signup.html', {'email': email})


def _figure_to_base64():
    """Convierte la figura actual de matplotlib a base64 y la cierra."""
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    img = base64.b64encode(buf.getvalue()).decode('utf-8')
    buf.close()
    plt.close()
    return img


def statistics_view(request):
    # Trae solo los campos que necesitas
    rows = Movie.objects.values('year', 'genre')

    year_counts = Counter()
    genre_counts = Counter()

    for r in rows:
        year = r['year'] if r['year'] else 'None'
        year_counts[year] += 1

        # Si el género viene separado por comas, cuenta cada uno
        genre_raw = r['genre'] if r['genre'] else 'Unknown'
        for g in str(genre_raw).split(','):
            g = g.strip()
            if g:
                genre_counts[g] += 1

    # ---- Grafica: Movies per year ----
    def parse_year(y):
        try:
            return int(y)
        except (TypeError, ValueError):
            return float('inf')  # "None" al final

    year_labels = sorted(year_counts.keys(), key=parse_year)
    year_values = [year_counts[k] for k in year_labels]

    plt.figure(figsize=(10, 5))
    pos = range(len(year_labels))
    plt.bar(pos, year_values, width=0.5, align='center')
    plt.title('Movies per year')
    plt.xlabel('Year')
    plt.ylabel('Number of movies')
    plt.xticks(pos, year_labels, rotation=90)
    plt.subplots_adjust(bottom=0.3)
    graphic_year = _figure_to_base64()

    # ---- Grafica: Movies per genre ----
    genre_labels = sorted(genre_counts.keys())
    genre_values = [genre_counts[k] for k in genre_labels]

    plt.figure(figsize=(10, 5))
    pos = range(len(genre_labels))
    plt.bar(pos, genre_values, width=0.5, align='center')
    plt.title('Movies per genre')
    plt.xlabel('Genre')
    plt.ylabel('Number of movies')
    plt.xticks(pos, genre_labels, rotation=45, ha='right')
    plt.subplots_adjust(bottom=0.3)
    graphic_genre = _figure_to_base64()

    return render(
        request,
        'statistics.html',
        {'graphic_year': graphic_year, 'graphic_genre': graphic_genre}
    )
