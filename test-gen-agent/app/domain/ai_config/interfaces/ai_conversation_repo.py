# AI Conversation Repository
from app.repositories.base import BaseRepo

class AiConversationRepo(BaseRepo):
    db_name = "tga.db"
    
    @classmethod
    def list_conversations(cls, user_id="", limit=100, offset=0):
        return []
    
    @classmethod
    def get_conversation(cls, conversation_id):
        return None
    
    @classmethod
    def create_conversation(cls, user_id, title="", model_id="", **kwargs):
        return {}
    
    @classmethod
    def update_conversation(cls, conversation_id, **kwargs):
        return True
    
    @classmethod
    def delete_conversation(cls, conversation_id):
        return True
    
    @classmethod
    def add_message(cls, conversation_id, role, content, **kwargs):
        return {}
    
    @classmethod
    def list_messages(cls, conversation_id, limit=100):
        return []

ai_conversation_repo = AiConversationRepo()
