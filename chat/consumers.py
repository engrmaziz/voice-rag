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

async def run_pipeline(text_input, conversation_id):
    """Runs the LangGraph brain with either transcribed voice or typed text"""
    conversation, chat_history = await get_conversation_history(conversation_id)
    
    final_state = await app_graph.ainvoke({
        "question": text_input,
        "chat_history": chat_history,
        "documents": [],
        "generation": "",
        "retry_count": 0,
        "sources": []
    })
    
    answer_text = final_state.get("generation", "")
    sources = final_state.get("sources", [])
    
    await save_messages(conversation, text_input, answer_text, sources)
    
    return {
        "question": text_input,
        "answer": answer_text
    }

class VoiceConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        await self.send(text_data=json.dumps({
            "type": "system",
            "message": "Neural link established. Awaiting voice or text input."
        }))

    async def disconnect(self, close_code):
        pass

    async def receive(self, text_data=None, bytes_data=None):
        # Extract conversation_id from route kwargs if present
        conversation_id = None
        if 'url_route' in self.scope and 'kwargs' in self.scope['url_route']:
            conversation_id = self.scope['url_route']['kwargs'].get('conversation_id')

        # 1. HANDLE TYPED TEXT FROM UI
        if text_data:
            data = json.loads(text_data)
            question = data.get("question")
            
            if question:
                await self.send(text_data=json.dumps({"type": "status", "message": "Processing text..."}))
                result = await run_pipeline(question, conversation_id)
                await self.send(text_data=json.dumps(result))

        # 2. HANDLE RAW VOICE BYTES FROM UI
        elif bytes_data:
            audio_path = None
            try:
                await self.send(text_data=json.dumps({"type": "status", "message": "Transcribing audio..."}))
                
                # Save the bytes to a temp file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.webm') as tmp_file:
                    tmp_file.write(bytes_data)
                    audio_path = tmp_file.name
                
                # Transcribe with Whisper
                client = AsyncGroq()
                with open(audio_path, "rb") as file:
                    transcription = await client.audio.transcriptions.create(
                        file=(os.path.basename(audio_path), file.read()),
                        model="whisper-large-v3",
                    )
                transcribed_text = transcription.text
                
                await self.send(text_data=json.dumps({"type": "status", "message": f"Heard: '{transcribed_text}'. Thinking..."}))
                
                # Run the pipeline with the transcribed text
                result = await run_pipeline(transcribed_text, conversation_id)
                await self.send(text_data=json.dumps(result))
                
            except Exception as e:
                await self.send(text_data=json.dumps({"error": str(e)}))
                
            finally:
                if audio_path and os.path.exists(audio_path):
                    os.remove(audio_path)