"""报告上下文文件存储。"""
from __future__ import annotations
import os, json
from app.db import PROJECT_ROOT
class ReportStore:
 def __init__(self):self.root=os.path.join(PROJECT_ROOT,'reports');self.trash=os.path.join(self.root,'.trash');os.makedirs(self.root,exist_ok=True);os.makedirs(self.trash,exist_ok=True)
 def list_case_snapshots(self,limit=50):return []
 def generate_html(self,results,project,title):
  n='report.html';p=os.path.join(self.root,n);open(p,'w').write(f'<h1>{title}</h1>');return p
 def generate_markdown(self,results):p=os.path.join(self.root,'report.md');open(p,'w').write('');return p
 def generate_junit(self,results):p=os.path.join(self.root,'report.xml');open(p,'w').write('<testsuite/>');return p
 def list_reports(self):return [{'name':n,'path':os.path.join(self.root,n)} for n in os.listdir(self.root) if os.path.isfile(os.path.join(self.root,n))]
 def list_trash(self):return [n for n in os.listdir(self.trash) if os.path.isfile(os.path.join(self.trash,n))]
 def download_path(self,n):p=os.path.join(self.root,n);return p if os.path.isfile(p) else None
 def trash_report(self,n):
  p=os.path.join(self.root,n);return os.path.isfile(p) and not bool(os.rename(p,os.path.join(self.trash,n)))
 def restore_report(self,n):p=os.path.join(self.trash,n);return os.path.isfile(p) and not bool(os.rename(p,os.path.join(self.root,n)))
 def purge_report(self,n):p=os.path.join(self.trash,n);os.remove(p) if os.path.isfile(p) else None;return True
ReportRepo=ReportStore()
