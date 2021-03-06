from argparse import _ActionsContainer
import sqlite3 as sql
from sqlite3 import IntegrityError
import time

DATABASE_FILE = "ds2015.db"
CHUNK_SIZE = 250000

def init():
    cur, conn = getCursor()
    cur.execute('''
       CREATE TABLE IF NOT EXISTS hashes
       (
       id INTEGER PRIMARY KEY ASC,
       hash TEXT UNIQUE,
       created_time REAL,
       started_time REAL,
       solved_time REAL,
       solved INTEGER DEFAULT 0,
       solution TEXT,
       solvable INTEGER DEFAULT 1
       )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS progress
        (
        hash_id INTEGER REFERENCES hashes(id) ON DELETE CASCADE,
        character TEXT,
        row REAL
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS clients
        (
        id TEXT UNIQUE,
        hash_working INTEGER,
        join_time REAL,
        last_ping REAL
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS work
        (
        id INTEGER PRIMARY KEY ASC,
        hash_id INTEGER REFERENCES hashes(id) ON DELETE CASCADE,
        character TEXT,
        progress REAL,
        done INTEGER DEFAULT 0
        )
    ''')

def addWork(target, character, progress):
    cur, conn = getCursor()
    cur.execute("SELECT id FROM hashes WHERE hash = '" + str(target) + "'")
    for row in cur:
        hash_id = row[0]
    cur.execute("INSERT INTO work (hash_id, character, progress) VALUES ("+str(hash_id)+",'"+str(character)+"','"+str(progress)+"')")
    conn.commit()

def executeWork(target, character, progress):
    print "executing work " + str(target) + str(character) + str(progress)
    if len(target) == 0:
        return 0
    cur, conn = getCursor()
    cur.execute("SELECT id FROM hashes WHERE hash = '" + str(target) + "'")
    for row in cur:
        hash_id = row[0]
    cur.execute("UPDATE work SET done = 1 WHERE hash_id = '" + str(hash_id) + "' AND character = '"+str(character)+"' AND progress='"+str(progress)+"'")
    conn.commit()

def getUnfinishedWork():
    cur, conn = getCursor()
    cur.execute("SELECT hashes.hash, character, progress FROM work JOIN hashes ON hashes.id = work.hash_id WHERE done = 0")
    for row in cur:
        return str(row[0]), str(row[1]), row[2]
    return None, None, None

def getClients():
    result = []
    cur, conn = getCursor()
    cur.execute('''
        SELECT * FROM clients
    ''')
    for row in cur:
        result.append(row)

    return result

def getUnsolvedHashes():
    result = []
    cur, conn = getCursor()
    cur.execute("SELECT * FROM hashes WHERE solved = 0 AND solvable = 1")
    for row in cur:
        result.append(row)
    return result

def getSolvedHashes():
    result = []
    cur, conn = getCursor()
    cur.execute("SELECT * FROM hashes WHERE solved = 1")
    for row in cur:
        result.append(row)
    return result


def getProgress(client_id):
    ###print "getprogress"
    hash_id = 0
    target = ""
    cur, conn = getCursor()
    sql = "SELECT clients.hash_working FROM clients JOIN hashes ON hashes.id = clients.hash_working WHERE clients.id = '" + str(client_id) + "' AND hashes.solvable = 1"
    cur.execute(sql)
    found = False
    for row in cur:
        hash_id = row[0]
        if not hash_id:
            return None, None, None
    if not found:
        return getNextHash()


def getNextHash():

    cur, conn = getCursor()
    cur.execute("SELECT id, hash FROM hashes WHERE solved = 0 AND solvable = 1 ORDER BY created_time LIMIT 1")
    found = False
    for row in cur:
        #print row[0]
        hash_id = row[0]
        target = row[1]
        found = True
    if not found:
        return None, None, None

    sql = "SELECT hashes.solvable, progress.character, progress.row FROM progress JOIN hashes ON hashes.id = progress.hash_id WHERE hash_id = '" + str(hash_id) + "'"
    cur.close()
    cur, conn = getCursor()
    cur.execute(sql)
    for row in cur:
        updateClient(hash_id, row[1], row[2])
        nextChunk(hash_id)
        #print "returning " + target + str(row[1]) + str(row[2])
        return target, row[1], row[2]


# update client progress
def updateClient(hash_id, character, row):
    cur, conn = getCursor()
    cur.execute("UPDATE progress SET character = '" + str(character) + "', row = '" + str(row)+ "' WHERE hash_id = '" + str(hash_id) + "'")
    conn.commit()

# set client to work on hash x
def setClientWorking(target, client_id):
    cur, conn = getCursor()
    cur.execute("SELECT id FROM hashes WHERE hash = '" + str(target) + "'")
    for row in cur:
        hash_id = row[0]
    cur.execute("UPDATE clients SET hash_working = '" + str(hash_id) + "' WHERE id = '" + str(client_id) + "'")
    conn.commit()
    ping(client_id)

def nextChunk(hash_id):
    ###print "nextchunk"
    cur, conn = getCursor()
    cur.execute("SELECT row FROM progress WHERE hash_id = '" + str(hash_id) + "'")
    found = False
    for row in cur:
        curRow = row[0]
        found = True
        ###print "found"
    if not found:
        return 0
    cur.execute("UPDATE progress SET row = " + str(curRow + CHUNK_SIZE))
    conn.commit()
    cur.close()


def nextCharacter(target_hash):
    cur, conn = getCursor()

    cur.execute("SELECT id FROM hashes WHERE hash = '" + target_hash + "' AND solvable = 1 AND solved = 0")
    for row in cur:
        hash_id = row[0]
    cur.execute("SELECT character FROM progress WHERE hash_id = '" + str(hash_id) + "'")
    for row in cur:
        curChar = row[0]

    new_char = ""
    ## if not end of alphabets
    if ord(curChar) < 122:
        new_char = chr(ord(curChar) + 1)
    else:
        target, character, progress = getUnfinishedWork()
        if not target:
            couldNotSolve(hash_id)
        return target, character, progress

    cur.execute("UPDATE progress SET character = '" + str(new_char) + "', row = 0 WHERE hash_id = '" + str(hash_id) + "'")
    conn.commit()
    return None, None, None
    

def solve(target, solution):
    cur, conn = getCursor()
    cur.execute("UPDATE hashes SET solved = 1, solution = '" + str(solution) + "' WHERE hash = '" + target + "'")
    conn.commit()

def couldNotSolve(hash_id):
    cur, conn = getCursor()
    print "setting " + str(hash_id) + " to unsolvable"
    cur.execute("UPDATE hashes SET solvable = 0 WHERE id = '" + str(hash_id) + "'")
    conn.commit()

def post_hash(hash):
    cur, conn = getCursor()
    sql = "INSERT INTO hashes (hash, created_time) VALUES ('" + str(hash) + "'," + str(time.time()) + ")"
    try:
        cur.execute(sql)
        conn.commit()
        lastid = cur.lastrowid
    except IntegrityError:
        conn.close()
        return "Hash already exists"

    cur.execute("INSERT INTO progress VALUES (" + str(lastid) + ",'a', 1)")
    conn.commit()
    cur.execute("SELECT * FROM hashes WHERE id = " + str(lastid))
    for row in cur:
        return row

def connectClient(client_id):
    cur, conn = getCursor()

    #print "connecting " + client_id
    try:
        cur.execute("INSERT INTO clients (id, join_time, last_ping) VALUES ('"+str(client_id)+"', "+str(time.time())+"," +str(time.time())+")")
        conn.commit()

    except Exception:
        return "FAILURE, not unique"
    sql = "SELECT last_ping FROM clients WHERE id = '" + str(client_id) + "'"
    cur.execute(sql)

    for row in cur:
        conn.close()
        return "OK"

    conn.close()
    return "FAILURE"

def disconnect(client_id):
    cur, conn = getCursor()
    cur.execute("DELETE FROM clients WHERE id = '" + str(client_id) + "'")
    conn.commit()
    conn.close()
    #print "Disconnected " + str(client_id)
    return "Deleted"

def ping(client_id):
    cur, conn = getCursor()
    now = time.time()
    #print "ping : " + str(now)
    #print "client : " + str(client_id)
    cur.execute("UPDATE clients SET last_ping = " + str(now) + " WHERE id = '" + str(client_id) + "'")
    conn.commit()
    cur.close()
    return str(now)

def getPing(client_id):
    cur, conn = getCursor()
    cur.execute("SELECT last_ping FROM clients WHERE id = '" + str(client_id) + "'")
    for row in cur:
        return str(row[0])

# remove nonresponding clients
def killThemDead():
    cur, conn = getCursor()
    now = time.time()
    #print "killing, now = " + str(now)
    cur.execute("SELECT id, last_ping FROM clients")
    for row in cur:
        #print "client last_ping = " + str(row[1])
        #print "diff = " + str(now - float(row[1]))
        # if client not responed for 60 seconds
        if (now - float(row[1])) > 90.0:
            cur.execute("DELETE FROM clients WHERE id ='" + str(row[0]) + "'")
            conn.commit()


def getCursor():
    c = sql.connect(DATABASE_FILE)
    c.cursor().execute("PRAGMA foreign_keys = ON")
    return c.cursor(), c