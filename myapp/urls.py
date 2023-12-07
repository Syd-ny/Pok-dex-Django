from . import views
from django.urls import path, include

urlpatterns = [
    path('admin/', views.index, name='index'),
    # path('blog/<str:name>/<int:number>',views.blog, name='blog'),
    path('info/',views.info, name='info'),
    path('index/',views.index, name='index'),
]
