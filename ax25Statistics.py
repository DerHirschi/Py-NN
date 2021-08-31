from ax25enc import get_call_str
import time


class MH(object):
    def __init__(self):
        self.raw = {}
        self.calls = {}
        """
        self.connections = {
            # conn_id: bla TODO Reverse id 
        }
        """

    def mh_inp(self, rx_in, port_id):
        """
        #########################
        # Connections
        if rx_in[0] not in self.connections:
            self.connections[rx_in[0]] = [rx_in[1]]
        else:
            self.connections[rx_in[0]].append(rx_in[1])
        """
        ########################
        # Call Stat
        call_str = get_call_str(rx_in[1]['FROM'][0], rx_in[1]['FROM'][1])
        if call_str not in self.raw.keys():
            self.raw[call_str] = [(rx_in[1], rx_in[2])]
        else:
            self.raw[call_str].append((rx_in[1], rx_in[2]))

        if call_str not in self.calls.keys():
            self.calls[call_str] = {
                'from': call_str,
                'to': [get_call_str(rx_in[1]['TO'][0], rx_in[1]['TO'][1])],
                'port': port_id,
                'first_seen': (time.time(), time.localtime()),
                'last_seen': (time.time(), time.localtime()),
                'pac_n': 1,         # N Packets
                'byte_n': rx_in[2],  # N Bytes
                'h_byte_n': 0,  # N Header Bytes
                'rej_n': 0,  # N Header Bytes
            }
            if rx_in[1]['data'][1]:
                self.calls[call_str]['h_byte_n'] = rx_in[1]['data'][1]
            if rx_in[1]['ctl']['flag'] == 'REJ':
                self.calls[call_str]['rej_n'] = 1
        else:
            self.calls[call_str]['pac_n'] += 1
            self.calls[call_str]['port'] = port_id
            self.calls[call_str]['byte_n'] += rx_in[2]
            self.calls[call_str]['last_seen'] = (time.time(), time.localtime())
            to_c_str = get_call_str(rx_in[1]['TO'][0], rx_in[1]['TO'][1])
            if to_c_str not in self.calls[call_str]['to']:
                self.calls[call_str]['to'].append(to_c_str)
            if rx_in[1]['data'][1]:
                self.calls[call_str]['h_byte_n'] += rx_in[1]['data'][1]
            if rx_in[1]['ctl']['flag'] == 'REJ':
                self.calls[call_str]['rej_n'] += 1

    def mh_out_cli(self):

        out = ''
        out += '\r                       < MH - List >\r\r'
        c = 0
        tp = 0
        tb = 0
        rj = 0
        for call in list(self.calls.keys()):
            out += 'P:{:2}>{:5} S {:9} {:3}'.format(self.calls[call]['port'],
                                                round(time.time() - self.calls[call]['last_seen'][0]),
                                                call,
                                                '')
            tp += self.calls[call]['pac_n']
            tb += self.calls[call]['byte_n']
            rj += self.calls[call]['rej_n']
            c += 1
            if c == 3:
                c = 0
                out += '\r'
        out += '\r'
        out += '\rTotal Packets Rec.: ' + str(tp)
        out += '\rTotal REJ-Packets Rec.: ' + str(rj)
        out += '\rTotal Bytes Rec.: ' + str(tb)
        out += '\r'

        return out
