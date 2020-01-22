from imdb import IMDb

ia = IMDb()

try:
    from .secrets import get_ia

    ia_s3 = get_ia()
except ImportError:
    ia_s3 = None
