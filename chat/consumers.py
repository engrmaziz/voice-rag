import json
import tempfile
import os
from channels.generic.websocket import AsyncWebsocketConsumer

async def run_pipeline(audio_path, conversation_id):
    # Placeholder implementation
    return {
        "question": "What is the question?",
        "answer": "This is a placeholder answer.",
        "audio_url": "/media/placeholder_audio.mp3"
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
