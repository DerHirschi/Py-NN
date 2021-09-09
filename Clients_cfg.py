import time
import os
import pickle

axip_clientList = 'data/axip_clientList.pkl'


class Client(object):
    def __init__(self):
        self.call_str = ''
        self.name = ''
        self.qth = ''
        self.loc = ''
        self.axip_add = ()
        self.last_axip_add = ()

        ########
        # self.filter
        # self.mode
        # self.aprs_mode
        # self.language


class AXIPClients(object):
    def __init__(self, port):
        self.port = port
        self.clients = {
            # 'call_str': {
            #       'addr': (),
            #       'lastsee': 0.0,
            # }
        }
        try:
            with open(axip_clientList, 'rb') as inp:
                self.clients = pickle.load(inp)
        except FileNotFoundError:
            os.system('touch {}'.format(axip_clientList))
        except EOFError:
            pass

    def cli_cmd_out(self):
        out = ''
        out += '\r                       < AXIP - Clients >\r\r'
        out += '-Call-----IP:Port---------------Timeout------------------\r'
        for ke in self.clients.keys():
            out += '{:9} {:21} {:8}\r'.format(
                ke,
                self.clients[ke]['addr'][0] + ':' + str(self.clients[ke]['addr'][1]),
                round(time.time() - self.clients[ke]['lastsee'])
            )
        out += '\r'
        return out

    def save_data(self):
        try:
            with open(axip_clientList, 'wb') as outp:
                pickle.dump(self.clients, outp, pickle.HIGHEST_PROTOCOL)
        except FileNotFoundError:
            os.system('touch {}'.format(axip_clientList))
            with open(axip_clientList, 'wb') as outp:
                pickle.dump(self.clients, outp, pickle.HIGHEST_PROTOCOL)