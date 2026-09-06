"""资源池 SQLite 存储。"""
import time,uuid
from app.core.database import Database
class ResourcePoolStore:
 def __init__(self):
  c=Database.get_conn('tga.db');c.execute("CREATE TABLE IF NOT EXISTS domain_resource_pools (id TEXT PRIMARY KEY,name TEXT,description TEXT,enable INTEGER,created_at REAL)");c.commit()
 def create(self,name='',description='',enable=True,pool_id=None):
  i=pool_id or str(uuid.uuid4());c=Database.get_conn('tga.db');c.execute('INSERT OR REPLACE INTO domain_resource_pools VALUES(?,?,?,?,?)',(i,name,description,int(enable),time.time()));c.commit();return self.get_by_id(i)
 def update(self,i,d):
  c=Database.get_conn('tga.db');c.execute('UPDATE domain_resource_pools SET name=?,description=?,enable=? WHERE id=?',(d.get('name',''),d.get('description',''),int(d.get('enable',1)),i));c.commit();return self.get_by_id(i)
 def get_by_id(self,i):
  r=Database.get_conn('tga.db').execute('SELECT * FROM domain_resource_pools WHERE id=?',(i,)).fetchone();return dict(r) if r else None
 def get_all(self,keyword=''):
  rows=Database.get_conn('tga.db').execute('SELECT * FROM domain_resource_pools WHERE name LIKE ?',(f'%{keyword}%',)).fetchall();return [dict(r) for r in rows]
 def delete(self,i):
  c=Database.get_conn('tga.db');cur=c.execute('DELETE FROM domain_resource_pools WHERE id=?',(i,));c.commit();return cur.rowcount>0
 def set_enable(self,i,enable):return bool(self.update(i,{'enable':enable}))
ResourcePoolRepo=ResourcePoolStore()
