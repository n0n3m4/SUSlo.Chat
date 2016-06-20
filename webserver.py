# -*- coding: utf-8 -*-

from flask import Flask
from flask import render_template
from flask_bootstrap import Bootstrap
from flask import request
from flask import session
from flask import redirect,url_for
import os
import time
import mainmodule as mm
import SocketServer
import json

SocketServer.TCPServer.allow_reuse_address = True

app = Flask(__name__)

app.secret_key = 'sjopadqweosdpajepoqjwepouasdopuqwoepquwoepupouopqwuepqwe'
Bootstrap(app)

LOAD_AT_ONCE = 60

@app.route("/index")
@app.route("/")
def index():
	if mm.getuid(session) is not None:
		return redirect(url_for('main'))
	else:
		return redirect(url_for('login'))
		
@app.route("/login")
def login():
	return render_template("login.html")
	
@app.route("/main")
def main():
	return render_template("main.html",chats=mm.getchats(mm.getuid(session)))
	
@app.route("/chat")
def chat():
	mm.updtime(int(request.args['id']),session)
	return render_template("chat.html",chatid=int(request.args['id']),loadatonce=LOAD_AT_ONCE)
	
@app.route("/loadchat")
def loadchat():
	chatdata = mm.loadchat(mm.getuid(session),int(request.args['id']),int(request.args['loaded']),LOAD_AT_ONCE,mm.gethisttime(int(request.args['id']),session))
	return json.dumps([{'name':x[0],'msg':x[1],'date':x[2].strftime("%H:%M:%S %d-%m-%Y")} for x in chatdata])
	
@app.route("/longpoll")
def longpoll():
	tmp = mm.longpoll(mm.getuid(session),int(request.args['id']),mm.getpolltime(int(request.args['id']),session))
	if len(tmp)>0:
		mm.setpolltime(int(request.args['id']),session,tmp[-1][2])
	return json.dumps([{'name':x[0],'msg':x[1],'date':x[2].strftime("%H:%M:%S %d-%m-%Y")} for x in tmp])
	
@app.route("/createchat",methods=['POST'])
def createchat():	
	return mm.createchat(mm.getuid(session),request.form['chatname'])

@app.route("/postchat",methods=['POST'])
def postchat():
	mm.postchat(mm.getuid(session),int(request.form['id']),request.form['message'])
	return ''
	
@app.route("/invite",methods=['POST'])
def invite():
	uid = mm.getuidbyname(request.form['username'])
	cid = int(request.form['id'])
	key = request.form['key']
	mm.invite(mm.getuid(session),uid,cid,key)
	return ''
	
@app.route("/dologin",methods=['POST'])
def dologin():
	session['uid']=mm.auth(request.form['username'],request.form['password'])
	return redirect(url_for('index'))
	
@app.route("/doregister",methods=['POST'])
def doregister():
	res=mm.register(request.form['username'],request.form['password'],request.form['pubkey'],request.form['nickname'])
	if 'audiokey' in request.files and res is None:
		tmp=request.files['audiokey']
		audio=tmp.read()
		mm.saveaudio(request.form['username'],audio)
	if res is not None:
		return res
	else:
		return ''

@app.route("/getpubkey")
def getpubkey():
	return mm.getpubkey(request.args['username'])

@app.route("/savechatkey",methods=['POST'])
def savechatkey():
	return mm.savechatkey(mm.getuid(session),int(request.form['id']),request.form['key'])

@app.route("/loadchatkey")
def loadchatkey():
	return mm.loadchatkey(mm.getuid(session),int(request.args['id']))

@app.route("/loadinvitekey")
def loadinvitekey():
	return mm.loadchatkeyRSA(mm.getuid(session),int(request.args['id']))

@app.route("/loadaudio")
def loadaudio():
	return mm.loadaudio(request.args['username'])

''' pastebin-service '''
@app.route('/paste')
def paste():
	hazpaste=False
	paste=None
	if 'id' in request.args:
		idx=request.args['id']
		hazpaste=True
		paste=mm.pasteget(idx)
	return render_template('paste.html',hazpaste=hazpaste,paste=paste)

@app.route('/pastepost',methods=['POST'])
def pastepost():
	return mm.pastepost(request.form['message'])


@app.after_request
def add_header(response):
    """
    Add headers to both force latest IE rendering engine or Chrome Frame,
    and also to cache the rendered page for 10 minutes.
    """
    response.headers['X-UA-Compatible'] = 'IE=Edge,chrome=1'
    response.headers['Cache-Control'] = 'public, max-age=0'
    return response
	
app.run(debug=True,threaded=True,host='0.0.0.0')
