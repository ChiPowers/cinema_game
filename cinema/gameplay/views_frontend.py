from django.shortcuts import render

def actor_chain_game_page(request):
    return render(request, 'gameplay/actor_chain_game.html')
