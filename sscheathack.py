import os, sys, re, json, time, zipfile, threading, queue, hashlib, subprocess
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

APP = 'sscheathack.exe'
TEXT = {
 'en': {'title':'SS Cheat Hack Scanner','scan':'Full Scan','monitor':'Start Live Monitor','stop':'Stop Monitor','choose':'Choose folder','lang':'Language','status':'Ready','results':'Findings','log':'Live activity','export':'Export report','clear':'Clear','scope':'Scan scope','all':'All accessible drives + user folders','minecraft':'Minecraft folders only','running':'Monitor running','stopped':'Monitor stopped','scanstart':'Scan started…','done':'Scan complete','warn':'Potential indicator','info':'Informational','error':'Could not read','none':'No indicators found in scanned locations. This is not proof that a system is clean.','consent':'Only scan a computer with its owner’s permission. The scan stays local; no files are uploaded or changed.','select':'Select folder to scan','monitorhint':'Monitors Minecraft logs and new/changed relevant files.','nojava':'Minecraft process not detected; log monitoring is still active.','report':'Report saved'},
 'vi': {'title':'SS Cheat Hack Scanner','scan':'Quét toàn máy','monitor':'Bật theo dõi trực tiếp','stop':'Dừng theo dõi','choose':'Chọn thư mục','lang':'Ngôn ngữ','status':'Sẵn sàng','results':'Kết quả phát hiện','log':'Hoạt động trực tiếp','export':'Xuất báo cáo','clear':'Xóa','scope':'Phạm vi quét','all':'Tất cả ổ đĩa truy cập được + thư mục người dùng','minecraft':'Chỉ thư mục Minecraft','running':'Đang theo dõi','stopped':'Đã dừng theo dõi','scanstart':'Đang quét…','done':'Quét hoàn tất','warn':'Dấu hiệu đáng nghi','info':'Thông tin','error':'Không đọc được','none':'Không tìm thấy dấu hiệu trong phạm vi đã quét. Điều này không chứng minh máy hoàn toàn sạch.','consent':'Chỉ quét máy khi chủ máy đồng ý. Dữ liệu ở lại máy, không tải lên và không sửa/xóa file.','select':'Chọn thư mục cần quét','monitorhint':'Theo dõi log Minecraft và file liên quan mới/thay đổi.','nojava':'Chưa phát hiện tiến trình Minecraft; vẫn đang theo dõi log.','report':'Đã lưu báo cáo'}
}
CLIENTS = ['meteor client','meteor+ client','vape client','novoware client','boze client','liquidbounce client','liquidbounce+ reborn','wurst client','wurst+1 client','wurst+2 client','wurst+3 client','forgehax client','fabrichax client','pika client','badlion client','lunar client','feather client','impact client','aristois','inertia client','bleachhack','salhack','kami blue','future client','rusherhack','konas client','ares client','sigma client']
MODULES = {
 'AutoTotem': [r'autototem',r'auto[_ -]?totem',r'module.{0,20}totem'],
 'AutoCart': [r'autocart',r'auto[_ -]?cart',r'minecart.{0,30}(auto|macro)',r'(auto|macro).{0,30}minecart'],
 'AutoClicker': [r'autoclicker',r'auto[_ -]?click'], 'KillAura': [r'killaura',r'kill[_ -]?aura'],
 'AutoCrystal': [r'autocrystal',r'auto[_ -]?crystal'], 'Scaffold': [r'\bscaffold\b'],
 'Reach': [r'\breach\b'], 'Velocity': [r'\bvelocity\b'], 'TriggerBot': [r'triggerbot']}
CLIENT_PATTERNS = [re.compile(re.escape(x), re.I) for x in CLIENTS]
MODULE_PATTERNS = {k:[re.compile(p,re.I) for p in v] for k,v in MODULES.items()}
LOG_PATTERNS = [(re.compile(p,re.I),name) for name, pats in MODULES.items() for p in pats]
MAX_ARCHIVE=30*1024*1024

class Scanner:
 def __init__(self, emit): self.emit=emit; self.findings=[]; self.stop_event=threading.Event(); self.monitor_thread=None; self.log_offsets={}; self.file_snapshot={}
 def add(self, level, category, path, detail):
  item={'time':datetime.now().isoformat(timespec='seconds'),'level':level,'category':category,'path':str(path),'detail':detail}
  self.findings.append(item); self.emit(('finding',item))
 def roots(self, mode, custom=None):
  if custom: return [Path(custom)]
  if mode=='minecraft': return self.minecraft_roots()
  roots=[]
  if os.name=='nt':
   for c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
    p=Path(c+':\\')
    if p.exists(): roots.append(p)
  else: roots=[Path.home(),Path('/tmp')]
  for p in [Path.home(),Path(os.environ.get('APPDATA','~')).expanduser(),Path(os.environ.get('LOCALAPPDATA','~')).expanduser()]:
   if p.exists() and p not in roots: roots.append(p)
  return roots
 def minecraft_roots(self):
  h=Path.home(); candidates=[h/'.minecraft',h/'AppData/Roaming/.minecraft',h/'.lunarclient',h/'AppData/Roaming/.lunarclient',h/'AppData/Roaming/PrismLauncher',h/'AppData/Roaming/ModrinthApp',h/'AppData/Roaming/CurseForge']
  for base in [h/'AppData/Roaming',h/'AppData/Local',h/'.local/share']:
   if base.exists():
    try:
     candidates += [p for p in base.iterdir() if any(x in p.name.lower() for x in ('minecraft','prism','lunar','modrinth','curseforge'))]
    except OSError: pass
  out=[]
  for p in candidates:
   if p.exists() and p not in out: out.append(p)
  return out
 def inspect_text(self, text, path, source='file'):
  low=text.lower()
  for pat in CLIENT_PATTERNS:
   if pat.search(text): self.add('warning','Client signature',path,f'Found text signature: {pat.pattern} ({source}); verify manually.')
  for name,pats in MODULE_PATTERNS.items():
   if any(p.search(text) for p in pats): self.add('warning',name,path,f'Possible {name} reference in {source}; a name/string alone does not prove use.')
 def inspect_jar(self,p):
  try:
   with zipfile.ZipFile(p) as z:
    names='\n'.join(z.namelist())
    self.inspect_text(names,p,'JAR entry names')
    for n in z.namelist():
     if n.endswith(('.class','.json','.toml','.properties','.cfg')):
      try:
       info=z.getinfo(n)
       if info.file_size>MAX_ARCHIVE: continue
       data=z.read(n)
       txt=data.decode('utf-8','ignore')
       self.inspect_text(txt,p,f'JAR:{n}')
      except Exception: pass
  except Exception as e: self.add('info','Unreadable archive',p,str(e))
 def scan(self, mode, custom=None):
  self.findings=[]; roots=self.roots(mode,custom); seen=set(); count=0
  for root in roots:
   self.emit(('status',f'Scanning {root}'))
   for base,dirs,files in os.walk(root,topdown=True):
    dirs[:]=[d for d in dirs if d.lower() not in {'windows','program files','program files (x86)','$recycle.bin','system volume information','node_modules','.git','cache','caches'}]
    for fn in files:
     if self.stop_event.is_set(): return
     p=Path(base)/fn
     try:
      st=p.stat(); key=(str(p).lower(),st.st_size,st.st_mtime_ns)
      if key in seen: continue
      seen.add(key); count+=1
      low=str(p).lower()
      if p.suffix.lower()=='.jar': self.inspect_jar(p)
      elif p.suffix.lower() in ('.log','.txt','.json','.toml','.cfg','.properties') and st.st_size<=8*1024*1024:
       try: self.inspect_text(p.read_text(errors='ignore'),p)
       except Exception: pass
      # Hidden/system/oddly named files are recorded as context, never treated as cheats by themselves.
      if os.name=='nt':
       try:
        import ctypes
        attrs=ctypes.windll.kernel32.GetFileAttributesW(str(p))
        if attrs!=-1 and attrs & 2 and (p.suffix.lower() in ('.jar','.dll','.exe','.log')):
         self.add('info','Hidden relevant file',p,'Hidden attribute set; not proof of cheating.')
       except Exception: pass
      if p.suffix.lower() in ('.jar','.dll','.exe') and any(x in low for x in ('meteor','vape','cheat','hack','client','inject','clicker','totem','cart')):
       self.add('warning','Suspicious filename',p,'Filename matches a review keyword; names can be harmless or deliberately changed.')
     except (PermissionError,FileNotFoundError,OSError): continue
  self.emit(('status',f'Finished: {count} files checked'))
  if not self.findings: self.emit(('empty',None))
  return count
 def log_files(self):
  out=[]
  for r in self.minecraft_roots():
   if r.is_file() and r.name.lower().endswith('.log'): out.append(r)
   elif r.exists():
    for sub in ('logs','crash-reports'):
     q=r/sub
     if q.exists():
      try: out += [p for p in q.glob('*.log') if p.is_file()]
      except OSError: pass
  return out
 def monitor(self):
  self.stop_event.clear(); self.log_offsets={}
  # Start at each current EOF so Live Monitor reports new activity, not old log history.
  for p in self.log_files():
   try: self.log_offsets[str(p)]=p.stat().st_size
   except OSError: pass
  self.emit(('status',TEXT['en']['running']))
  while not self.stop_event.wait(1.0):
   for p in self.log_files():
    try:
     size=p.stat().st_size; off=self.log_offsets.get(str(p),0)
     if size<off: off=0
     if size>off:
      with p.open('r',errors='ignore') as f: f.seek(off); data=f.read(2*1024*1024); self.log_offsets[str(p)]=f.tell()
      for line in data.splitlines():
       for pat,name in LOG_PATTERNS:
        if pat.search(line): self.add('warning',name,p,'Live log line contains a related keyword; not proof of automated behavior.')
    except (OSError,PermissionError): pass
  self.emit(('status',TEXT['en']['stopped']))
 def start_monitor(self):
  if self.monitor_thread and self.monitor_thread.is_alive(): return
  self.monitor_thread=threading.Thread(target=self.monitor,daemon=True); self.monitor_thread.start()
 def stop_monitor(self): self.stop_event.set()

class App:
 def __init__(self,root):
  self.root=root; self.lang='en'; self.q=queue.Queue(); self.scanner=Scanner(self.q.put); self.custom=None
  root.geometry('1000x700'); root.minsize(800,560); root.configure(bg='#0b1020')
  self.style=ttk.Style(); self.style.theme_use('clam'); self.style.configure('TFrame',background='#0b1020'); self.style.configure('TLabel',background='#0b1020',foreground='#e7edf7'); self.style.configure('TButton',padding=8); self.style.configure('TCombobox',fieldbackground='#182238',background='#182238',foreground='#e7edf7')
  self.build(); self.update_text(); root.after(150,self.poll)
 def build(self):
  top=ttk.Frame(self.root,padding=16); top.pack(fill='x')
  self.title=ttk.Label(top,text='SS Cheat Hack Scanner',font=('Segoe UI',20,'bold')); self.title.pack(side='left')
  self.langbox=ttk.Combobox(top,values=['English','Tiếng Việt'],state='readonly',width=13); self.langbox.current(0); self.langbox.pack(side='right'); self.langbox.bind('<<ComboboxSelected>>',self.change_lang)
  self.notice=ttk.Label(self.root,text='',wraplength=940); self.notice.pack(fill='x',padx=18,pady=(0,10))
  bar=ttk.Frame(self.root,padding=12); bar.pack(fill='x',padx=12)
  self.scope=ttk.Combobox(bar,values=[],state='readonly',width=40); self.scope.pack(side='left'); self.scope.current(0)
  self.scanbtn=ttk.Button(bar,text='',command=self.start_scan); self.scanbtn.pack(side='left',padx=8)
  self.pickbtn=ttk.Button(bar,text='',command=self.pick); self.pickbtn.pack(side='left')
  self.monbtn=ttk.Button(bar,text='',command=self.toggle_monitor); self.monbtn.pack(side='right')
  self.status=ttk.Label(self.root,text='',padding=12); self.status.pack(fill='x')
  panes=ttk.Panedwindow(self.root,orient='vertical'); panes.pack(fill='both',expand=True,padx=12,pady=8)
  a=ttk.Frame(panes); b=ttk.Frame(panes); panes.add(a,weight=3); panes.add(b,weight=2)
  self.resultlabel=ttk.Label(a,text='',font=('Segoe UI',11,'bold')); self.resultlabel.pack(anchor='w')
  self.results=tk.Text(a,bg='#101a2d',fg='#e7edf7',insertbackground='white',relief='flat',wrap='word'); self.results.pack(fill='both',expand=True,pady=6)
  self.loglabel=ttk.Label(b,text='',font=('Segoe UI',11,'bold')); self.loglabel.pack(anchor='w')
  self.live=tk.Text(b,height=8,bg='#101a2d',fg='#b7c6dd',insertbackground='white',relief='flat',wrap='word'); self.live.pack(fill='both',expand=True,pady=6)
  foot=ttk.Frame(self.root,padding=12); foot.pack(fill='x')
  self.exportbtn=ttk.Button(foot,text='',command=self.export); self.exportbtn.pack(side='left')
  self.clearbtn=ttk.Button(foot,text='',command=self.clear); self.clearbtn.pack(side='left',padx=8)
 def update_text(self):
  t=TEXT[self.lang]; self.root.title(t['title']); self.notice.config(text=t['consent']); self.scope['values']=[t['all'],t['minecraft']]
  self.scanbtn.config(text=t['scan']); self.pickbtn.config(text=t['choose']); self.monbtn.config(text=t['monitor'] if not (self.scanner.monitor_thread and self.scanner.monitor_thread.is_alive()) else t['stop'])
  self.status.config(text=t['status']); self.resultlabel.config(text=t['results']); self.loglabel.config(text=t['log']); self.exportbtn.config(text=t['export']); self.clearbtn.config(text=t['clear'])
 def change_lang(self,_=None): self.lang='vi' if self.langbox.current()==1 else 'en'; self.update_text()
 def start_scan(self):
  if not messagebox.askyesno('SS Scanner',TEXT[self.lang]['consent']): return
  mode='minecraft' if self.scope.current()==1 else 'all'; self.status.config(text=TEXT[self.lang]['scanstart'])
  threading.Thread(target=self.scanner.scan,args=(mode,self.custom),daemon=True).start()
 def pick(self):
  p=filedialog.askdirectory(title=TEXT[self.lang]['select'])
  if p: self.custom=p; self.status.config(text=p)
 def toggle_monitor(self):
  if self.scanner.monitor_thread and self.scanner.monitor_thread.is_alive(): self.scanner.stop_monitor()
  else:
   if not messagebox.askyesno('SS Scanner',TEXT[self.lang]['consent']): return
   self.scanner.start_monitor()
  self.update_text()
 def poll(self):
  try:
   while True:
    typ,data=self.q.get_nowait()
    if typ=='finding':
     level=data['level'].upper(); line=f"[{level}] {data['category']} | {data['path']}\n  {data['detail']}\n\n"
     self.results.insert('end',line); self.results.see('end')
     self.live.insert('end',line); self.live.see('end')
    elif typ=='status': self.status.config(text=data); self.update_text()
    elif typ=='empty': self.results.insert('end',TEXT[self.lang]['none']+'\n')
  except queue.Empty: pass
  self.root.after(150,self.poll)
 def clear(self): self.results.delete('1.0','end'); self.live.delete('1.0','end'); self.scanner.findings=[]
 def export(self):
  p=filedialog.asksaveasfilename(defaultextension='.json',filetypes=[('JSON report','*.json'),('Text report','*.txt')],initialfile='sscheathack-report.json')
  if not p:return
  data={'application':APP,'generated':datetime.now().isoformat(),'findings':self.scanner.findings,'limitations':'Indicators are not proof. Logs may omit client-side actions. Access-denied files are skipped.'}
  try:
   if p.lower().endswith('.txt'):
    with open(p,'w',encoding='utf-8') as f:
     for x in self.scanner.findings:f.write(f"{x['time']} [{x['level']}] {x['category']}\n{x['path']}\n{x['detail']}\n\n")
   else: Path(p).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
   messagebox.showinfo('SS Scanner',TEXT[self.lang]['report']+': '+p)
  except Exception as e: messagebox.showerror('SS Scanner',str(e))

def main():
 root=tk.Tk(); App(root); root.mainloop()
if __name__=='__main__': main()
