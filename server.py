from argparse import _ActionsContainer
from flask import Flask, url_for, request
import json
import db_model

DEBUG = True

app = Flask(__name__)

def setup():
    db_model.init()

@app.route('/hash/', methods=['GET', 'POST'])
def hash():
    db_model.killThemDead()
    if request.method == 'POST':
        for k in request.form:
            resp = db_model.post_hash(k)
            return json.dumps(resp)
    else:
        return json.dumps(db_model.getUnsolvedHashes())

@app.route('/join', methods=['POST'])
def join():
    for k in request.form:
        resp = db_model.connectClient(request.form[k].encode('rot13'))
    return resp

@app.route('/disconnect', methods=['POST'])
def disconnect():
    for k in request.form:
        resp = db_model.disconnect(request.form[k].encode('rot13'))
    return resp

@app.route('/start_crack', methods=['POST'])
def start_crack():
    result = []
    client_id = str(request.form["client_id"].encode('rot13'))
    db_model.executeWork(
        request.form["target"].encode('rot13'),
        request.form["character"].encode('rot13'),
        request.form["progress"].encode('rot13')
    )
    if not client_id:
        return "No client id given."
    #print "starting " + client_id
    if client_id == "aaaaa":
        return 0
    target, character, progress = db_model.getNextHash()
    if not character:
        return "No hashes to solve!"
    f = open("wordlists/dictionary_huge_" + character + ".dic", 'r')
    rowcount = 0
    readrows = 0
    while readrows < db_model.CHUNK_SIZE:
        row = f.readline()
        ## end of file
        if not row:
            ## EOF
            f.close()
            newtarget, newchar, newprog = db_model.nextCharacter(target)
            if not newtarget:
                break
            else:
                for row in readfile(newchar, newprog):
                    result.append(row)
                break
        if ((rowcount <= progress + db_model.CHUNK_SIZE) & (rowcount >= progress)):
            result.append(row.rstrip().encode('rot13'))
            readrows += 1
        rowcount += 1
    f.close()

    resp = dict()
    resp["char"] = character.encode('rot13')
    resp["progress"] = str(progress).encode('rot13')
    resp["target"] = target.encode('rot13')
    resp["words"] = result
    db_model.setClientWorking(target, client_id)
    db_model.addWork(target, character, progress)
    return json.dumps(resp)


@app.route('/next', methods=['POST'])
def next():
    db_model.killThemDead()
    client_id = str(request.form["client_id"].encode('rot13'))
    db_model.executeWork(
        request.form["target"].encode('rot13'),
        request.form["character"].encode('rot13'),
        request.form["progress"].encode('rot13')
    )
    if not client_id:
        return "No client id given."
    result = []
    target, character, progress = db_model.getProgress(client_id)
    if not character:
        "Could not find progress for client_id = " + client_id
        target, character, progress = db_model.getNextHash()

    if not target:
        resp = dict()
        resp["target"] = "No hashes to solve."
        result = []
        result.append("No hashes to solve.")
        resp["words"] = result
        print "nothing to solve"
        return json.dumps(resp)
    f = open("wordlists/dictionary_huge_" + character + ".dic", 'r')
    rowcount = 0
    readrows = 0

    while readrows < db_model.CHUNK_SIZE:
        row = f.readline()
        ## end of file
        if not row:
            #print "EOF"
            f.close()
            newtarget, newchar, newprog = db_model.nextCharacter(target)
            if not newtarget:
                break
            else:
                for row in readfile(newchar, newprog):
                    result.append(row)
                break

        if ((rowcount <= progress + db_model.CHUNK_SIZE) & (rowcount >= progress)):
            result.append(row.rstrip().encode('rot13'))
            readrows += 1
        rowcount += 1
    f.close()

    resp = dict()
    resp["char"] = character.encode('rot13')
    resp["progress"] = str(progress).encode('rot13')
    resp["target"] = target.encode('rot13')
    resp["words"] = result

    db_model.setClientWorking(target, client_id)
    db_model.addWork(target, character, progress)
    return json.dumps(resp)

def readfile(character, progress):
    print "read file!"
    f = open("wordlists/dictionary_huge_" + character + ".dic", 'r')
    rowcount = 0
    readrows = 0

    while readrows < db_model.CHUNK_SIZE:
        row = f.readline()
        ## end of file
        if not row:
            #print "EOF"
            break

        if ((rowcount <= progress + db_model.CHUNK_SIZE) & (rowcount >= progress)):
            yield row.rstrip().encode('rot13')
            readrows += 1
        rowcount += 1
    f.close()


@app.route('/found', methods=['POST'])
def found():
    #print "FOUND IT"
    solution = request.form["solution"]
    target = request.form["target"]
    db_model.solve(target, solution)
    return ":)(:"

@app.route('/ping', methods=['POST'])
def ping():
    for k in request.form:
        return db_model.ping(request.form[k].encode('rot13'))


@app.route('/')
def server_ui():
    db_model.killThemDead()
    resp = '''<link rel=stylesheet type=text/css href=''' + url_for('static', filename='ui.css') + '''>'''
    resp += '''<script type=text/javascript src=''' + url_for('static', filename='jquery-1.11.3.min.js') + '''></script>'''
    resp += '''<script type=text/javascript src=''' + url_for('static', filename='ui.js') + '''></script>'''

    resp += '''
    <div class='add_new_hash'>
        Add new hash to bruteforce: <input type='text' id='new_hash' size='36'></input><div class='submit_button'>Submit</div>
    </div>
    '''

    unsolvedHashes = db_model.getUnsolvedHashes()
    resp += "<div class='hashes'>Unsolved hashes:<br>"

    for h in unsolvedHashes:
        resp += '''
            <div class='hash_row'>
                <div class='hash_id'>ID: ''' + str(h[0]) + '''</div>
                <div class='hash_string'>Hash:    ''' + str(h[1]) + '''</div>
                <div class='hash_start'>Created: ''' + str(h[2]) + '''</div>
            </div>
        '''

    resp += "</div>"

    clientProgress = db_model.getClients()
    resp += "<div class='clients'>Connected clients:<br>"

    for c in clientProgress:
        resp += '''
        <div class='client_row'>
            <div class='client_id'>Client id:    ''' + str(c[0]) + '''</div>
            <div class='client_working'>Working on:   ''' + str(c[1]) + '''</div>
            <div class='client_ping'>Last contact: ''' + str(c[3]) + '''</div>
        </div>
        '''

    resp += "</div>"

    solvedHashes = db_model.getSolvedHashes()
    resp += "<div class='hashes_solved'>Solved hashes:<br>"

    for h in solvedHashes:
        resp += '''
            <div class='hash_row_solved'>
                <div class='hash_string'>Hash:    ''' + str(h[1]) + '''</div>
                <div class='hash_start'>Created: ''' + str(h[2]) + '''</div>
                <div class='hash_solution'>Solution: ''' + str(h[6]) + '''</div>
                <div class='hash_solution_time'>Solved on : ''' + str(h[4]) + '''</div>
            </div>
        '''

    resp += "</div>"

    return resp

if __name__ == '__main__':
    db_model.init()
    app.debug = DEBUG
    ## if public
    #app.run(host='0.0.0.0')
    ## if private
    app.run()