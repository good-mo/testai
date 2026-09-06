# Auth Repository
from app.repositories.base import BaseRepo

class AuthRepo(BaseRepo):
    db_name = "tga.db"
    
    @classmethod
    def authenticate(cls, username, password):
        return None
    
    @classmethod
    def create_session(cls, user_id, **kwargs):
        return {}
    
    @classmethod
    def get_session_user(cls, token):
        return None
    
    @classmethod
    def delete_session(cls, token):
        return True
    
    @classmethod
    def cleanup_expired_sessions(cls):
        return 0
    
    @classmethod
    def update_user(cls, user_id, **kwargs):
        return True
    
    @classmethod
    def delete_user(cls, user_id):
        return True
    
    @classmethod
    def get_rsa_public_key(cls):
        return ""
    
    @classmethod
    def rsa_decrypt(cls, data):
        return data

auth_repo = AuthRepo()
