from django.urls import path, include
from rest_framework.routers import DefaultRouter
from chat.views import ConversationViewSet
router = DefaultRouter()
router.register(r'api/conversations', ConversationViewSet, basename='conversation')
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include(router.urls)),
]