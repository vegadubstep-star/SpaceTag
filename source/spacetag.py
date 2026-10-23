"""Space Tag - Orbital Trance Records beta. Edit tags, not filenames."""
import os,re,shutil,struct,tempfile,tkinter as tk
from pathlib import Path
from tkinter import ttk,filedialog,messagebox
from mutagen.id3 import ID3, ID3NoHeaderError,TIT2,TPE1,TALB,TCON,TDRC,TXXX,COMM,APIC
from mutagen.aiff import AIFF
from PIL import Image,ImageTk

FIELDS=("Title","Artist","Album","Genre","Year","Catalogue","Comments")
MAPPING={"Title":b"INAM","Artist":b"IART","Album":b"IPRD","Genre":b"IGNR","Year":b"ICRD","Catalogue":b"ICAT","Comments":b"ICMT"}
FORMATS={".mp3",".wav",".aiff",".aif"}
BG="#071824"; PANEL="#112a38"; FG="#e5f8f8"; ACC="#32e8cc"

def parse_filename(filename):
    name=Path(filename).stem.strip(); catalogue=""
    m=re.match(r"^([a-zA-Z]{2,12}[ _-]?\d{2,7})\s+(.+)$",name)
    if m: catalogue=re.sub(r"[ _-]","",m[1]).upper();name=m[2].strip()
    parts=re.split(r"\s+[-–—]\s+",name,maxsplit=1)
    return {"Catalogue":catalogue,"Artist":parts[0].strip() if len(parts)==2 else "","Title":parts[-1].strip()}

def chunk(name,data):
    return name+struct.pack("<I",len(data))+data+(b"\0" if len(data)%2 else b"")

def riff_blocks(data):
    if len(data)<12 or data[:4]!=b"RIFF" or data[8:12]!=b"WAVE":
        raise ValueError("Not a valid RIFF WAV")
    pos=12
    while pos+8<=len(data):
        size=struct.unpack_from("<I",data,pos+4)[0];end=pos+8+size+(size&1)
        if end>len(data):raise ValueError("Corrupt WAV chunk")
        yield data[pos:pos+4],data[pos+8:pos+8+size],data[pos:end]
        pos=end
    if pos!=len(data):raise ValueError("Malformed WAV")

def wav_read(path):
    data=Path(path).read_bytes();out={}
    for name,body,_ in riff_blocks(data):
        if name!=b"LIST" or not body.startswith(b"INFO"):continue
        off=4
        while off+8<=len(body):
            ident=body[off:off+4];n=struct.unpack_from("<I",body,off+4)[0]
            if off+8+n>len(body):break
            key=next((k for k,v in MAPPING.items() if v==ident),None)
            if key:out[key]=body[off+8:off+8+n].rstrip(b"\0").decode("utf-8","replace")
            off+=8+n+(n&1)
    return out

def wav_write(source,destination,fields):
    data=Path(source).read_bytes();original=[];had=False
    items=b"".join(chunk(v,(fields[k]+"\0").encode("utf-8")) for k,v in MAPPING.items() if fields.get(k))
    new=chunk(b"LIST",b"INFO"+items) if items else b""
    for name,body,raw in riff_blocks(data):
        if name==b"LIST" and body.startswith(b"INFO"):
            if not had and new:original.append(new)
            had=True
        else:original.append(raw)
    if not had and new:original.append(new)
    size=4+sum(len(x) for x in original)
    if size>0xffffffff:raise ValueError("WAV too large for standard RIFF")
    with open(destination,"wb") as f:
        f.write(b"RIFF"+struct.pack("<I",size)+b"WAVE")
        for part in original:f.write(part)

def get_id3(path):
    if Path(path).suffix.lower() in (".aif",".aiff"):
        obj=AIFF(path)
        return obj,obj.tags
    try:return None,ID3(path)
    except ID3NoHeaderError:return None,None

def read_tags(path):
    result={k:"" for k in FIELDS}
    if Path(path).suffix.lower()==".wav":
        result.update(wav_read(path));return result
    _,tags=get_id3(path)
    if tags is None:return result
    for key,frame in (("Title","TIT2"),("Artist","TPE1"),("Album","TALB"),("Genre","TCON"),("Year","TDRC")):
        found=tags.getall(frame)
        if found and found[0].text:result[key]=str(found[0].text[0])
    for f in tags.getall("TXXX"):
        if f.desc.lower() in ("catalognumber","catalogue","catalog number"):result["Catalogue"]=str(f.text[0]) if f.text else ""
    comments=tags.getall("COMM")
    if comments and comments[0].text:result["Comments"]=str(comments[0].text[0])
    return result

def save_id3(path,fields,artwork):
    obj,tags=get_id3(path)
    if tags is None:
        if obj:obj.add_tags();tags=obj.tags
        else:tags=ID3()
    for name,klass in (("Title",TIT2),("Artist",TPE1),("Album",TALB),("Genre",TCON),("Year",TDRC")):
        tags.delall(klass.__name__)
        if fields.get(name):tags.add(klass(encoding=3,text=[fields[name]]))
    tags.delall("TXXX:CATALOGNUMBER")
    if fields.get("Catalogue"):tags.add(TXXX(encoding=3,desc="CATALOGNUMBER",text=[fields["Catalogue"]]))
    tags.delall("COMM")
    if fields.get("Comments"):tags.add(COMM(encoding=3,lang="eng",desc="",text=[fields["Comments"]]))
    if artwork:
        image=Path(artwork).read_bytes();kind="image/png" if Path(artwork).suffix.lower()==".png" else "image/jpeg"
        tags.delall("APIC");tags.add(APIC(encoding=3,mime=kind,type=3,desc="Cover",data=image))
    if obj:obj.save()
    else:tags.save(path,v2_version=3)

def write_tags(path,fields,artwork=None):
    p=Path(path)
    if p.suffix.lower() not in FORMATS:raise ValueError("Unsupported format")
    backup=p.with_name(p.name+".spacetag.bak")
    if not backup.exists():shutil.copy2(p,backup)
    fd,tmp=tempfile.mkstemp(suffix=p.suffix,dir=p.parent);os.close(fd)
    try:
        if p.suffix.lower()==".wav":
            if artwork:raise ValueError("WAV artwork disabled for Pioneer compatibility: use AIFF or MP3")
            wav_write(p,tmp,fields)
        else:
            shutil.copy2(p,tmp);save_id3(tmp,fields,artwork)
        os.replace(tmp,p)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)

class SpaceTag(tk.Tk):
    def __init__(self):
        super().__init__();self.title("SPACE TAG  |  Orbital Trance Records");self.geometry("1150x740");self.configure(bg=BG)
        self.files=[];self.current=None;self.artwork=None;self.vars={k:tk.StringVar() for k in FIELDS}
        sty=ttk.Style();sty.theme_use("clam")
        sty.configure("Treeview",background=PANEL,foreground=FG,fieldbackground=PANEL,rowheight=28)
        sty.configure("Treeview.Heading",background="#193647",foreground=FG)
        self.build()
    def build(self):
        head=tk.Frame(self,bg=BG);head.pack(fill="x",padx=18,pady=15)
        tk.Label(head,text="◉  S P A C E   T A G",font=("Segoe UI",22,"bold"),bg=BG,fg=ACC).pack(side="left")
        tk.Label(head,text="ORBITAL TRANCE RECORDS  /  METADATA EDITOR",bg=BG,fg=FG).pack(side="right")
        bar=tk.Frame(self,bg=BG);bar.pack(fill="x",padx=18)
        for caption,fn in (("Add files",self.add_files),("Add folder",self.add_folder),("Auto parse",self.auto_parse),("Embed artwork",self.pick_art),("Save selected tags",self.save_selected)):
            tk.Button(bar,text=caption,command=fn,bg="#146c69",fg="white",padx=12,pady=7).pack(side="left",padx=4)
        self.keep=tk.BooleanVar(value=True)
        tk.Checkbutton(bar,text="Keep filenames unchanged (always enforced)",variable=self.keep,state="disabled",bg=BG,fg=FG,selectcolor=BG).pack(side="right")
        body=tk.Frame(self,bg=BG);body.pack(fill="both",expand=True,padx=18,pady=12)
        left=tk.Frame(body,bg=PANEL);left.pack(side="left",fill="both",expand=True,padx=(0,10))
        self.tree=ttk.Treeview(left,columns=("file","format"),show="headings",selectmode="extended")
        self.tree.heading("file",text="Original filename");self.tree.heading("format",text="Format")
        self.tree.column("file",width=390);self.tree.column("format",width=75,stretch=False)
        self.tree.pack(fill="both",expand=True,padx=10,pady=10)
        self.tree.bind("<<TreeviewSelect>>",self.select)
        right=tk.Frame(body,bg=PANEL,width=480);right.pack(side="right",fill="y")
        right.pack_propagate(False)
        tk.Label(right,text="TRACK METADATA",bg=PANEL,fg=ACC,font=("Segoe UI",15,"bold")).pack(anchor="w",padx=20,pady=14)
        for field in FIELDS:
            row=tk.Frame(right,bg=PANEL);row.pack(fill="x",padx=20,pady=5)
            tk.Label(row,text=field,width=11,anchor="w",bg=PANEL,fg=FG).pack(side="left")
            tk.Entry(row,textvariable=self.vars[field],bg="#081c2a",fg="white",insertbackground="white",relief="flat",font=("Segoe UI",11)).pack(side="left",fill="x",expand=True,ipady=6)
        self.artlabel=tk.Label(right,text="No artwork selected",bg=PANEL,fg=FG);self.artlabel.pack(pady=15)
        tk.Label(right,text="WAV artwork is intentionally disabled for Pioneer-friendly output.\nMP3 & AIFF artwork supported. Backups use .spacetag.bak.",bg=PANEL,fg="#8dafbb",justify="left",wraplength=400).pack(anchor="w",padx=20)
        self.status=tk.Label(self,text="Ready. Import files or a folder to begin.",bg=BG,fg=ACC,anchor="w")
        self.status.pack(fill="x",padx=18,pady=5)
    def add_files(self):
        names=filedialog.askopenfilenames(filetypes=[("Audio files","*.wav *.mp3 *.aiff *.aif")])
        self.add(names)
    def add_folder(self):
        folder=filedialog.askdirectory()
        if folder:self.add(str(p) for p in Path(folder).rglob("*") if p.suffix.lower() in FORMATS)
    def add(self,names):
        for path in names:
            if path not in self.files and Path(path).suffix.lower() in FORMATS:
                self.files.append(path);self.tree.insert("","end",iid=str(len(self.files)-1),values=(Path(path).name,Path(path).suffix.upper()))
        self.status.config(text=f"{len(self.files)} files loaded")
    def select(self,event=None):
        items=self.tree.selection()
        if not items:return
        self.current=self.files[int(items[0])]
        try:data=read_tags(self.current)
        except Exception as e:messagebox.showerror("Read error",str(e));return
        for k in FIELDS:self.vars[k].set(data.get(k,""))
        self.artwork=None;self.artlabel.config(text="No new artwork selected")
    def auto_parse(self):
        items=self.tree.selection()
        if not items:messagebox.showinfo("Select tracks","Select a track first");return
        found=parse_filename(self.files[int(items[0])])
        for key,value in found.items():
            if value:self.vars[key].set(value)
        self.status.config(text="Detected metadata applied to editor. Check before saving.")
    def pick_art(self):
        name=filedialog.askopenfilename(filetypes=[("Images","*.jpg *.jpeg *.png")])
        if name:self.artwork=name;self.artlabel.config(text="Artwork: "+Path(name).name)
    def save_selected(self):
        items=self.tree.selection()
        if not items:messagebox.showinfo("Select tracks","Select at least one track");return
        if len(items)>1 and not messagebox.askyesno("Batch save","Apply the same editor fields to all selected files?"):return
        fields={k:v.get().strip() for k,v in self.vars.items()};ok=0;errors=[]
        for item in items:
            name=self.files[int(item)]
            try:write_tags(name,fields,self.artwork);ok+=1
            except Exception as e:errors.append(f"{Path(name).name}: {e}")
        self.status.config(text=f"Saved {ok} file(s), {len(errors)} error(s); filenames unchanged")
        if errors:messagebox.showwarning("Some tracks were skipped","\n".join(errors[:10]))
        elif ok:messagebox.showinfo("Space Tag",f"Saved {ok} file(s). Backup(s) created.")

if __name__=="__main__":SpaceTag().mainloop()
