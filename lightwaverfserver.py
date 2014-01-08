from flask import Flask, render_template, request
import logging, socket, json, math, time, httplib



app = Flask(__name__)
app.config.from_pyfile('settings.py')
logging.basicConfig(format='%(asctime)s: %(message)s', level=logging.DEBUG, filename='lightwave.log')

try:
    config = json.load(open('lightwaverf-config.json'))
except:
    logging.info("Couldn't load config file")
    config = {}

####################################################
#
#  Delete this section to remove Sonos support
#
#
#####################################################

from soco import SoCo
@app.route('/sonos/<command>/<int:volume>')
@app.route('/sonos/<command>')
def sonos(command, volume=-1):
    s = SoCo(app.config['SONOS'])
    try:
        if command == 'play':
            s.play()
        elif command == 'pause':
            s.pause()
        elif command =='volume':
            logging.info('Setting volume of Sonos to %d' % volume)
            s.volume(volume)
        elif command == 'next':
            s.next()
        elif command == 'previous':
            s.previous()
        return "OK"
    except:
        return "FAIL"

#######################################################        

@app.route('/')
def hello_world():
    return 'Seems to be working!'

@app.route('/configure', methods=['GET', 'POST'])
def newConfiguration():
    if request.method == 'GET':
        return render_template('newconfiguration.html')
    if request.method == 'POST':
        tempconfig = {"rooms":{}}
        for r in range(1,7):
            try:
                room = request.form['room-%d' % r]
                if  room:
                    tempconfig['rooms'][room] = {}
                    tempconfig['rooms'][room]['devices'] = (request.form[('room-%d-devices-hidden' % r)])[1:].split(',')
                    tempconfig['rooms'][room]['moods'] = (request.form[('moods-%d-hidden' % r)])[1:].split(',')
            except:
                pass
        return render_template('newconfiguration.html', tempconfig=tempconfig, data=request.form)
    
    
@app.route('/controller')
def showConfiguration():
    return render_template('controller.html', config=config)

@app.route('/alloff')
def alloff():
    for room in config['rooms']:
        doCommand(room, command='alloff')
    return "Turned everything off"   
    
@app.route('/<room>/<command>')
@app.route('/<room>/<device>/<command>')
@app.route('/<room>/<device>/<command>/<int:dim>')
def doCommand(room, device=None, command=None, dim=-1):
    logging.info("Got command '%s' for %s in %s" % (command, device, room))
    try:
        roomid = config['rooms'][room]['id']
        if device == 'moods':
            moodid = config['rooms'][room]['moods'].index(command)+1
            sendCommand('%s,!R%dFmP%d%s' % (app.config['START'], roomid, moodid, app.config['END']))
            return "Setting %s to %s mood" % (room, command)
        if command == 'on':
            dim=100
        if command == 'allon':
            print config['rooms'][room]['devices']
            for d in config['rooms'][room]['devices']:
                time.sleep(1.5)
                doCommand(room, d, 'on')
            return "Turning everything on in %s" % room
        if command == 'alloff':
            sendCommand('%s,!R%dFa%s' % (app.config['START'], roomid, app.config['END']))
            return "Turning everything off in %s" % room
        deviceid = config['rooms'][room]['devices'].index(device)+1
        if dim >=0:
            level = math.floor(0.01 * float(dim) * 32)
            sendCommand('%s,!R%dD%dFdP%d%s' % (app.config['START'], roomid, deviceid, level, app.config['END']))
            return "Dimming %s in %s to %d" % (device, room, dim)

    except KeyError:
        return "Sorry, I couldn't find %s in your list of rooms." % (room)
    except ValueError:
        return "Sorry, I couldn't find %s in your list of devices for room %s. The only ones I know about are %s" % (device, room, str(config['rooms'][room]['devices']))
    message = '%s,!R%dD%dF%d%s' % (app.config['START'], roomid, deviceid, 0,app.config['END'])
    sendCommand(message)
    return "Sending command %s to %s in %s" % (command, device, room)

@app.route('/raw/<command>')
def sendRawCommand(command):
    sendCommand(command + '\0')
    return command

def sendCommand(command):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    receivesock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    receivesock.bind(('0.0.0.0', app.config['UDP_PORT']+1))
    logging.info('Sending message %s' % command)
    try:
        sock.sendto(command, (app.config['UDP_IP'], app.config['UDP_PORT']))
        receivesock.settimeout(15.0)
        d = receivesock.recvfrom(1024)
        reply = d[0]
        addr = d[1]
        logging.info( 'Server reply: ' + reply)
    except socket.error, msg:
        logging.error( 'Error message : ' + str(msg))
    
    
if __name__ == '__main__':
    app.debug = True
    app.run(host=app.config['HOST'])
