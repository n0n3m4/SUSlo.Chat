# -*- coding: utf-8 -*-

'''
	CREATE DATABASE chat DEFAULT CHARACTER SET utf8 DEFAULT COLLATE utf8_general_ci;

	USE chat;

	CREATE TABLE users (uid INT AUTO_INCREMENT,name TEXT,password TEXT,pubkey TEXT,nickname TEXT,PRIMARY KEY (uid));
	
	CREATE TABLE chats (cid INT AUTO_INCREMENT,name TEXT,PRIMARY KEY (cid));

	CREATE TABLE chatusers (id INT AUTO_INCREMENT,uid INT,cid INT,PRIMARY KEY (id),FOREIGN KEY (uid) REFERENCES users(uid),FOREIGN KEY (cid) REFERENCES chats(cid));

	CREATE TABLE invites(id INT AUTO_INCREMENT,uid INT,cid INT,`key` TEXT,PRIMARY KEY (id),FOREIGN KEY (uid) REFERENCES users(uid),FOREIGN KEY (cid) REFERENCES chats(cid));

	CREATE TABLE aeskeys(id INT AUTO_INCREMENT,uid INT,cid INT,`key` TEXT,PRIMARY KEY (id),FOREIGN KEY (uid) REFERENCES users(uid),FOREIGN KEY (cid) REFERENCES chats(cid));

	CREATE TABLE messages (id INT AUTO_INCREMENT,uid INT,cid INT,msg TEXT,time TIMESTAMP,PRIMARY KEY (id),FOREIGN KEY (uid) REFERENCES users(uid),FOREIGN KEY (cid) REFERENCES chats(cid));

	CREATE TABLE paste (id INT AUTO_INCREMENT,message TEXT,PRIMARY KEY(ID));

	CREATE TABLE audiokeys(id INT AUTO_INCREMENT,uid INT,audio LONGBLOB,PRIMARY KEY(ID),FOREIGN KEY (uid) REFERENCES users(uid));

	-- Межгалактический костыль.
	-- Однако, вроде и быстрый должен быть, благо кеширование запросов.
	
        DELIMITER //
        CREATE FUNCTION LONGWAIT(pcid INT,pfrom TIMESTAMP,ptimeout INT) RETURNS INT
        BEGIN
                DECLARE i INT;
                DECLARE t FLOAT;
                DECLARE kostyl INT;
                SELECT COUNT(*) INTO i FROM messages WHERE cid=pcid AND time>pfrom;
                SET t := 0;
                WHILE i = 0 AND t < ptimeout DO
                        SELECT sleep(0.1) INTO kostyl;                        
                        SELECT COUNT(*) INTO i FROM messages WHERE cid=pcid AND time>pfrom;
                        SET t := t + 0.1;
                END WHILE;
                RETURN 0;
        END//
        DELIMITER ;
        

'''

import pymysql

def getsql():
	conn = pymysql.connect(host='localhost', port=3306, user='root', db='chat', charset='utf8')
	cur = conn.cursor()
	return conn,cur

def closql(conn,cur):
	cur.close()
	conn.close()

''' webserver-db time sync '''
def getnow():
	sql,cur=getsql()
	cur.execute("SELECT NOW()")
	res=cur.fetchone()
	closql(sql,cur)
	return res

''' returns saved uid or None '''
''' actually means nothing '''
def getuid(session):
	if not session:
		return None
	if not session['uid']:
		return None
	return int(session['uid'])

def getuidbyname(uname):
	sql,cur=getsql()
	cur.execute("SELECT uid FROM users WHERE name=%s",(uname))
	res=cur.fetchone()
	closql(sql,cur)
	if res is not None:
		return res[0]
	return None

''' save chat load time (to split messages into history and longpolls) '''
def updtime(chatid,session):
	if not session:
		return None
	if not session['uid']:
		return None
	x=getnow()
	session['histtime_'+str(chatid)]=x
	session['polltime_'+str(chatid)]=x

def gethisttime(chatid,session):
	return session['histtime_'+str(chatid)]

def getpolltime(chatid,session):
	return session['polltime_'+str(chatid)]

def setpolltime(chatid,session,x):
	session['polltime_'+str(chatid)]=x
	
''' returns uid or None '''
def auth(uname,pwd):
	sql,cur=getsql()
	cur.execute("SELECT uid FROM users WHERE name=%s AND password=%s",(uname,pwd))
	res=cur.fetchone()
	closql(sql,cur)
	if res is not None:
		return res[0]
	return None

''' returns ??? or None '''
def register(uname,pwd,pubkey,nickname):
	if len(uname)==0 or len(pwd)==0 or len(nickname)==0:
		return 'Too short'
	sql,cur=getsql()
	cur.execute("SELECT uid FROM users WHERE name=%s",(uname))
	res=cur.fetchone()
	if res is not None:
		closql(sql,cur)
		return 'Already exists'
	cur.execute("INSERT INTO users (name,password,pubkey,nickname) VALUES (%s,%s,%s,%s)",(uname,pwd,pubkey,nickname))
	sql.commit()
	closql(sql,cur)
	return None

def saveaudio(uname,audio):
	sql,cur=getsql()
	cur.execute("SELECT uid FROM users WHERE name=%s",(uname))
	uid=cur.fetchone()[0]
	cur.execute("INSERT INTO audiokeys (uid,audio) VALUES (%s,%s)",(uid,audio))
	sql.commit()
	closql(sql,cur)

def loadaudio(uname):
	sql,cur=getsql()
	cur.execute("SELECT audio FROM audiokeys INNER JOIN users ON users.uid = audiokeys.uid WHERE name=%s",(uname))
	aud=cur.fetchall()
	if len(aud)>0:
		aud=aud[0][0]
	else:
		aud=''
	closql(sql,cur)
	return aud

''' returns a tuple of name,msg,time '''
def loadchat(uid,cid,offset,amount,before):
	sql,cur=getsql()
	# Никаких проверок на принадлежность к чату. Наслаждайтесь зашифрованными сообщениями.
	cur.execute("SELECT nickname,msg,time FROM messages INNER JOIN users ON users.uid = messages.uid WHERE cid=%s AND time<=%s ORDER BY id DESC LIMIT %s,%s",(cid,before,offset,amount))
	pairz=cur.fetchall()[::-1]
	closql(sql,cur)
	return pairz

''' blocks until new messages, returns tuple of name,msg,time '''
def longpoll(uid,cid,since):
	sql,cur=getsql()
	# Осторожно, костыль. pymysql немного болеет и не умеет коммитить из разных подключений
	# Давайте поможем ему не страдать от своего недуга
	cur.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
	cur.execute("SELECT LONGWAIT(%s,%s,%s)",(cid,since,25));
	cur.fetchall()
	cur.execute("SELECT nickname,msg,time FROM messages INNER JOIN users ON users.uid = messages.uid WHERE cid=%s AND time>%s ORDER BY id ASC",(cid,since))
	pairz=cur.fetchall()
	closql(sql,cur)
	return pairz
	
''' returns None '''
def postchat(uid,cid,msg):
	sql,cur=getsql()
	cur.execute("SELECT uid FROM chatusers WHERE uid=%s AND cid=%s",(uid,cid))
	if len(cur.fetchall())==0:
		''' Тот неловкий момент когда пользователь постит в группу где сам не состоит '''
		closql(sql,cur)
		return None
	cur.execute("INSERT INTO messages (uid,cid,msg) VALUES (%s,%s,%s)",(uid,cid,msg))
	sql.commit()
	closql(sql,cur)
	return None

''' returns None '''
def joinchat(uid,cid):
	sql,cur=getsql()
	cur.execute("INSERT INTO chatusers (uid,cid) VALUES (%s,%s)",(uid,cid))
	sql.commit()
	closql(sql,cur)
	return None

''' returns cid '''
def createchat(uid,name):
	sql,cur=getsql()
	cur.execute("INSERT INTO chats (name) VALUES (%s)",(name))
	cur.execute("SELECT LAST_INSERT_ID()")	
	cid = cur.fetchone()[0]
	sql.commit()
	closql(sql,cur)
	joinchat(uid,cid)	
	return str(cid)
	
''' returns None '''
def invite(myuid,uid,cid,key):
	sql,cur=getsql()
	cur.execute("SELECT uid FROM chatusers WHERE uid=%s AND cid=%s",(myuid,cid))
	if len(cur.fetchall())==0:
		''' Тот неловкий момент когда пользователь приглашает в группу где сам не состоит '''
		closql(sql,cur)
		return None
	closql(sql,cur)
	if len(key)==0:
		''' По-моему с этим ключом что-то не так '''
		return None
	#Vulnerability: DoS by posting wrong keys or just spamming
	savechatkeyRSA(uid,cid,key)
	joinchat(uid,cid)
	return None
	
''' returns tuple of cid,name '''
def getchats(uid):
	sql,cur=getsql()
	cur.execute("SELECT chats.cid,name FROM chats INNER JOIN chatusers ON chats.cid = chatusers.cid WHERE uid=%s ORDER BY cid DESC",(uid))
	pairz=[{'id':x[0],'name':x[1]} for x in cur.fetchall()]
	closql(sql,cur)	
	return pairz

def getpubkey(name):
	''' Так повелось, что публичный ключ кого угодно может получить кто угодно другой, ничего плохого '''
	sql,cur=getsql()
	cur.execute("SELECT pubkey FROM users WHERE name=%s",(name))
	ret=cur.fetchall()
	if (len(ret)!=0):
		ret=ret[0][0]
	else:
		ret=''
	closql(sql,cur)
	return ret

def savechatkey(uid,cid,key):
	sql,cur=getsql()
	cur.execute("INSERT INTO aeskeys (uid,cid,`key`) VALUES (%s,%s,%s)",(uid,cid,key))
	sql.commit()
	closql(sql,cur)
	return ''

def savechatkeyRSA(uid,cid,key):
	sql,cur=getsql()
	cur.execute("INSERT INTO invites (uid,cid,`key`) VALUES (%s,%s,%s)",(uid,cid,key))
	sql.commit()
	closql(sql,cur)
	return ''

def loadchatkey(uid,cid):
	sql,cur=getsql()
	cur.execute("SELECT `key` FROM aeskeys WHERE uid=%s AND cid=%s",(uid,cid))
	ret=cur.fetchall()
	if (len(ret)!=0):
		ret=ret[0][0]
	else:
		ret=''
	closql(sql,cur)
	return ret

def loadchatkeyRSA(uid,cid):
	sql,cur=getsql()
	cur.execute("SELECT `key` FROM invites WHERE uid=%s AND cid=%s",(uid,cid))
	ret=cur.fetchall()
	if (len(ret)!=0):
		ret=ret[0][0]
	else:
		ret=''
	closql(sql,cur)
	return ret

def pastepost(message):
	sql,cur=getsql()
	cur.execute("INSERT INTO paste (message) VALUES (%s)",(message))
	cur.execute("SELECT LAST_INSERT_ID()")	
	cid = cur.fetchone()[0]
	sql.commit()
	closql(sql,cur)
	return str(cid)

def pasteget(idx):
	sql,cur=getsql()
	cur.execute("SELECT message FROM paste WHERE id=%s",(idx))
	retx=cur.fetchall()
	if (len(retx)!=0):
		retx=retx[0][0]
	else:
		retx=''
	closql(sql,cur)
	return retx
