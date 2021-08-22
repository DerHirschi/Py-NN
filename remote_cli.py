
class CLIDefault(object):
    def __init__(self, Station):
        self.station = Station
        Station.prompt = '\r' + Station.prompt
        Station.ctext = Station.ctext + Station.prompt
        Station.qtext = Station.qtext.format(Station.call_str)
        self.cmd_inp = []
        self.stat = ''  # DISC,  ...
        self.scr = []   # Script mode ( Func, Step )
        self.scr_run = False   # Script mode / Don't wait for input
        self.cmd_dic.update(self.cmd_dic_extra)

    cli_msg_tag = '<{}>'
    cli_sufix = '//'
    cmd_dic_extra = {}

    def get_tx_packet_item(self):
        return {
            'call': self.station.call,
            'dest': self.station.dest,
            'via': self.station.via,
            'out': '',
            'typ': [],  # ['SABM', True, 0],  # Type, P/F, N(R), N(S)
            'cmd': False,
            'pid': 6,
        }

    def main(self):
        if not self.stat:
            # if not self.scr:
            if self.station.rx_data:
                print(str(self.station.rx_data[0][0]))
                tmp = self.station.rx_data[0][0].decode('UTF-8', errors='ignore')
                if '\r' in tmp:
                    self.cmd_inp = tmp.split('\r')[:-1]
                else:
                    self.cmd_inp = [tmp]
                self.station.rx_data = self.station.rx_data[1:]
                # self.station.tx_data += self.station.prompt
            if self.cmd_inp:
                tmp = self.cmd_inp
                for el in tmp:
                    if not self.scr:
                        if self.cli_sufix:
                            if self.cli_sufix == el[:len(self.cli_sufix)]:
                                el = el[len(self.cli_sufix):]
                                self.exec_cmd(el)
                                print('## CLI CMD IN > ' + el)
                        else:
                            self.exec_cmd(el)
                            print('## CLI CMD IN > ' + el)
                    else:
                        ######################################
                        # Script mode ( Execute self.scr[0] )
                        print('## CLI SCR Mode > ' + str(self.scr))
                        self.scr[0]()
                    self.cmd_inp = self.cmd_inp[1:]
            elif self.scr and self.scr_run:
                print('## CLI SCR Mode runs !!> ' + str(self.scr))
                self.scr[0]()

        # Wait until all Data are sendet
        elif self.stat == 'DISC' and all(not el for el in [self.station.tx_data,
                                                           self.station.tx,
                                                           self.station.tx_ctl,
                                                           self.station.noAck]):
            self.disc_cmd()

    def exec_cmd(self, cmd_in=''):
        if cmd_in:
            if cmd_in[0].upper() in self.cmd_dic.keys():
                self.cmd_dic[cmd_in[0].upper()][0](self)
            elif cmd_in[:2].upper() in self.cmd_dic.keys():
                self.cmd_dic[cmd_in[:2].upper()][0](self)
            else:
                self.tx_cli_msg(' Command not found ! ')
        else:
            self.station.tx_data += self.station.prompt

    ############################################
    # Default CMDs
    def tx_cli_msg(self, msg):
        self.station.tx_data += '\r' + self.cli_msg_tag.format(msg)
        self.station.tx_data += self.station.prompt

    def list_cmd_help(self):
        out = 'Available Commands:'
        for el in self.cmd_dic.keys():
            out += ' {},'.format(el)
        self.tx_cli_msg(out)

    def short_help(self):
        out = '\r<Short Help:>\r'
        for el in list(self.cmd_dic.keys()):
            if len(el) < 2:
                fl = '{:2}'.format(el)[::-1]
            else:
                fl = el
            out += '{} < {}\r'.format(fl, self.cmd_dic[el][1])
        self.station.tx_data += out
        self.station.tx_data += self.station.prompt

    def quit_cmd(self):
        print('######## CLI Disc Q/B')
        self.stat = 'DISC'
        self.station.tx_data += self.station.qtext

    def disc_cmd(self):
        print('######## CLI Disc CMD')
        if self.station.stat == 'RR':
            self.station.ack = [False, False, False]
            self.station.rej = [False, False]
            self.station.stat = 'DISC'
            self.station.n2 = 1
            self.station.t1 = 0
            pac = self.get_tx_packet_item()
            pac['typ'] = ['DISC', True]
            pac['cmd'] = True
            self.station.tx = [pac]

    ############################################
    # Default CMD Dict
    cmd_dic = {
        'Q': (quit_cmd, 'Quit/Bye'),
        'B': (quit_cmd, 'Bye/Quit'),
        'D': (disc_cmd, 'Disconnect from Station'),
        '?': (list_cmd_help, 'List available Commands'),
        'H': (short_help, 'Show this ..'),
    }


#################################################
# Test CLI
class CLITest(CLIDefault):
    cli_msg_tag = '<{}>'
    cli_sufix = ''

    ###################################################
    # Send N Packets with N len
    def testfnc(self):
        if not self.scr:
            self.station.tx_data += '\r< Test Packet Sender >'
            self.station.tx_data += '\r< How many Test-Packets should be sent? Enter Digit Number. (Max 40) >'
            self.tx_cli_msg(' Enter A to abort. ')
            # Init Fnc Count
            self.scr_run = False
            self.scr = [self.testfnc, 0]
        elif self.scr[1] == 1:
            n = self.cmd_inp[0]
            if n.isdigit():
                self.station.tx_data += '\r< How big should the packages be? Enter Digit Number. (Max 250) >'
                self.tx_cli_msg(' Enter A to abort. ')
                n = max(min(int(n), 40), 1)
                self.scr.append(n)
            elif n.upper() == 'A':
                self.tx_cli_msg(' Canceled !! ')
                self.scr = []
            else:
                self.station.tx_data += '\r< Please enter Digit Number from 1 to 40 or A for Abort >'
                self.tx_cli_msg(' How many Test-Packets should be sent? Enter Digit Number. (Max 40) ')
                self.scr = [self.testfnc, 0]
        elif self.scr[1] == 2:
            n2 = self.cmd_inp[0]
            if n2.isdigit():
                n = self.scr[2]
                n2 = max(min(int(n2), 250), 1)
                self.scr = [self.testfnc, 3, int(self.station.ax25PacLen)]
                self.station.ax25PacLen = n2
                out = ''
                for c in range(n):
                    for i in range(n2):
                        out += str(c % 10)

                self.station.tx_data += out
                self.scr_run = True
            elif n2.upper() == 'A':
                self.tx_cli_msg(' Canceled !! ')
                self.scr = []
            else:
                self.station.tx_data += '\r< Please enter Digit Number from 1 to 250 or A for Abort >'
                self.tx_cli_msg(' How big should the packages be? ')
                self.scr = [self.testfnc, 1, self.scr[2]]
        # Wait for sending all Data
        elif self.scr[1] >= 3:
            print('### CLI Test Script 3 > ' + str(int(self.scr[1])))
            if not self.station.tx and not self.station.tx_data:
                self.station.ax25PacLen = int(self.scr[2])
                self.station.tx_data += '\r'
                self.tx_cli_msg(' Finished !! ')
                self.scr = []
                self.scr_run = False
            elif self.cmd_inp:
                self.station.ax25PacLen = int(self.scr[2])
                self.station.tx_data += '\r'
                self.tx_cli_msg(' Canceled !! ')
                self.scr = []
                self.scr_run = False

        # Func Count
        if self.scr:
            if int(self.scr[1]) < 3:
                self.scr[1] += 1

    ###################################################
    # Send N Packets . PacLen n + 1
    def testfnc2(self):
        if not self.scr:
            self.station.tx_data += '\r< Test Packet Sender 2 >'
            self.station.tx_data += '\r< How many Test-Packets should be sent? Enter Digit Number. (Max 60) >'
            self.tx_cli_msg(' Enter A to abort. ')
            # Init Fnc Count
            self.scr_run = False
            self.scr = [self.testfnc2, 0]
        elif self.scr[1] == 1:
            n = self.cmd_inp[0]
            if n.isdigit():
                self.station.tx_data += '\r< Start length of Packet ? Enter Digit Number. (Max 190) >'
                self.tx_cli_msg(' Enter A to abort. ')
                n = max(min(int(n), 60), 1)
                self.scr.append(n)
            elif n.upper() == 'A':
                self.tx_cli_msg(' Canceled !! ')
                self.scr = []
            else:
                self.station.tx_data += '\r< Please enter Digit Number from 1 to 60 or A for Abort >'
                self.tx_cli_msg(' How many Test-Packets should be sent? Enter Digit Number. (Max 60) ')
                self.scr = [self.testfnc2, 0]
        elif self.scr[1] == 2:
            n2 = self.cmd_inp[0]
            if n2.isdigit():
                n = int(self.scr[2])
                n2 = max(min(int(n2), 190), 1)
                self.scr = [self.testfnc2, 3, int(self.station.ax25PacLen), 0, n2 + 1, n]
                self.station.ax25PacLen = n2
                out = ''
                for c in range(n2):
                    out += '#'
                out += '\r'
                self.station.tx_data += out
                self.scr_run = True
            elif n2.upper() == 'A':
                self.tx_cli_msg(' Canceled !! ')
                self.scr = []
            else:
                self.station.tx_data += '\r< Please enter Digit Number from 1 to 190 or A for Abort >'
                self.tx_cli_msg(' Start length of Packet ? ')
                self.scr = [self.testfnc2, 1, self.scr[2]]
        # Wait for sending all Data
        elif self.scr[1] >= 3:
            print('### CLI Test Script 3 > ' + str(int(self.scr[1])))
            if not self.station.tx and not self.station.tx_data:
                if self.scr[3] < self.scr[5]:
                    self.station.ax25PacLen = int(self.scr[4])
                    out = ''
                    for c in range(self.station.ax25PacLen):
                        out += '#'
                    out += '\r'
                    self.station.tx_data += out
                    self.scr = [self.testfnc2, 3, int(self.scr[2]), int(self.scr[3]) + 1, int(self.scr[4]) + 1, int(self.scr[5])]

                else:
                    self.station.ax25PacLen = int(self.scr[2])
                    self.station.tx_data += '\r'
                    self.tx_cli_msg(' Finished !! ')
                    self.scr = []
                    self.scr_run = False
            elif self.cmd_inp:
                self.station.ax25PacLen = int(self.scr[2])
                self.station.tx_data += '\r'
                self.tx_cli_msg(' Canceled !! ')
                self.scr = []
                self.scr_run = False

        # Func Count
        if self.scr:
            if int(self.scr[1]) < 3:
                self.scr[1] += 1

    cmd_dic_extra = {
        'T1': (testfnc, 'Test Packet sender 1'),
        'T2': (testfnc2, 'Test Packet sender 2')
    }


####################################################################
class CLINode(CLIDefault):
    pass


####################################################################
# INIT
def init_cli(conn_obj):
    conn_obj.cli = {
        1: CLINode,
        9: CLITest,
    }[conn_obj.cli_type](conn_obj)
####################################################################
