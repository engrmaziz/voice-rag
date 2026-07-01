import json
import tempfile
import os
from channels.generic.websocket import AsyncWebsocketConsumer
from groq import AsyncGroq
from asgiref.sync import sync_to_async
from chat.models import Conversation, Message
from graph.build import app_graph

@sync_to_async
def get_conversation_history(conversation_id):
    if not conversation_id:
        return None, []
    
    try:
        conversation = Conversation.objects.get(id=conversation_id)
        messages = list(conversation.messages.order_by('created_at'))
        chat_history = [f"{msg.role}: {msg.content}" for msg in messages]
        return conversation, chat_history
    except Conversation.DoesNotExist:
        return None, []

@sync_to_async
def save_messages(conversation, question_text, answer_text, sources=None):
    if not conversation:
        return
    
    Message.objects.create(
        conversation=conversation,
        role='user',
        content=question_text
    )
    
    Message.objects.create(
        conversation=conversation,
        role='assistant',
        content=answer_text,
        retrieved_sources=sources or []
    )

async def run_pipeline(audio_path, conversation_id):
    client = AsyncGroq()
    
    with open(audio_path, "rb") as file:
        transcription = await client.audio.transcriptions.create(
            file=(audio_path, file.read()),
            model="whisper-large-v3",
        )
    transcribed_text = transcription.text
    
    conversation, chat_history = await get_conversation_history(conversation_id)
    
    final_state = await app_graph.ainvoke({
        "question": transcribed_text,
        "chat_history": chat_history,
        "documents": [],
        "generation": "",
        "retry_count": 0,
        "sources": []
    })
    
    answer_text = final_state.get("generation", "")
    sources = final_state.get("sources", [])
    
    await save_messages(conversation, transcribed_text, answer_text, sources)
    
    return {
        "question": transcribed_text,
        "answer": answer_text
    }

class VoiceConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()

    async def disconnect(self, close_code):
        pass

    async def receive(self, text_data=None, bytes_data=None):
        if bytes_data:
            try:
                # Save the bytes to a temp file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.webm') as tmp_file:
                    tmp_file.write(bytes_data)
                    audio_path = tmp_file.name
                
                # Optional: Extract conversation_id from route kwargs if present
                conversation_id = None
                if 'url_route' in self.scope and 'kwargs' in self.scope['url_route']:
                    conversation_id = self.scope['url_route']['kwargs'].get('conversation_id')
                
                # Call the placeholder async function
                result = await run_pipeline(audio_path, conversation_id)
                
                # Clean up the temp file
                if os.path.exists(audio_path):
                    os.remove(audio_path)
                
                # Send the dict back to the client as JSON
                await self.send(text_data=json.dumps(result))
                
            except Exception as e:
                # Handle exceptions without crashing the socket
                await self.send(text_data=json.dumps({"error": str(e)}))
