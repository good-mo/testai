"""项目上下文 SQLite 存储。"""
from __future__ import annotations
import json, time, uuid
from app.core.database import Database

class ProjectStore:
    db_name = "tga.db"
    def __init__(self):
        c=Database.get_conn(self.db_name)
        c.execute("""CREATE TABLE IF NOT EXISTS domain_projects (id TEXT PRIMARY KEY,name TEXT NOT NULL,description TEXT NOT NULL DEFAULT '',repo_url TEXT NOT NULL DEFAULT '',language TEXT NOT NULL DEFAULT '',path TEXT NOT NULL DEFAULT '',organization_id TEXT NOT NULL DEFAULT '',status TEXT NOT NULL DEFAULT 'active',deleted INTEGER NOT NULL DEFAULT 0,created_at REAL NOT NULL,updated_at REAL NOT NULL)""")
        c.execute("""CREATE TABLE IF NOT EXISTS domain_project_members (id TEXT PRIMARY KEY,project_id TEXT NOT NULL,user_id TEXT NOT NULL,username TEXT NOT NULL DEFAULT '',name TEXT NOT NULL DEFAULT '',email TEXT NOT NULL DEFAULT '',role TEXT NOT NULL DEFAULT 'member',user_group TEXT NOT NULL DEFAULT '')""")
        c.execute("""CREATE TABLE IF NOT EXISTS domain_project_records (id TEXT PRIMARY KEY,project_id TEXT NOT NULL,kind TEXT NOT NULL,data TEXT NOT NULL)"""); c.commit()
    def _project(self,row): return dict(row) if row else None
    def next_id(self): return uuid.uuid4().hex[:12]
    def get(self,pid,include_deleted=False):
        q="SELECT * FROM domain_projects WHERE id=?"+('' if include_deleted else ' AND deleted=0'); return self._project(Database.get_conn(self.db_name).execute(q,(pid,)).fetchone())
    def list(self,search='',status='',limit=100,include_deleted=False):
        clauses=['deleted=?']; p=[int(include_deleted)]
        if search: clauses.append('name LIKE ?'); p.append(f'%{search}%')
        if status: clauses.append('status=?'); p.append(status)
        p.append(max(1,limit)); rows=Database.get_conn(self.db_name).execute(f"SELECT * FROM domain_projects WHERE {' AND '.join(clauses)} ORDER BY updated_at DESC LIMIT ?",p).fetchall(); return [self._project(x) for x in rows]
    def create(self,**d):
        pid=d.get('id') or self.next_id(); now=time.time(); c=Database.get_conn(self.db_name); c.execute("INSERT INTO domain_projects VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",(pid,d.get('name',''),d.get('description',''),d.get('repo_url',''),d.get('language',''),d.get('path',''),d.get('organization_id',''),d.get('status','active'),0,now,now)); c.commit(); return self.get(pid)
    def update(self,pid,d):
        old=self.get(pid,True)
        if not old:return None
        x={**old,**d,'updated_at':time.time()}; c=Database.get_conn(self.db_name); c.execute("UPDATE domain_projects SET name=?,description=?,repo_url=?,language=?,path=?,organization_id=?,status=?,updated_at=? WHERE id=?",(x['name'],x['description'],x['repo_url'],x['language'],x['path'],x['organization_id'],x['status'],x['updated_at'],pid)); c.commit(); return self.get(pid,True)
    def delete(self,pid): return self._flag(pid,1)
    def recover(self,pid): return self._flag(pid,0)
    def _flag(self,pid,v):
        c=Database.get_conn(self.db_name); cur=c.execute('UPDATE domain_projects SET deleted=? WHERE id=?',(v,pid)); c.commit(); return cur.rowcount>0
    def list_members(self,pid,keyword=''):
        q='SELECT * FROM domain_project_members WHERE project_id=?'; p=[pid]
        if keyword:q+=' AND (name LIKE ? OR username LIKE ?)';p += [f'%{keyword}%',f'%{keyword}%']
        return [dict(x) for x in Database.get_conn(self.db_name).execute(q,p).fetchall()]
    def add_member(self,**d):
        mid=d.get('id') or uuid.uuid4().hex[:12]; c=Database.get_conn(self.db_name); c.execute('INSERT OR REPLACE INTO domain_project_members VALUES(?,?,?,?,?,?,?,?)',(mid,d.get('project_id',''),d.get('user_id',''),d.get('username',''),d.get('name',''),d.get('email',''),d.get('role','member'),d.get('user_group','')));c.commit();return self.get_member(mid)
    def get_member(self,mid):
        r=Database.get_conn(self.db_name).execute('SELECT * FROM domain_project_members WHERE id=?',(mid,)).fetchone();return dict(r) if r else None
    def update_member(self,mid,d):
        old=self.get_member(mid)
        if not old:return None
        return self.add_member(**{**old,**d})
    def remove_member(self,pid,uid):
        c=Database.get_conn(self.db_name);cur=c.execute('DELETE FROM domain_project_members WHERE project_id=? AND user_id=?',(pid,uid));c.commit();return cur.rowcount>0
    def batch_remove_members(self,pid,uids): return sum(self.remove_member(pid,u) for u in uids)
    def _record(self,kind,pid='',rid='',data=None):
        c=Database.get_conn(self.db_name); rid=rid or uuid.uuid4().hex[:12];c.execute('INSERT OR REPLACE INTO domain_project_records VALUES(?,?,?,?)',(rid,pid,kind,json.dumps({**(data or {}),'id':rid})));c.commit();return self.get_custom_func_row(rid)
    def list_custom_funcs(self,project_id='',keyword=''): return self._list_records('custom_func',project_id,keyword)
    def get_custom_func_row(self,i): return self._get_record(i,'custom_func')
    def create_custom_func(self,func_id,project_id='',**d): return bool(self._record('custom_func',project_id,func_id,{**d,'project_id':project_id}))
    def update_custom_func(self,i,d,**kw): return bool(self._record('custom_func',d.get('project_id',''),i,d))
    def update_custom_func_status(self,i,status): return bool(self._record('custom_func','',i,{'status':status}))
    def delete_custom_func(self,i): return self._delete_record(i,'custom_func')
    def list_custom_func_status(self,project_id=''): return self._list_records('custom_func',project_id)
    def list_custom_fields(self,scope_id,scene=''): return self._list_records('custom_field',scope_id,scene)
    def get_custom_field(self,i): return self._get_record(i,'custom_field')
    def upsert_custom_field(self,i,body): return self._record('custom_field',body.get('scope_id',''),i,body)
    def delete_custom_field(self,i): return self._delete_record(i,'custom_field')
    def _get_record(self,i,k):
        r=Database.get_conn(self.db_name).execute('SELECT data FROM domain_project_records WHERE id=? AND kind=?',(i,k)).fetchone();return json.loads(r['data']) if r else None
    def _list_records(self,k,pid='',keyword=''):
        rows=Database.get_conn(self.db_name).execute('SELECT data FROM domain_project_records WHERE kind=?',(k,)).fetchall();return [json.loads(r['data']) for r in rows if (not pid or json.loads(r['data']).get('project_id',json.loads(r['data']).get('scope_id',''))==pid) and (not keyword or keyword.lower() in json.loads(r['data']).get('name','').lower())]
    def _delete_record(self,i,k):
        c=Database.get_conn(self.db_name);cur=c.execute('DELETE FROM domain_project_records WHERE id=? AND kind=?',(i,k));c.commit();return cur.rowcount>0
project_store=ProjectStore()
ProjectRepo=project_store
