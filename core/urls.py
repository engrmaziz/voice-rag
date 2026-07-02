from django.contrib import admin
from django.urls import path, include
from chat.views import get_or_create_conversation
from chat.views import chat_interface

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/chat/init/', get_or_create_conversation),
    path('', chat_interface, name='chat'),
]