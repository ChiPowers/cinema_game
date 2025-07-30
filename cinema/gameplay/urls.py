from django.urls import path
from . import views
from . import views_frontend

urlpatterns = [
    path('start/', views.start_game, name='start_game'),
    path('validate/', views.validate_chain, name='validate_chain'),
    path('play/', views_frontend.actor_chain_game_page, name='actor_chain_game'),
]
