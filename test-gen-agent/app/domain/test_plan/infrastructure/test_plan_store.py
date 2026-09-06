"""测试计划上下文 SQLite 存储。"""
from __future__ import annotations
import json,time
from app.core.database import Database
class TestPlanStore:
 def __init__(self):
  c=Database.get_conn('tga.db');c.execute("CREATE TABLE IF NOT EXISTS domain_test_plans (id TEXT PRIMARY KEY,name TEXT,description TEXT,priority TEXT,module_id TEXT,project_id TEXT,created_by TEXT,status TEXT DEFAULT 'draft',tags TEXT DEFAULT '[]',start_time REAL,end_time REAL,pass_threshold REAL DEFAULT 0,test_planning INTEGER DEFAULT 1,auto_update_status INTEGER DEFAULT 0,repeat_case INTEGER DEFAULT 0,type TEXT DEFAULT 'FUNCTIONAL',group_id TEXT DEFAULT '',created_at REAL,updated_at REAL)");c.commit()
 def get_plan(self,i):
  r=Database.get_conn('tga.db').execute('SELECT * FROM domain_test_plans WHERE id=?',(i,)).fetchone();return self._d(r)
 def _d(self,r):
  if not r:return None
  x=dict(r)
  try:x['tags']=json.loads(x.get('tags') or '[]')
  except:x['tags']=[]
  return x
 def list_plans(self,keyword='',status='',project_id='',module_ids=None,limit=100,offset=0,type='',group_id=''):
  q='SELECT * FROM domain_test_plans WHERE 1=1';p=[]
  if keyword:q+=' AND name LIKE ?';p.append(f'%{keyword}%')
  if status:q+=' AND status=?';p.append(status)
  if project_id:q+=' AND project_id=?';p.append(project_id)
  p += [max(1,limit),max(0,offset)];return [self._d(r) for r in Database.get_conn('tga.db').execute(q+' ORDER BY updated_at DESC LIMIT ? OFFSET ?',p).fetchall()]
 def count_plans(self,**kw):return len(self.list_plans(**{k:v for k,v in kw.items() if k in ('keyword','status','project_id','module_ids','limit','offset','type','group_id')},limit=100000))
 def update_plan(self,i,**d):
  old=self.get_plan(i)
  if not old:return None
  x={**old,**d};c=Database.get_conn('tga.db');c.execute('UPDATE domain_test_plans SET name=?,description=?,priority=?,module_id=?,status=?,tags=?,pass_threshold=?,updated_at=? WHERE id=?',(x.get('name',''),x.get('description',''),x.get('priority',''),x.get('module_id',''),x.get('status','draft'),json.dumps(x.get('tags',[])),x.get('pass_threshold',0),time.time(),i));c.commit();return self.get_plan(i)
 def delete_plan(self,i):
  c=Database.get_conn('tga.db');cur=c.execute('DELETE FROM domain_test_plans WHERE id=?',(i,));c.commit();return cur.rowcount>0
 def archive_plan(self,i):return bool(self.update_plan(i,status='archived'))
 def get_plan_statistics(self,i):return {'plan_id':i,'total':0}
 def get_plans_statistics(self,ids):return {i:self.get_plan_statistics(i) for i in ids}
DB_NAME='tga.db';TestPlanRepo=TestPlanStore()
