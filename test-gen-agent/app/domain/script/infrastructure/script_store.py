"""脚本上下文 SQLite 存储。"""
from __future__ import annotations
import json,time,uuid
from app.core.database import Database
class ScriptStore:
 def __init__(self):
  c=Database.get_conn('tga.db');c.execute("CREATE TABLE IF NOT EXISTS domain_scripts (id TEXT PRIMARY KEY,name TEXT,file_path TEXT,framework TEXT,description TEXT,locators TEXT,total_runs INTEGER DEFAULT 0,success_runs INTEGER DEFAULT 0,fail_runs INTEGER DEFAULT 0,last_run_at REAL,last_status TEXT,health_score REAL DEFAULT 0,status TEXT,created_at REAL,updated_at REAL)");c.execute("CREATE TABLE IF NOT EXISTS domain_script_executions (id TEXT PRIMARY KEY,script_id TEXT,success INTEGER,duration REAL,error_type TEXT,error_message TEXT,locator_failures TEXT,created_at REAL)");c.commit()
 def _d(self,r):
  if not r:return None
  x=dict(r)
  try:x['locators']=json.loads(x.get('locators') or '{}')
  except: x['locators']={}
  return x
 def register(self,**d):
  i=uuid.uuid4().hex[:12];n=time.time();c=Database.get_conn('tga.db');c.execute('INSERT INTO domain_scripts(id,name,file_path,framework,description,locators,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)',(i,d.get('name',''),d.get('file_path',''),d.get('framework',''),d.get('description',''),json.dumps(d.get('locators',{})), 'active',n,n));c.commit();return self.get(i)
 def get(self,i):return self._d(Database.get_conn('tga.db').execute('SELECT * FROM domain_scripts WHERE id=?',(i,)).fetchone())
 def list(self,status=None,search=None,limit=100,offset=0):
  q='SELECT * FROM domain_scripts WHERE 1=1';p=[]
  if status:q+=' AND status=?';p.append(status)
  if search:q+=' AND (name LIKE ? OR file_path LIKE ?)';p += [f'%{search}%',f'%{search}%']
  p += [max(1,limit),max(0,offset)];return [self._d(r) for r in Database.get_conn('tga.db').execute(q+' ORDER BY updated_at DESC LIMIT ? OFFSET ?',p).fetchall()]
 def update(self,i,**d):
  old=self.get(i)
  if not old:return None
  x={**old,**d};c=Database.get_conn('tga.db');c.execute('UPDATE domain_scripts SET name=?,file_path=?,framework=?,description=?,locators=?,total_runs=?,success_runs=?,fail_runs=?,last_run_at=?,last_status=?,health_score=?,status=?,updated_at=? WHERE id=?',(x.get('name',''),x.get('file_path',''),x.get('framework',''),x.get('description',''),json.dumps(x.get('locators',{})),x.get('total_runs',0),x.get('success_runs',0),x.get('fail_runs',0),x.get('last_run_at'),x.get('last_status',''),x.get('health_score',0),x.get('status','active'),time.time(),i));c.commit();return self.get(i)
 def delete(self,i):
  c=Database.get_conn('tga.db');cur=c.execute('DELETE FROM domain_scripts WHERE id=?',(i,));c.commit();return cur.rowcount>0
 def record_execution(self,script_id,success,duration,error_type='',error_message='',locator_failures=None):
  c=Database.get_conn('tga.db');c.execute('INSERT INTO domain_script_executions VALUES(?,?,?,?,?,?,?,?)',(uuid.uuid4().hex[:12],script_id,int(success),duration,error_type,error_message,json.dumps(locator_failures or []),time.time()));c.commit();return {'script_id':script_id,'success':success}
 def list_executions(self,script_id,limit=20):return [dict(r) for r in Database.get_conn('tga.db').execute('SELECT * FROM domain_script_executions WHERE script_id=? ORDER BY created_at DESC LIMIT ?',(script_id,limit)).fetchall()]
 def stats(self):return {'total':Database.get_conn('tga.db').execute('SELECT COUNT(*) FROM domain_scripts').fetchone()[0]}
 def evaluate_selector(self,strategy,selector):return {'strategy':strategy,'selector':selector,'valid':bool(selector)}
 def recommend_strategy(self,selector,strategy):return {'strategy':strategy,'selector':selector}
 def auto_repair(self,script_id,locator_name):return {'script_id':script_id,'locator_name':locator_name,'repaired':False}
ScriptRepo=ScriptStore()
