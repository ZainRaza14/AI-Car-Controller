import socket 
import sys
import getopt
import pandas as pd
import numpy as np
import math as mt
PI= 3.14159265359

# Initialize help messages
ophelp=  'Options:\n'
ophelp+= ' --host, -H <host>    TORCS server host. [localhost]\n'
ophelp+= ' --port, -p <port>    TORCS port. [3001]\n'
ophelp+= ' --id, -i <id>        ID for server. [SCR]\n'
ophelp+= ' --steps, -m <#>      Maximum simulation steps. 1 sec ~ 50 steps. [100000]\n'
ophelp+= ' --episodes, -e <#>   Maximum learning episodes. [1]\n'
ophelp+= ' --track, -t <track>  Your name for this track. Used for learning. [unknown]\n'
ophelp+= ' --stage, -s <#>      0=warm up, 1=qualifying, 2=race, 3=unknown. [3]\n'
ophelp+= ' --debug, -d          Output full telemetry.\n'
ophelp+= ' --help, -h           Show this help.\n'
ophelp+= ' --version, -v        Show current version.'
usage= 'Usage: %s [ophelp [optargs]] \n' % sys.argv[0]
usage= usage + ophelp
version= "20130505-2"

# ==============================================
# ============== CLASSES =======================
# ==============================================
class Client():
    def __init__(self,H=None,p=None,i=None,e=None,t=None,s=None,d=None):
        # If you don't like the option defaults,  change them here.
        self.host= 'localhost'
        self.port= 3002
        self.sid= 'SCR'
        self.maxEpisodes=1
        self.trackname= 'unknown'
        self.stage= 3
        self.debug= False
        self.maxSteps= 100000  # 50steps/second
        self.parse_the_command_line()
        if H: self.host= H
        if p: self.port= p
        if i: self.sid= i
        if e: self.maxEpisodes= e
        if t: self.trackname= t
        if s: self.stage= s
        if d: self.debug= d
        self.S= ServerState()
        self.R= DriverAction()
        self.setup_connection()

    def conn_ok(self):
        if self.so == None:
            return False
        return True

    def setup_connection(self):
        # == Set Up UDP Socket ==
        try:
            self.so= socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        except socket.error, emsg:
            print 'Error: Could not create socket...'
            sys.exit(-1)
        # == Initialize Connection To Server ==
        self.so.settimeout(1)
        while True:
            a= "-90 -75 -60 -45 -30 -20 -15 -10 -5 0 5 10 15 20 30 45 60 75 90"
            initmsg='%s(init %s)' % (self.sid,a)

            try:
                self.so.sendto(initmsg, (self.host, self.port))
            except socket.error, emsg:
                sys.exit(-1)
            sockdata= str()
            try:
                sockdata,addr= self.so.recvfrom(1024)
            except socket.error, emsg:
                print "Waiting for server............"
            if '***identified***' in sockdata:
                print "Client connected.............."
                break

    def parse_the_command_line(self):
        try:
            (opts, args) = getopt.getopt(sys.argv[1:], 'H:p:i:m:e:t:s:dhv',
                       ['host=','port=','id=','steps=',
                        'episodes=','track=','stage=',
                        'debug','help','version'])
        except getopt.error, why:
            print 'getopt error: %s\n%s' % (why, usage)
            sys.exit(-1)
        try:
            for opt in opts:
                if opt[0] == '-h' or opt[0] == '--help':
                    print usage
                    sys.exit(0)
                if opt[0] == '-d' or opt[0] == '--debug':
                    self.debug= True
                if opt[0] == '-H' or opt[0] == '--host':
                    self.host= opt[1]
                if opt[0] == '-i' or opt[0] == '--id':
                    self.sid= opt[1]
                if opt[0] == '-t' or opt[0] == '--track':
                    self.trackname= opt[1]
                if opt[0] == '-s' or opt[0] == '--stage':
                    self.stage= opt[1]
                if opt[0] == '-p' or opt[0] == '--port':
                    self.port= int(opt[1])
                if opt[0] == '-e' or opt[0] == '--episodes':
                    self.maxEpisodes= int(opt[1])
                if opt[0] == '-m' or opt[0] == '--steps':
                    self.maxSteps= int(opt[1])
                if opt[0] == '-v' or opt[0] == '--version':
                    print '%s %s' % (sys.argv[0], version)
                    sys.exit(0)
        except ValueError, why:
            print 'Bad parameter \'%s\' for option %s: %s\n%s' % (
                                       opt[1], opt[0], why, usage)
            sys.exit(-1)
        if len(args) > 0:
            print 'Superflous input? %s\n%s' % (', '.join(args), usage)
            sys.exit(-1)

    def get_servers_input(self):
        '''Server's input is stored in a ServerState object'''
        if not self.so: return
        sockdata= str()
        while True:
            try:
                # Receive server data 
                sockdata,addr= self.so.recvfrom(1024)
            except socket.error, emsg:
                print "Waiting for data.............."

            if '***identified***' in sockdata:
                print "Client connected.............."
                continue
            elif '***shutdown***' in sockdata:
                print "SHUTDOWN MESSAGE : ", sockdata
                print "Server has stopped the race. You were in %d place." % self.S.d['racePos']
                self.shutdown()
                return
            elif '***restart***' in sockdata:
                # What do I do here?
                print "SHUTDOWN MESSAGE : ", sockdata
                print "Server has restarted the race."
                # I haven't actually caught the server doing this.
                self.shutdown()
                return
            elif not sockdata: # Empty?
                continue       # Try again.
            else:
                self.S.parse_server_str(sockdata)
                if self.debug: print self.S
                break # Can now return from this function.

    def respond_to_server(self):
        if not self.so: return
        if self.debug: print self.R
        try:
            self.so.sendto(repr(self.R), (self.host, self.port))
        except socket.error, emsg:
            print "Error sending to server: %s Message %s" % (emsg[1],str(emsg[0]))
            sys.exit(-1)

    def shutdown(self):
        if not self.so: return
        print "Race terminated or %d steps elapsed. Shutting down." % self.maxSteps
        self.so.close()
        self.so= None
        #sys.exit() # No need for this really.

class ServerState():
    'What the server is reporting right now.'
    def __init__(self):
        self.servstr= str()
        self.d= dict()

    def parse_server_str(self, server_string):
        'parse the server string'
        self.servstr= server_string.strip()[:-1]
        sslisted= self.servstr.strip().lstrip('(').rstrip(')').split(')(')
        for i in sslisted:
            w= i.split(' ')
            self.d[w[0]]= destringify(w[1:])

    def __repr__(self):
        out= str()
        for k in sorted(self.d):
            strout= str(self.d[k])
            if type(self.d[k]) is list:
                strlist= [str(i) for i in self.d[k]]
                strout= ', '.join(strlist)
            out+= "%s: %s\n" % (k,strout)
        return out

class DriverAction():
    '''What the driver is intending to do (i.e. send to the server).
    Composes something like this for the server:
    (accel 1)(brake 0)(gear 1)(steer 0)(clutch 0)(focus 0)(meta 0) or
    (accel 1)(brake 0)(gear 1)(steer 0)(clutch 0)(focus -90 -45 0 45 90)(meta 0)'''
    def __init__(self):
       self.actionstr= str()
       # "d" is for data dictionary.
       self.d= { 'accel':0.2,
                   'brake':0,
                  'clutch':0,
                    'gear':1,
                   'steer':0,
                   'focus':[-90,-45,0,45,90],
                    'meta':0 
                    }

    def __repr__(self):
        out= str()
        for k in self.d:
            out+= '('+k+' '
            v= self.d[k]
            if not type(v) == list:
                out+= '%.3f' % v
            else:
                out+= ' '.join([str(x) for x in v])
            out+= ')'
        return out
        return out+'\n'

# ==============================================
# ============= UTILITY FUCNTION ===============
# ==============================================
def destringify(s):
    '''makes a string into a value or a list of strings into a list of
    values (if possible)'''
    if not s: return s
    if type(s) is str:
        try:
            return float(s)
        except ValueError:
            print "Could not find a value in %s" % s
            return s
    elif type(s) is list:
        if len(s) < 2:
            return destringify(s[0])
        else:
            return [destringify(i) for i in s]

def clip(v,lo,hi):
    if v<lo: return lo
    elif v>hi: return hi
    else: return v

# ==============================================
# ============= DRIVER FUCNTIONS  ==============
# ==============================================
def drive_next_gen(c):

    S = c.S.d
    R = c.R.d
    target_speed = 300

    steer = (S['angle'] - S['trackPos'] * 0.5) / 0.78
    # print "---data---"
    # print steer
    # print S['angle']
    # print S['trackPos']
    
    speed_estimator = 1
    breaking = 0.05

    if ((S['track'][8] + S['track'][9] + S['track'][10]) / 3) > -1:
        est_speed = (speed_estimator * (S['track'][8] + S['track'][9] + S['track'][10]))
        if est_speed >= target_speed:    est_speed -= 5
        else:    est_speed += 5
    else:
        est_speed = (speed_estimator * 20)
        if est_speed >= target_speed:    est_speed -= 5
        else:    est_speed += 5

    diff = est_speed - S['speedX']

    if diff <= 0:
        if S['track'][9] >= 50:
            brake = ((diff / est_speed) * breaking) * -3
        elif S['track'][9] >= 75:
            brake = ((diff / est_speed) * breaking) * -2
        else:
            brake = ((diff / est_speed) * breaking) * -1
        acce = ((diff / est_speed) * 0.2) + 0.4
    else:
        brake = 0
        acce = ((diff / est_speed) * 10) + 0.4

    R['gear'] = 1
    if ((S['track'][8] + S['track'][9] + S['track'][10]) / 3) == -1:
        if S['speedX'] < 5:
            R['gear'] = -1
            acce = ((diff / est_speed) * 0.2) + 0.4
            steer = -0.85  

    R['steer'] = steer
    R['accel'] = acce
    R['brake'] = brake

    if R['gear'] != -1:
        R['gear']=1
        if S['speedX']>=80:
            R['gear']=2
        if S['speedX']>=110:
            R['gear']=3
        if S['speedX']>=160:
            R['gear']=4
        if S['speedX']>=200:
            R['gear']=5
        if S['speedX']>=250:
            R['gear']=6

    # 78, 104, 145, 178, 230
    return {'S':(S['track'][8], S['track'][9], S['track'][10], S['angle'], S['trackPos'], S['speedX']), 'R':(speed_estimator, breaking)}

def drive_example_gen(c, driver):

    S = c.S.d
    R = c.R.d
    target_speed = 300

    speed_estimator = 0
    breaking = 0

    if driver == 5:
        speed_estimator = 0.7
        breaking = 0.05
    elif driver == 6:
        speed_estimator = 0.5
        breaking = 0.1
    elif driver == 7:
        speed_estimator = 0.5
        breaking = 0.02
    elif driver == 8:           # ModVerof-5
        # 3.03, T4, L1
        speed_estimator = 0.6
        breaking = 0.1
    elif driver == 9:           # ModVerof-6 
        # 3.13, T4, L1
        speed_estimator = 0.5
        breaking = 0.05
    elif driver == 10:           # ModVerof-8
        # 2.58, T4, L1
        speed_estimator = 0.6
        breaking = 0.08
    elif driver == 11:           # ModVerof-8
        # 0.0, T4, L1
        speed_estimator = 2
        breaking = 0.05
    elif driver == 12:           # ModVerof-8
        # 0.0, T4, L1
        speed_estimator = 0.5
        breaking = 0.08
    elif driver == 13:
        if S['track'][9] >= 170:   
            speed_estimator = 2
            breaking = 0.05
        elif S['track'][9] >= 150:  
            speed_estimator = 1
            breaking = 0.07
        else:
            speed_estimator = 0.6
            breaking = 0.08
    elif driver == 14:
        avg = (S['track'][8] + S['track'][9] + S['track'][10]) / 3
        if avg >= 104:
            speed_estimator = 2
            breaking = 0.06
        elif avg >= 85:
            speed_estimator = 1
            breaking = 0.07
        elif avg >= 70:
            speed_estimator = 0.7
            breaking = 0.08
        elif avg >= 55:
            speed_estimator = 0.5
            breaking = 0.1
        else:
            speed_estimator = 0.4
            breaking = 0.05

        # print breaking
    elif driver == 15:
        if S['track'][9] >= 170:   
            speed_estimator = 1
            breaking = 0.05
        elif S['track'][9] >= 150:  
            speed_estimator = 0.6
            breeaking = 0.07
        elif S['track'][9] >= 100:  
            speed_estimator = 0.5
            breeaking = 0.1
        else:
            speed_estimator = 0.4
            breaking = 0.08

    # Comments
    # ( 57.4882 , 200.0 , 57.2495 )   - straight  (314) - 105
    # ( 86.5782 , 54.1852 , 33.8532 ) - left      (173) - 58
    # ( 150.244 , 79.7689 , 41.7256 ) - left      (270) - 90
    # ( 31.5755 , 42.3964 , 52.9153 ) - right     (125) - 42


    if ((S['track'][8] + S['track'][9] + S['track'][10]) / 3) > -1:
        est_speed = (speed_estimator * (S['track'][8] + S['track'][9] + S['track'][10]))
        if est_speed >= target_speed:    est_speed -= 5
        else:    est_speed += 5
    else:
        est_speed = (speed_estimator * 20)
        if est_speed >= target_speed:    est_speed -= 5
        else:    est_speed += 5

    diff = est_speed - S['speedX']
    acce = ((diff / est_speed) * 0.2) + 0.4

    if diff <= 0:
        brake = ((diff / est_speed) * breaking) * -1
    else:
        brake = 0
        acce = ((diff / est_speed) * 10) + 0.4

    steer = (S['angle'] - S['trackPos'] * 0.5) / 0.78

    # R['gear'] = 1
    # if ((S['track'][8] + S['track'][9] + S['track'][10]) / 3) == -1:
    #     if mt.floor(S['speedX']) == 0:
    #         R['gear'] = -1
    #         acce = ((diff / est_speed) * 0.2) + 0.4
    #         if S['angle'] < -1:     steer = -1
    #         else:    steer = 1

    # R['gear'] = gear
    R['steer'] = steer
    R['accel'] = acce
    R['brake'] = brake

    # Automatic Transmission
    if R['gear'] != -1:
        R['gear']=1
        if S['speedX']>=78:
            R['gear']=2
        if S['speedX']>=104:
            R['gear']=3
        if S['speedX']>=145:
            R['gear']=4
        if S['speedX']>=178:
            R['gear']=5
        if S['speedX']>=220:
            R['gear']=6

    # print S['angle']
    return {'S':(S['track'][8], S['track'][9], S['track'][10], S['angle'], S['trackPos'], S['speedX']), 'R':(speed_estimator, breaking)}

def drive_example_gen_2(c, driver):

    S = c.S.d
    R = c.R.d
    target_speed = 300

    speed_estimator = 0
    breaking = 0

    if driver == 6:
        speed_estimator = 0.5
        breaking = 0.1
    elif driver == 7:
        speed_estimator = 0.5
        breaking = 0.02
    elif driver == 13:
        if S['track'][9] >= 170:   
            speed_estimator = 2
            breaking = 0.05
        elif S['track'][9] >= 150:  
            speed_estimator = 1
            breaking = 0.07
        else:
            speed_estimator = 0.6
            breaking = 0.08
    
    print speed_estimator, breaking

    if ((S['track'][8] + S['track'][9] + S['track'][10]) / 3) > -1:
        est_speed = (speed_estimator * (S['track'][8] + S['track'][9] + S['track'][10]))
        if est_speed >= target_speed:    est_speed -= 5
        else:    est_speed += 5
    else:
        est_speed = (speed_estimator * 20)
        if est_speed >= target_speed:    est_speed -= 5
        else:    est_speed += 5

    diff = est_speed - S['speedX']
    acce = ((diff / est_speed) * 0.2) + 0.4

    if diff <= 0:
        if S['track'][9] >= 50:
            brake = ((diff / est_speed) * breaking) * -3
        elif S['track'][9] >= 75:
            brake = ((diff / est_speed) * breaking) * -2
        else:
            brake = ((diff / est_speed) * breaking) * -1
    else:
        brake = 0
        acce = ((diff / est_speed) * 10) + 0.4

    steer = (S['angle'] - S['trackPos'] * 0.5) / 0.78

    # R['gear'] = 1
    # if ((S['track'][8] + S['track'][9] + S['track'][10]) / 3) == -1:
    #     if mt.floor(S['speedX']) == 0:
    #         R['gear'] = -1
    #         acce = ((diff / est_speed) * 0.2) + 0.4
    #         if S['angle'] < -1:     steer = -1
    #         else:    steer = 1

    # R['gear'] = gear
    R['steer'] = steer
    R['accel'] = acce
    R['brake'] = brake

    # Automatic Transmission
    if R['gear'] != -1:
        R['gear']=1
        if S['speedX']>=78:
            R['gear']=2
        if S['speedX']>=104:
            R['gear']=3
        if S['speedX']>=145:
            R['gear']=4
        if S['speedX']>=178:
            R['gear']=5
        if S['speedX']>=220:
            R['gear']=6

    # print S['angle']
    return {'S':(S['track'][8], S['track'][9], S['track'][10], S['angle'], S['trackPos'], S['speedX']), 'R':(speed_estimator, breaking)}

# ==============================================
# ============= MAIN FUCNTION==================
# ==============================================
if __name__ == "__main__":

    #------------- MAKING STORAGE LOCATION FOR DATA
    # data = pd.DataFrame([])
    # cols = ['R', 'S']
    # d_prev = {}

    C = Client()
    for step in xrange(C.maxSteps,0,-1):
        C.get_servers_input()

        #------------- USED FOR CODE PURPOSES
        controller_id = 6

        #------------- USED FROM DATA GENERATION FOR NEURAL NETWORK
        # s = pd.Series(drive_example_4(C))
        # s = pd.Series(drive_example_gen(C, controller_id))
        # s = pd.Series(drive_example_gen_2(C, controller_id))
        
        # ------------ CALLING MAIN CONTROLLER METHOD 'drive_example'
        # drive_next_gen(C)
        drive_example_gen(C, controller_id)
        
        # ------------ MAKING NN OBJECT AND CALLING NN VLASSIFICATIO METHOD FOR PREDICTION
        # Neural-Network
        # NueralNetClassifier = three_layer_neuralnetwork()
        # NueralNetClassifier.train()

        #------------- USED FROM DATA GENERATION FOR NEURAL NETWORK
        # data = data.append(pd.DataFrame([s], index=[data.shape[0]]))

        #------------- CLOSING SERVER CONNECTION
        if C.conn_ok() == False:
            break
        C.respond_to_server()
    C.shutdown()

    #------------- STORING DATA TO CSV/TXT FILES, FRO USE BY NEURAL NETWORK
    # data.to_csv('Data2\TrackRandom - 1.txt', sep='\t', index=False, header=False)
