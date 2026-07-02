from django.http import JsonResponse
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from chat.models import Conversation
from chat.serializers import ConversationSerializer
from django.shortcuts import render

def chat_interface(request):
    return render(request, 'chat/index.html')


class ConversationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]
    def get_queryset(self):
        return Conversation.objects.filter(owner=self.request.user).order_by('-created_at')

async def get_or_create_conversation(request):
    """
    Returns an existing conversation ID or creates a new one.
    """
    conversation_id = request.GET.get('conversation_id')
    
    if conversation_id:
        try:
            conversation = await Conversation.objects.aget(id=conversation_id)
            return JsonResponse({'conversation_id': conversation.id})
        except Conversation.DoesNotExist:
            return JsonResponse({'error': 'Conversation not found'}, status=404)
    
    # Create a new conversation (owner=None for now as requested)
    conversation = await Conversation.objects.acreate(owner=None)
    return JsonResponse({'conversation_id': conversation.id})
