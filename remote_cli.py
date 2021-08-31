import config


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
            file = open('test.gz', 'rb')
            f_out = file.read()
            file.close()
            self.station.tx_data += '\r#BIN#' + str(len(f_out)) + '\r'

            # Init Fnc Count
            self.scr_run = False
            self.scr = [self.ft_dn, 0]
        elif self.scr[1] == 0:
            inp = self.cmd_inp[0]
            print(inp)
            if inp == '#OK#':
                # if not self.station.noAck and not self.station.tx_data:
                file = open('test.gz', 'rb')
                f_out = file.read()
                file.close()
                self.station.tx_bin += f_out
                self.scr_run = True
                self.scr = [self.ft_dn, 1]
        elif self.scr[1] == 1:
            if not self.station.noAck and not self.station.tx_bin:
                self.station.tx_data += '#OK#\r'
                self.tx_cli_msg(' Done ! ')
                self.scr_run = False
                self.scr = []

    def ft_dt(self):
        f_out = b'123456789'

        if not self.scr:
            self.station.tx_data += '\r#BIN#' + str(len(f_out)) + '\r'
            # Init Fnc Count
            self.scr_run = False
            self.scr = [self.ft_dt, 0]
        elif self.scr[1] == 0:
            inp = self.cmd_inp[0]
            print(inp)
            if inp == '#OK#':
                # if not self.station.noAck and not self.station.tx_data:
                self.station.tx_bin += f_out
                self.scr_run = True
                self.scr = [self.ft_dt, 1]
        elif self.scr[1] == 1:
            if not self.station.noAck and not self.station.tx_bin:
                self.station.tx_data += '#OK#\r'
                self.tx_cli_msg(' Done ! ')
                self.scr_run = False
                self.scr = []

    CLIDefault.cmd_dic.update({

        'UP': (ft_up, '(Up)load Test File'),
        'DO': (ft_dn, '(Do)wnload Test File'),
        'DT': (ft_dt, '(D)wnload (T)est Data (b"123456789")'),
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
            self.station.tx_data += '\r< How many Test-Packets should be sent? Enter Digit Number. (Max 500) >'
            self.tx_cli_msg(' Enter A to abort. ')
            # Init Fnc Count
            self.scr_run = False
            self.scr = [self.testfnc, 0]
        elif self.scr[1] == 1:
            n = self.cmd_inp[0]
            if n.isdigit():
                self.station.tx_data += '\r< How big should the packages be? Enter Digit Number. (Max 250) >'
                self.tx_cli_msg(' Enter A to abort. ')
                n = max(min(int(n), 500), 1)
                self.scr.append(n)
            elif n.upper() == 'A':
                self.tx_cli_msg(' Canceled !! ')
                self.scr = []
            else:
                self.station.tx_data += '\r< Please enter Digit Number from 1 to 500 or A for Abort >'
                self.tx_cli_msg(' How many Test-Packets should be sent? Enter Digit Number. (Max 500) ')
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

    def port(self):
        out = "\r-#-Name/Call----Speed/M-Max-TXD-PAC-PERS-SLOT-IRTT---T2----T3--RET-DA-C-S-M--CLI\r"
        for ke in config.conf_ax_ports.keys():
            out += '{:2} {:12} ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\r'.format(ke,
                                                                            config.conf_ax_ports[ke]['name'])
            for stat in config.ax_ports[ke].ax_Stations.keys():
                # print(str(config.ax_ports[ke].ax_Stations))
                print(''.join("%s: %s\r" % item for item in vars(config.ax_ports[ke].ax_Stations[stat]).items()))
                # out +='{:2} {:12} {:11}   {}  {:3} {:3}         {:4}\r'.format(
                out +='{:2} {:12} {:7}   {} {:3} {:3}           {:4}  {:3}  {:4}   {:2}            {:2}\r'.format(
                                            config.ax_ports[ke].ax_Stations[stat].port_conf_id,
                                            stat,
                                            config.ax_ports[ke].ser_baud,
                                            config.ax_ports[ke].ax_Stations[stat].ax25MaxFrame,
                                            config.ax_ports[ke].ax_Stations[stat].ax25TXD,
                                            config.ax_ports[ke].ax_Stations[stat].ax25PacLen,
                                            round(config.ax_ports[ke].ax_Stations[stat].parm_IRTT),
                                            round(config.ax_ports[ke].ax_Stations[stat].parm_T2),
                                            round(config.ax_ports[ke].ax_Stations[stat].ax25T3 / 100),
                                            config.ax_ports[ke].ax_Stations[stat].ax25N2,
                                            config.ax_ports[ke].ax_Stations[stat].cli_type)

        self.station.tx_data += '\r' + out
        self.station.tx_data += self.station.promptvar

    def ax_clients(self):
        out = 'Call-------IP----------------------Mode----Port---Timeout--IP/Hostname----\r'
        for ke in config.ax_ports.keys():
            if config.ax_ports[ke].port_typ == 'AXIP':
                for conn_id in config.ax_ports[ke].ax_conn.keys():
                    bcast_mode = config.conf_ax_ports[config.ax_ports[ke].ax_conn[conn_id].port_conf_id]['bcast']
                    if bcast_mode:
                        bcast_mode = 'BRCAST'
                    else:
                        bcast_mode = ''
                    out += '{}  {:15}:{}    {:6} {:5}   {}         {:15}\r'.format(
                        config.ax_ports[ke].ax_conn[conn_id].call_str,
                        config.conf_ax_ports[config.ax_ports[ke].ax_conn[conn_id].port_conf_id]['parm1'],
                        config.conf_ax_ports[config.ax_ports[ke].ax_conn[conn_id].port_conf_id]['parm2'],
                        bcast_mode,
                        config.ax_ports[ke].ax_conn[conn_id].axip_client[1],
                        '',
                        config.ax_ports[ke].ax_conn[conn_id].axip_client[0]
                    )
        self.station.tx_data += '\r' + out
        self.station.tx_data += self.station.promptvar

    CLIDefault.cmd_dic.update({
        'C': (connect, '(C)onnect to other Station ( Not implemented yet )'),
        'P': (port, 'Show (P)orts'),
        'AX': (ax_clients, 'Show (AX)IP Clients'),
    })


####################################################################
# INIT
def init_cli(conn_obj):
    conn_obj.cli = {
        1: CLINode,
        9: CLITest,
    }[conn_obj.cli_type](conn_obj)
####################################################################
