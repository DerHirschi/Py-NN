
class CLIDefault(object):
    def __init__(self, Station):
        self.station = Station
        self.cmd_inp = []
        self.stat = ''  # DISC,  HOLD...
        self.scr = []   # Script mode ( Func, Step )
        self.scr_run = False   # Script mode / Don't wait for input
        Station.qtext = Station.qtext.format(Station.call_str)
    cli_msg_tag = '<{}>'
    cli_sufix = '//'

    def main(self):
        if self.stat != 'HOLD':
            if not self.stat:
                # if not self.scr:
                if self.station.rx_data:
                    # print(str(self.station.rx_data[0][0]))
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
                    self.scr[0]()

            # Wait until all Data are sendet
            elif self.stat == 'DISC' and all(not el for el in [self.station.tx_data,
                                                               self.station.tx,
                                                               self.station.tx_ctl,
                                                               self.station.noAck]):
                self.disc_cmd()

    def exec_cmd(self, cmd_in=''):
        if cmd_in:
            if cmd_in[:2].upper() in self.cmd_dic.keys():
                self.cmd_dic[cmd_in[:2].upper()][0](self)
            elif cmd_in[0].upper() in self.cmd_dic.keys():
                self.cmd_dic[cmd_in[0].upper()][0](self)
            else:
                self.tx_cli_msg(' Command not found ! ')
        else:
            self.station.tx_data += self.station.promptvar

    ############################################
    # Default CMDs
    def tx_cli_msg(self, msg):
        self.station.tx_data += '\r' + self.cli_msg_tag.format(msg)
        self.station.tx_data += self.station.promptvar

    def vers(self):
        out = "******************************************************\r" \
              "* Testing Stuff Station. I don't know something with *\r" \
              "*  AX25 de/encoding in Python from MD2SAW (Manuel)   *\r" \
              "******************************************************\r"
        self.station.tx_data += '\r' + out
        self.station.tx_data += self.station.promptvar

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
        self.station.tx_data += self.station.promptvar

    def mh_cmd(self):
        out = self.station.mh.mh_out_cli()
        self.station.tx_data += out
        self.station.tx_data += self.station.promptvar

    def quit_cmd(self):
        print('######## CLI Disc Q/B')
        self.stat = 'DISC'
        self.station.tx_data += self.station.qtext

    def disc_cmd(self):
        print('######## CLI Disc CMD')
        self.station.port.DISC_TX(self.station.conn_id)

    ############################################
    # Default CMD Dict
    cmd_dic = {
        'Q': (quit_cmd, '(Q)uit/Bye'),
        'B': (quit_cmd, '(B)ye/Quit'),
        'D': (disc_cmd, '(D)isconnect from Station'),
        'MH': (mh_cmd, '(MH) LIst'),
        '?': (list_cmd_help, 'List available Commands'),
        'H': (short_help, 'Show this ..'),
        'V': (vers, '(V)ersion - Software Info'),
    }


#################################################
# File Transpoert ( Test )
class CLIFileTransport(CLIDefault):

    def ft_up(self):
        self.tx_cli_msg('!!DUMMY!!Not implemented yet !')

    def ft_dn(self):
        if not self.scr:
            file = open('test.tar.gz', 'rb')
            f_out = file.read()
            file.close()
            self.station.tx_data += '\r#BIN#' + str(len(f_out)) + '##test.tar.gz'

            # Init Fnc Count
            self.scr_run = True
            self.scr = [self.ft_dn, 0]
        elif self.scr[1] == 0:
            if not self.station.noAck and not self.station.tx_data:
                file = open('test.tar.gz', 'rb')
                f_out = file.read()
                file.close()
                self.station.tx_bin += f_out
                self.scr_run = True
                self.scr = [self.ft_dn, 1]
        elif self.scr[1] == 1:
            if not self.station.noAck and not self.station.tx_bin:
                self.station.tx_data += '\r#OK#\r'
                self.tx_cli_msg(' Done ! ')
                self.scr_run = False
                self.scr = []
    CLIDefault.cmd_dic.update({

        'UP': (ft_up, '(Up)load Test File'),
        'DO': (ft_dn, '(Do)wnload Test File'),
    })


#################################################
# Test CLI
class CLITest(CLIFileTransport):
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

    def sh_parm(self):
        out = ''.join("%s: %s\r" % item for item in vars(self.station).items())
        self.station.tx_data += '\r< Connection Parameter >\r\r'
        self.station.tx_data += out
        self.station.tx_data += self.station.promptvar

    def rtt_parm(self):
        def send_parm():
            # out = 'parm_T2> {}\r'.format(self.station.parm_T2)
            # out += 'parm_IRTT> {}\r'.format(self.station.parm_IRTT)
            out = 'parm_RTT> {}\r'.format(self.station.parm_RTT)
            # out += 'deb_calc_t1> {}\r'.format(self.station.deb_calc_t1)
            self.station.tx_data += '\r< RTT Parameter >\r\r'
            self.station.tx_data += out
            # self.station.tx_data += self.station.promptvar
        if not self.scr:
            send_parm()
            self.tx_cli_msg(' Press Enter for next... ')
            self.scr_run = False
            self.scr = [self.rtt_parm, 0]
        elif self.scr[1] < 3:
            send_parm()
            self.tx_cli_msg(' Press Enter for next... ')
            self.scr[1] += 1
        else:
            send_parm()
            self.tx_cli_msg(' Done !! ')
            self.scr = []
            self.scr_run = False

    CLIDefault.cmd_dic.update({
        'T1': (testfnc, 'Test Packet sender 1'),
        'T2': (testfnc2, 'Test Packet sender 2'),
        'PA': (sh_parm, 'Show all (Pa)rameters'),
        'RT': (rtt_parm, 'Show (RT)T Parameters'),
    })


####################################################################
# class CLINode(CLIDefault):
class CLINode(CLITest):
    def connect(self):
        self.station.tx_data += str(self.station.port)
        self.station.tx_data += self.station.promptvar
        # self.station.port.DISC_TX(self.station.conn_id)

    CLIDefault.cmd_dic.update({
        'C': (connect, '(C)onnect to other Station ( Not implemented yet )'),
    })


####################################################################
# INIT
def init_cli(conn_obj):
    conn_obj.cli = {
        1: CLINode,
        9: CLITest,
    }[conn_obj.cli_type](conn_obj)
####################################################################
