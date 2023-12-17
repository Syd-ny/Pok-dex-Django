from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PokemonViewSet

router = DefaultRouter()
router.register(r'pokemon', PokemonViewSet)

urlpatterns = [
    path('', include(router.urls)),
    # path('blog/<str:name>/<int:number>',views.blog, name='blog'),
    #path('info/',views.info, name='info'),
    #path('index/',views.index, name='index'),
]
