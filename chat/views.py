from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from chat.models import Conversation
from chat.serializers import ConversationSerializer
# Create your views here.
class ConversationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]
    def get_queryset(self):
        return Conversation.objects.filter(owner=self.request.user).order_by('-created_at')
