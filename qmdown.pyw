#coding=utf-8

from tkinter import *
from tkinter.ttk import *
import requests
from requests.auth import HTTPDigestAuth as Digest
from bs4 import BeautifulSoup
import sqlite3
import io
import os

for d in ['~/desktop','~/桌面']:
    if os.path.isdir(os.path.expanduser(d)):
        homedir=os.path.expanduser(d)
        break
else:
    homedir='.'

tk=Tk()
hostvar=StringVar(value='192.168.1.193:10000')
unvar=StringVar()
pwvar=StringVar()
singersvar=StringVar(value=())
songsvar=StringVar(value=())
msg=StringVar(value='点击连接按钮')

def connect(*_):
    global base
    global db
    global s
    global singers
    global songs
    s=requests.Session()
    s.auth=Digest(unvar.get(),pwvar.get())
    host=hostvar.get()
    host=host if '://' in host else 'http://'+host

    msg.set('获取 QQ音乐 的位置……')
    tk.update()
    #get user applications
    res=s.get(host+'/var/mobile/Applications',timeout=2)
    if res.status_code==401:
        return msg.set('密码错误')
    elif res.status_code==404:
        return msg.set('找不到用户程序目录')
    elif res.status_code!=200:
        return msg.set('枚举用户程序时出错 %d %s'%(res.status_code,res.reason))

    #find qqmusic
    soup=BeautifulSoup(res.text,'html.parser')
    link=soup.find('a',text=lambda x: 'QQ音乐' in x)
    if not link:
        return msg.set('用户程序中找不到 QQ音乐')

    msg.set('下载音乐数据库……')
    tk.update()
    #get music db
    base=host+link['href']+'/Documents'
    res=s.get(base+'/qqmusic.sqlite')
    if res.status_code==404:
        return msg.set('音乐数据库不存在')
    elif res.status_code!=200:
        return msg.set('获取音乐数据库时出错 %d %s'%(res.status_code,res.reason))

    try:
        with open('qqmusic.sqlite','wb') as f:
            f.write(res.content)
    except Exception as e:
        msg.set('保存音乐数据库失败')
        raise

    msg.set('查询歌手信息……')
    tk.update()
    #get singers
    try:
        db=sqlite3.connect('qqmusic.sqlite')
    except Exception as e:
        msg.set('打开音乐数据库失败')
        raise

    def prettify(singers):
        def _real():
            current=None
            for name,py in singers:
                if current!=py:
                    current=py
                    yield '[%s] %s'%(py,name)
                else:
                    yield '    %s'%name
        return tuple(_real())
    
    cur=db.cursor()
    cur.execute(
        'select singer,singerindex from SONGS where file!=""'
        'group by singer order by singerindex asc'
    )
    singers=cur.fetchall()
    singersvar.set(prettify(singers))
    songs=[]

    msg.set('双击歌曲名称下载')

def getsongs(*_):
    def prettify(songs):
        def _real():
            for name,file in songs:
                yield '%s (%s)'%(name,file)
        return tuple(_real())
    
    global songs
    if not l1.curselection():
        return
    singer=singers[l1.curselection()[0]][0]
    cur=db.cursor()
    cur.execute(
        'select name,file from SONGS where singer=? and file!="" '
        'order by nameindex asc',
        [singer]
    )
    songs=cur.fetchall()
    songsvar.set(prettify(songs))

def download(*_):
    def normalize(path):
        for ch in ['\\','/',':','?','"','<','>','|']:
            path=path.replace(ch,'-')
        if path.endswith('.tm3') or path.endswith('.tm0'):
            path=path[:-4]+'.mp3'
        return path
    
    if not l2.curselection():
        return
    name,uri=songs[l2.curselection()[0]]
    msg.set('正在下载……')
    tk.update()
    res=s.get(base+uri)
    with open(os.path.join(homedir,normalize(name+os.path.splitext(uri)[1])),'wb') as f:
        f.write(res.content)
    os.startfile(homedir)
    msg.set('下载完成')
    

tk.title('QM Download Tool')
tk.rowconfigure(1,weight=1)
tk.columnconfigure(0,weight=1)
tk.columnconfigure(1,weight=2)

upper=Frame(tk)
upper.grid(row=0,column=0,columnspan=2,pady=3,padx=3,sticky='we')
upper.columnconfigure(3,weight=1)

Entry(upper,textvariable=hostvar,width=35).grid(row=0,column=0,)
Entry(upper,textvariable=unvar,width=15).grid(row=0,column=1,padx=10)
Entry(upper,textvariable=pwvar,show='*',width=15).grid(row=0,column=2)
Label(upper,width=0).grid(row=0,column=3,padx=25)
Button(upper,text='连接',command=connect).grid(row=0,column=4)

l1=Listbox(tk,listvariable=singersvar,height=20,font='Consolas -13')
l1.grid(row=1,column=0,sticky='nswe')
l2=Listbox(tk,listvariable=songsvar,font='Consolas -13')
l2.grid(row=1,column=1,sticky='nswe')

Label(tk,textvariable=msg).grid(row=2,column=0,columnspan=2,sticky='we')

l1.bind('<<ListboxSelect>>',getsongs)
l2.bind('<Double-Button-1>',download)
mainloop()
