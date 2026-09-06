# UserGroup Repository
from app.repositories.base import BaseRepo

class UserGroupRepo(BaseRepo):
    db_name = "tga.db"
    
    @classmethod
    def list_groups(cls, group_type="SYSTEM", scope_id=""):
        return []
    
    @classmethod
    def get_group(cls, group_id):
        return None
    
    @classmethod
    def update_group(cls, group_id, **kwargs):
        return True
    
    @classmethod
    def get_group_permissions(cls, group_id):
        return []
    
    @classmethod
    def update_group_permissions(cls, group_id, permissions):
        return True
    
    @classmethod
    def get_user_options(cls, exclude_group_id="", keyword=""):
        return []
    
    @classmethod
    def remove_user_org_memberships(cls, user_id):
        return 0

user_group_repo = UserGroupRepo()
