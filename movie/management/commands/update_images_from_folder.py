import os
import re
import unicodedata
from difflib import get_close_matches
from django.core.management.base import BaseCommand
from movie.models import Movie


class Command(BaseCommand):
    help = "Assign images from media/movie/images/ folder to movies in the database (tolerant matching)"

    def handle(self, *args, **kwargs):
        images_folder = os.path.join('media', 'movie', 'images')
        if not os.path.exists(images_folder):
            self.stderr.write(f"Images folder '{images_folder}' not found.")
            return

        # Indexa los archivos existentes una sola vez
        all_files = [f for f in os.listdir(images_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
        all_files_lower = {f.lower(): f for f in all_files}  # mapa para recuperar el nombre real con mayúsculas
        # También un conjunto sin extensión para matching rápido
        basenames_noext_lower = {os.path.splitext(f.lower())[0]: f for f in all_files}

        self.stdout.write(f"Found {len(all_files)} image files in folder")

        updated = 0
        movies = Movie.objects.all()
        self.stdout.write(f"Found {movies.count()} movies in database")

        for movie in movies:
            # Genera variantes de nombre que podríamos encontrar en el folder
            variants = self._filename_variants(movie.title)

            found_file = None

            # 1) Búsqueda exacta por cada variante (case-insensitive)
            for base in variants:
                # probamos varias extensiones típicas
                for ext in ('.png', '.jpg', '.jpeg', '.webp'):
                    candidate = f"{base}{ext}"
                    m_candidate = f"m_{candidate}"
                    # intentamos con prefijo 'm_'
                    if m_candidate.lower() in all_files_lower:
                        found_file = all_files_lower[m_candidate.lower()]
                        break
                    # intentamos sin 'm_'
                    if candidate.lower() in all_files_lower:
                        found_file = all_files_lower[candidate.lower()]
                        break
                if found_file:
                    break

            # 2) Si no hay exacto, probamos fuzzy contra los basenames
            if not found_file:
                # Tomamos referencia principal (la primera variante sin extensión)
                ref = variants[0]
                # Generamos las dos opciones con y sin prefijo m_
                candidates = list(basenames_noext_lower.keys())
                for ref_try in (ref, f"m_{ref}"):
                    close = get_close_matches(ref_try.lower(), candidates, n=1, cutoff=0.75)
                    if close:
                        found_file = basenames_noext_lower[close[0]]
                        break

            if found_file:
                # Actualiza ruta relativa como la espera tu app
                rel_path = os.path.join('movie', 'images', found_file)
                movie.images = rel_path
                movie.save()
                updated += 1
                self.stdout.write(self.style.SUCCESS(f"Updated: {movie.title} → {found_file}"))
            else:
                # Mensaje de ayuda con todas las variantes probadas
                self.stderr.write(f"Image not found for: {movie.title} (tried: {', '.join([f'm_{v}.png' for v in variants[:3]])}...)")

        self.stdout.write(self.style.SUCCESS(f"Finished updating {updated} movies."))

    # ---------- Normalización y variantes ----------

    def _normalize_ascii(self, s: str) -> str:
        """
        Quita acentos/diacríticos y deja ASCII puro.
        """
        if not s:
            return s
        s = unicodedata.normalize('NFKD', s)
        s = s.encode('ascii', 'ignore').decode('ascii')
        return s

    def _basic_clean(self, s: str) -> str:
        """
        Limpia puntuación problemática y espacios. Mantiene letras/números/_/-/./
        """
        s = s.strip()
        # Reemplaza separadores comunes por espacio
        s = s.replace('’', "'").replace('‘', "'").replace('“', '"').replace('”', '"')
        s = s.replace('&', ' and ')
        # Elimina signos que suelen no estar en los archivos
        s = re.sub(r"[^\w\s\.-]", " ", s)  # fuera de \w (alfa-numérico y _), espacio, . y -
        s = re.sub(r"\s+", " ", s).strip()
        return s

    def _to_filename_core(self, title: str) -> str:
        """
        Convierte el título a núcleo de nombre tipo 'Alice_in_Wonderland'
        (sin prefijo 'm_' ni extensión).
        """
        s = self._normalize_ascii(title)
        s = self._basic_clean(s)
        # Une con underscore
        s = s.replace(' ', '_')
        # Evita dobles underscores
        s = re.sub(r"_+", "_", s)
        return s

    def _filename_variants(self, title: str):
        """
        Genera un conjunto de variantes probables del basename (sin extensión),
        para cubrir diferencias de punctuación/idioma.
        """
        base = self._to_filename_core(title)

        variants = set()
        variants.add(base)

        # Variante sin 'The_' inicial
        if base.lower().startswith('the_'):
            variants.add(base[4:])

        # Variante sin artículo en español 'El_', 'La_', 'Los_', 'Las_'
        for art in ('el_', 'la_', 'los_', 'las_'):
            if base.lower().startswith(art):
                variants.add(base[len(art):])

        # Variante sin artículos en francés 'le_', 'la_', 'les_', ni apóstrofos
        for art in ('le_', 'la_', 'les_'):
            if base.lower().startswith(art):
                variants.add(base[len(art):])

        # Variante con guiones en vez de underscores (por si los archivos vienen así)
        variants.add(base.replace('_', '-'))

        # Variante sin palabras muy cortas problemáticas (como a/of/the)
        tokens = base.split('_')
        if len(tokens) > 2:
            filtered = [t for t in tokens if t.lower() not in {'a', 'of', 'the', 'and'}]
            if filtered:
                variants.add('_'.join(filtered))

        # Variante recortada si hay dos puntos / guiones largos (títulos con subtítulo)
        if '_' in base:
            variants.add(base.split('_', 1)[0])

        # Devuelve en orden estable (primera es la más “fiel”)
        return [v for v in [base] + list(variants - {base}) if v]
    
