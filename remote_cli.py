import config
import ax25enc as ax
import monitor


class CLIDefault(object):
    def __init__(self, Connction):
        self.conncetion = Connction
        self.cmd_inp = []
        self.stat = ''  # DISC,  HOLD...
        self.scr = []  # Script mode ( Func, Step )
        self.scr_run = False  # Script mode / Don't wait for input
        # self.cmd_dic = dict(self.cmd_dic_default)
        Connction.qtext = Connction.qtext.format(Connction.call_str)
        self.cli_msg_tag = Connction.cli_msg_tag
        self.cli_sufix = Connction.cli_sufix
        self.cmd_dic_default = {}
        self.cmd_dic = {}

    def main(self):
        if self.stat != 'HOLD':
            if not self.stat:
                # if not self.scr:
                ###################################################
                if self.conncetion.rx_data:
                    tmp = self.conncetion.rx_data[0][0].decode('UTF-8', errors='ignore')
                    if '\r' in tmp:
                        self.cmd_inp = tmp.split('\r')[:-1]
                    else:
                        self.cmd_inp = [tmp]
                    self.conncetion.rx_data = self.conncetion.rx_data[1:]
                    # self.station.tx_data += self.station.prompt
                ###################################################
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
                                    print('## CLI CMD IN no SUFIX> ' + el)
                                    # self.tx_cli_msg('Command not found !')
                            else:
                                self.exec_cmd(el)
                                print('## CLI CMD IN > ' + el)
                        else:
                            ######################################
                            # Script mode ( Execute self.scr[0] )
                            # with input data
                            print('## CLI SCR Mode > ' + str(self.scr))
                            self.scr[0]()
                        self.cmd_inp = self.cmd_inp[1:]
                #####################################
                # Jump to Script Mode w/o input data
                elif self.scr and self.scr_run:
                    self.scr[0]()
            elif self.stat == 'NODE':
                self.node_relay_data()
            # Wait until all Data are sendet
            elif self.stat == 'DISC' and all(not el for el in [self.conncetion.tx_data,
                                                               self.conncetion.tx,
                                                               self.conncetion.tx_ctl,
                                                               self.conncetion.noAck]):
                self.disc_cmd()

    def exec_cmd(self, cmd_in=''):
        # print('CMD IN > ' + str(cmd_in))
        # print('CMD DICT > ' + str(self.cmd_dic))
        if cmd_in:
            if cmd_in[:2].upper() in self.cmd_dic.keys():
                self.cmd_dic[cmd_in[:2].upper()][0](self)
            elif cmd_in[0].upper() in self.cmd_dic.keys():
                self.cmd_dic[cmd_in[0].upper()][0](self)
            else:
                self.tx_cli_msg(' Command not found ! ')
        else:
            self.conncetion.tx_data += self.conncetion.promptvar

    ############################################
    # Default CMDs
    def tx_cli_msg(self, msg):
        self.conncetion.tx_data += '\r' + self.cli_msg_tag.format(msg)
        self.conncetion.tx_data += self.conncetion.promptvar

    def vers(self):
        """
        out = "******************************************************\r" \
              "* Testing Stuff Station. I don't know something with *\r" \
              "*  AX25 de/encoding in Python from MD2SAW (Manuel)   *\r" \
              "******************************************************\r"
        """
        """
        out = "*****************************************\r" \
              "*  ____        _   _  ___  ____  _____  *\r" \
              "* |  _ \ _   _| \ | |/ _ \|  _ \| ____| *\r" \
              "* | |_) | | | |  \| | | | | | | |  _|   *\r" \
              "* |  __/| |_| | |\  | |_| | |_| | |___  *\r" \
              "* |_|    \__, |_| \_|\___/|____/|_____| *\r" \
              "*        |___/                          *\r" \
              "* Under development by MD2SAW (Manuel)  *\r" \
              "* Will be published on GitHub..         *\r" \
              "*****************************************\r"
        """
        out = "***************************************\r" \
              "*  ____                  _   _ _   _  *\r" \
              "* |  _ \ _   _          | \ | | \ | | *\r" \
              "* | |_) | | | |  _____  |  \| |  \| | *\r" \
              "* |  __/| |_| | |_____| | |\  | |\  | *\r" \
              "* |_|    \__, |         |_| \_|_| \_| *\r" \
              "*        |___/                        *\r" \
              "***************************************\r" \
              "*        < Python - Net Node >        *\r" \
              "* Under development by MD2SAW (Manuel)*\r" \
              "* Will be published on GitHub..       *\r" \
              "***************************************\r"
        self.conncetion.tx_data += '\r' + out
        self.conncetion.tx_data += self.conncetion.promptvar

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
        self.conncetion.tx_data += out
        self.conncetion.tx_data += self.conncetion.promptvar

    def mh_cmd(self):
        out = self.conncetion.mh.mh_out_cli()
        self.conncetion.tx_data += out
        self.conncetion.tx_data += self.conncetion.promptvar

    def quit_cmd(self):
        print('######## CLI Disc Q/B')
        self.stat = 'DISC'
        self.conncetion.tx_data += self.conncetion.qtext

    def disc_cmd(self):
        print('######## CLI Disc CMD')
        self.conncetion.port.DISC_TX(self.conncetion.conn_id)


#################################################
# File Transport ( Test )
# class CLIFileTransport(CLIDefault):
    def ft_up(self):
        self.tx_cli_msg('!!DUMMY!!Not implemented yet !')

    def ft_dn(self):
        if not self.scr:
            file = open('test.gz', 'rb')
            f_out = file.read()
            file.close()
            self.conncetion.tx_data += '\r#BIN#' + str(len(f_out)) + '\r'

            # Init Fnc Count
            self.scr_run = False
            self.scr = [self.ft_dn, 0]
        elif self.scr[1] == 0:
            inp = self.cmd_inp[0]
            # print(inp)
            if inp == '#OK#':
                # if not self.station.noAck and not self.station.tx_data:
                file = open('test.gz', 'rb')
                f_out = file.read()
                file.close()
                self.conncetion.tx_bin += f_out
                self.scr_run = True
                self.scr = [self.ft_dn, 1]
        elif self.scr[1] == 1:
            if not self.conncetion.noAck and not self.conncetion.tx_bin:
                self.conncetion.tx_data += '#OK#\r'
                self.tx_cli_msg(' Done ! ')
                self.scr_run = False
                self.scr = []

    def ft_dt(self):
        f_out = b'123456789'

        if not self.scr:
            self.conncetion.tx_data += '\r#BIN#' + str(len(f_out)) + '\r'
            # Init Fnc Count
            self.scr_run = False
            self.scr = [self.ft_dt, 0]
        elif self.scr[1] == 0:
            inp = self.cmd_inp[0]
            # print(inp)
            if inp == '#OK#':
                # if not self.station.noAck and not self.station.tx_data:
                self.conncetion.tx_bin += f_out
                self.scr_run = True
                self.scr = [self.ft_dt, 1]
        elif self.scr[1] == 1:
            if not self.conncetion.noAck and not self.conncetion.tx_bin:
                self.conncetion.tx_data += '#OK#\r'
                self.tx_cli_msg(' Done ! ')
                self.scr_run = False
                self.scr = []

    """

    CLIDefault.cmd_dic = dict(CLIDefault.cmd_dic_default)
    CLIDefault.cmd_dic.update({

        'UP': (ft_up, '(Up)load Test File'),
        'DO': (ft_dn, '(Do)wnload Test File'),
        'DT': (ft_dt, '(D)wnload (T)est Data (b"123456789")'),
    })
    """

    #################################################
    # Test CLI
    # class CLITest(CLIDefault):
    # cli_msg_tag = '<{}>'  ## Config in Station Class (DefaultParam)
    # cli_sufix = ''        ## Config in Station Class (DefaultParam)

    ###################################################
    # Send N Packets with N len
    def testfnc(self):
        if not self.scr:
            self.conncetion.tx_data += '\r< Test Packet Sender >'
            self.conncetion.tx_data += '\r< How many Test-Packets should be sent? Enter Digit Number. (Max 50) >'
            self.tx_cli_msg(' Enter A to abort. ')
            # Init Fnc Count
            self.scr_run = False
            self.scr = [self.testfnc, 0]
        elif self.scr[1] == 1:
            n = self.cmd_inp[0]
            if n.isdigit():
                self.conncetion.tx_data += '\r< How big should the packages be? Enter Digit Number. (Max 250) >'
                self.tx_cli_msg(' Enter A to abort. ')
                n = max(min(int(n), 50), 1)
                self.scr.append(n)
            elif n.upper() == 'A':
                self.tx_cli_msg(' Canceled !! ')
                self.scr = []
            else:
                self.conncetion.tx_data += '\r< Please enter Digit Number from 1 to 50 or A for Abort >'
                self.tx_cli_msg(' How many Test-Packets should be sent? Enter Digit Number. (Max 50) ')
                self.scr = [self.testfnc, 0]
        elif self.scr[1] == 2:
            n2 = self.cmd_inp[0]
            if n2.isdigit():
                n = self.scr[2]
                n2 = max(min(int(n2), 250), 1)
                self.scr = [self.testfnc, 3, int(self.conncetion.ax25PacLen)]
                self.conncetion.ax25PacLen = n2
                out = ''
                for c in range(n):
                    for i in range(n2):
                        out += str(c % 10)

                self.conncetion.tx_data += out
                self.scr_run = True
            elif n2.upper() == 'A':
                self.tx_cli_msg(' Canceled !! ')
                self.scr = []
            else:
                self.conncetion.tx_data += '\r< Please enter Digit Number from 1 to 250 or A for Abort >'
                self.tx_cli_msg(' How big should the packages be? ')
                self.scr = [self.testfnc, 1, self.scr[2]]
        # Wait for sending all Data
        elif self.scr[1] >= 3:
            if not self.conncetion.tx and not self.conncetion.tx_data:
                self.conncetion.ax25PacLen = int(self.scr[2])
                self.conncetion.tx_data += '\r'
                self.tx_cli_msg(' Done !! ')
                self.scr = []
                self.scr_run = False
            elif self.cmd_inp:
                self.conncetion.ax25PacLen = int(self.scr[2])
                self.conncetion.tx_data += '\r'
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
            self.conncetion.tx_data += '\r< Test Packet Sender 2 >'
            self.conncetion.tx_data += '\r< How many Test-Packets should be sent? Enter Digit Number. (Max 60) >'
            self.tx_cli_msg(' Enter A to abort. ')
            # Init Fnc Count
            self.scr_run = False
            self.scr = [self.testfnc2, 0]
        elif self.scr[1] == 1:
            n = self.cmd_inp[0]
            if n.isdigit():
                self.conncetion.tx_data += '\r< Start length of Packet ? Enter Digit Number. (Max 190) >'
                self.tx_cli_msg(' Enter A to abort. ')
                n = max(min(int(n), 60), 1)
                self.scr.append(n)
            elif n.upper() == 'A':
                self.tx_cli_msg(' Canceled !! ')
                self.scr = []
            else:
                self.conncetion.tx_data += '\r< Please enter Digit Number from 1 to 60 or A for Abort >'
                self.tx_cli_msg(' How many Test-Packets should be sent? Enter Digit Number. (Max 60) ')
                self.scr = [self.testfnc2, 0]
        elif self.scr[1] == 2:
            n2 = self.cmd_inp[0]
            if n2.isdigit():
                n = int(self.scr[2])
                n2 = max(min(int(n2), 190), 1)
                self.scr = [self.testfnc2, 3, int(self.conncetion.ax25PacLen), 0, n2 + 1, n]
                self.conncetion.ax25PacLen = n2
                out = ''
                for c in range(n2):
                    out += '#'
                out += '\r'
                self.conncetion.tx_data += out
                self.scr_run = True
            elif n2.upper() == 'A':
                self.tx_cli_msg(' Canceled !! ')
                self.scr = []
            else:
                self.conncetion.tx_data += '\r< Please enter Digit Number from 1 to 190 or A for Abort >'
                self.tx_cli_msg(' Start length of Packet ? ')
                self.scr = [self.testfnc2, 1, self.scr[2]]
        # Wait for sending all Data
        elif self.scr[1] >= 3:
            if not self.conncetion.tx and not self.conncetion.tx_data:
                if self.scr[3] < self.scr[5]:
                    self.conncetion.ax25PacLen = int(self.scr[4])
                    out = ''
                    for c in range(self.conncetion.ax25PacLen):
                        out += '#'
                    out += '\r'
                    self.conncetion.tx_data += out
                    self.scr = [self.testfnc2, 3, int(self.scr[2]), int(self.scr[3]) + 1, int(self.scr[4]) + 1,
                                int(self.scr[5])]

                else:
                    self.conncetion.ax25PacLen = int(self.scr[2])
                    self.conncetion.tx_data += '\r'
                    self.tx_cli_msg(' Done !! ')
                    self.scr = []
                    self.scr_run = False
            elif self.cmd_inp:
                self.conncetion.ax25PacLen = int(self.scr[2])
                self.conncetion.tx_data += '\r'
                self.tx_cli_msg(' Canceled !! ')
                self.scr = []
                self.scr_run = False

        # Func Count
        if self.scr:
            if int(self.scr[1]) < 3:
                self.scr[1] += 1

    def sh_parm(self):
        out = ''.join("%s: %s\r" % item for item in vars(self.conncetion).items())
        self.conncetion.tx_data += '\r< Connection Parameter >\r\r'
        self.conncetion.tx_data += out
        self.conncetion.tx_data += self.conncetion.promptvar

    def rtt_parm(self):
        def send_parm():
            # out = 'parm_T2> {}\r'.format(self.station.parm_T2)
            # out += 'parm_IRTT> {}\r'.format(self.station.parm_IRTT)
            out = 'parm_RTT> {}\r'.format(self.conncetion.parm_RTT)
            # out += 'deb_calc_t1> {}\r'.format(self.station.deb_calc_t1)
            self.conncetion.tx_data += '\r< RTT Parameter >\r\r'
            self.conncetion.tx_data += out
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

    """
    CLIDefault.cmd_dic = dict(CLIDefault.cmd_dic_default)
    CLIDefault.cmd_dic.update({
        'T1': (testfnc, 'Test Packet sender 1'),
        'T2': (testfnc2, 'Test Packet sender 2'),
        'PA': (sh_parm, 'Show all (Pa)rameters'),
        'RT': (rtt_parm, 'Show (RT)T Parameters'),
    })
    """

####################################################################
# class CLINode(CLIDefault):
    def connect(self):
        inp = str(self.cmd_inp[0]).upper()
        inp = inp.split(' ')[1:]
        if not inp:
            self.tx_cli_msg(' Please enter valid Call !! ')
            return
        dest_call = inp[0]
        caller_call = ax.get_call_str(self.conncetion.dest)
        via = []
        conn_via_list = list(self.conncetion.via)
        conn_via_list.reverse()
        port = config.mh.mh_get_last_port_obj(dest_call)
        if port.port_typ == 'AXIP':
            axip_add = config.mh.mh_get_last_port_obj(dest_call)
        else:
            axip_add = None

        for el in conn_via_list:
            via.append(ax.get_call_str(el))
        via.append(self.conncetion.call_str)
        if len(inp) > 1:
            via += inp[1:]
        conn_id = dest_call + ':' + caller_call

        conn_via_list = []
        tr = True
        for el in via:
            conn_id += ':' + el
            tm = ax.get_ssid(el)
            if tr:
                tm.append(True)         # Digi Trigger ( H BIT )
                if el == self.conncetion.call_str:
                    tr = False
            else:
                tm.append(False)        # Digi Trigger ( H BIT )
            conn_via_list.append(tm)

        print(conn_id)
        print(via)
        print(conn_via_list)

        if conn_id not in port.ax_conn.keys():
            port.ax_conn[conn_id] = self.conncetion.port.ax_Stations[self.conncetion.call_str]()
            port.ax_conn[conn_id].call = self.conncetion.dest
            dest = ax.get_ssid(dest_call)
            port.ax_conn[conn_id].dest = [dest[0], dest[1]]
            port.ax_conn[conn_id].via = conn_via_list
            port.ax_conn[conn_id].conn_id = conn_id
            port.ax_conn[conn_id].db_entry = config.db.get_entry(dest_call)
            port.ax_conn[conn_id].port = port
            port.ax_conn[conn_id].axip_client = axip_add

            port.ax_conn[conn_id].stat = 'SABM'
            tx_pack = port.get_tx_packet_item(conn_id=conn_id)
            tx_pack['typ'] = ['SABM', True]
            tx_pack['cmd'] = True
            #################
            # Debugging
            # deb = ''.join("%s: %s\r\n" % item for item in vars(self.conncetion.port.ax_conn[conn_id]).items())
            # print(deb)
            #################

            port.ax_conn[conn_id].tx = [tx_pack]
            # set_t1(conn_id)
            port.ax_conn[conn_id].port.set_t3(conn_id)
            # self.conncetion.port.set_t3(conn_id)
            ###############
            # Add Link
            link = config.NodeLink(port.ax_conn[conn_id], self.conncetion.conn_id)
            own_link = config.NodeLink(self.conncetion, self.conncetion.conn_id)
            # ADD DEST LINK
            self.conncetion.node_links[conn_id] = link
            # ADD OWN LINK TO DEST STATION
            port.ax_conn[conn_id].node_links[self.conncetion.conn_id] = own_link
            #####################
            # Init Node Mode
            self.stat = 'NODE'
            link.link.cli.stat = 'NODE'
            ###############
            # self.conncetion.tx_data += '\r' + str(self.conncetion.port.ax_conn)
            self.conncetion.tx_data += '\r' + self.conncetion.promptvar
            self.conncetion.tx_data += "Link setup... Port ({})".format(port.port_id)
        else:
            self.conncetion.tx_data += '\r' + 'Busy !! There is still a connection to this Station !!!'

        # self.conncetion.tx_data += self.conncetion.promptvar
        # self.station.port.DISC_TX(self.station.conn_id)

    def node_relay_data(self):
        # print(self.conncetion.conn_id)
        if not self.conncetion.node_links.keys():
            self.stat = ''
            ####################################################
            # send "*** Reconnected to CALL" flag
            self.conncetion.tx_data += '\r*** Reconnected to {}\r'.format(
                self.conncetion.call_str
            )
            self.conncetion.tx_data += self.conncetion.promptvar
            return
        #############################################################################
        # Multiple Links Possible (Convers). But should cause Problems at this state
        for k in list(self.conncetion.node_links.keys()):
            link = self.conncetion.node_links[k]
            ################
            # Status check
            if link.stat == 'SABM':
                if link.link.stat == 'RR':
                    link.stat = 'RR'
                    self.conncetion.tx_data += '\r*** Connected to {}\r'.format(
                        ax.get_call_str(link.link.dest)
                    )
                elif link.link.stat == 'SABM' and self.conncetion.rx_data:
                    self.scr = []
                    self.scr_run = False
                    self.stat = ''
                    link.disc_tx()
                    del link

                    self.conncetion.tx_data += self.conncetion.promptvar
            ################
            # Relay Data
            # elif link.stat == 'RR' and link.link.node_links[self.conncetion.conn_id].stat == 'RR':
            elif link.stat == 'RR':
                # RX > TX
                if link.link.rx_data:
                    tmp = list(link.link.rx_data)
                    for el in tmp:
                        # print('NODE> ' + str(el))
                        self.conncetion.tx_bin += el[0]
                        link.link.rx_data.remove(el)
                # TX > RX
                if self.conncetion.rx_data:
                    for el in list(self.conncetion.rx_data):
                        link.link.tx_bin += el[0]
            # elif link.stat == 'DISC' or link.link.node_links[self.conncetion.conn_id].stat == 'DISC':
            elif link.stat == 'DISC':
                print(link.caller_id + ' ' + self.conncetion.conn_id)
                if link.caller_id != self.conncetion.conn_id:
                    self.stat = 'DISC'
                    link.link.cli.stat = 'DISC'
                del self.conncetion.node_links[k]

        self.conncetion.rx_data = []

    def port(self):
        out = "\r-#-Name/Call----Speed/M-Max-TXD-PAC-PERS-SLOT-IRTT---T2----T3--RET-CLI----------\r"
        for ke in config.conf_ax_ports.keys():
            out += '{:2} {:12} ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\r'.format(ke,
                                                                                                          config.conf_ax_ports[
                                                                                                              ke][
                                                                                                              'name'])
            for stat in config.ax_ports[ke].ax_Stations.keys():
                # print(str(config.ax_ports[ke].ax_Stations))
                # print(''.join("%s: %s\r" % item for item in vars(config.ax_ports[ke].ax_Stations[stat]).items()))
                # out +='{:2} {:12} {:11}   {}  {:3} {:3}         {:4}\r'.format(
                out += '{:2} {:12} {:7}   {} {:3} {:3}           {:4}  {:3}  {:4}   {:2} {}\r'.format(
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
                    str(config.ax_ports[ke].ax_Stations[stat].cli_type))

        self.conncetion.tx_data += '\r' + out
        self.conncetion.tx_data += self.conncetion.promptvar

    def ax_clients(self):
        out = '\r                  < AXIP - Connected Clients >\r\r'
        out += 'Call-------Client IP:Port----------Mode----AXPort-Timeout--Server IP:Port-\r'
        for ke in config.ax_ports.keys():
            if config.ax_ports[ke].port_typ == 'AXIP':
                for conn_id in config.ax_ports[ke].ax_conn.keys():
                    bcast_mode = config.conf_ax_ports[config.ax_ports[ke].ax_conn[conn_id].port_conf_id]['bcast']
                    if bcast_mode:
                        bcast_mode = 'BRCAST'
                    else:
                        bcast_mode = 'PEER'
                    out += '{}  {:15}:{}    {:6} {:2}      {:4}     {:15}:{}\r'.format(
                        config.ax_ports[ke].ax_conn[conn_id].call_str,
                        config.ax_ports[ke].ax_conn[conn_id].axip_client[0],
                        config.ax_ports[ke].ax_conn[conn_id].axip_client[1],
                        # config.conf_ax_ports[config.ax_ports[ke].ax_conn[conn_id].port_conf_id]['parm1'],
                        # config.conf_ax_ports[config.ax_ports[ke].ax_conn[conn_id].port_conf_id]['parm2'],
                        bcast_mode,
                        # config.ax_ports[ke].ax_conn[conn_id].axip_client[1],
                        ke,
                        'n/a',
                        config.conf_ax_ports[config.ax_ports[ke].ax_conn[conn_id].port_conf_id]['parm1'],
                        config.conf_ax_ports[config.ax_ports[ke].ax_conn[conn_id].port_conf_id]['parm2']
                    )
        self.conncetion.tx_data += '\r' + out
        self.conncetion.tx_data += self.conncetion.promptvar

    def ax_routes(self):
        out = ''
        for ke in config.ax_ports.keys():
            if config.ax_ports[ke].port_typ == 'AXIP':
                out += config.ax_ports[ke].axip_clients.cli_cmd_out()
        self.conncetion.tx_data += out
        self.conncetion.tx_data += self.conncetion.promptvar

    """
    CLIDefault.cmd_dic = dict(CLIDefault.cmd_dic_default)
    CLIDefault.cmd_dic.update({
        'C': (connect, '(C)onnect to other Station ( Not implemented yet )'),
        'P': (port, 'Show (P)orts'),
        'AX': (ax_clients, 'Show (AX)IP Clients'),
        'AR': (ax_routes, 'Show (A)XIP (R)outes'),
    })
    """

    # class CLIAXIP(CLIDefault):
    def new_user(self):
        if self.scr[1] == 0:
            out = '\rHello {}..\r' \
                  'Please enter your name: '.format(self.scr[2].call_str)
            self.conncetion.tx_data += out
            self.scr = [self.new_user, 1, self.scr[2]]
            self.scr_run = False
        elif self.scr[1] == 1:
            inp = self.cmd_inp[0]
            out = '{} saved ...\r' \
                  'Please enter your QTH : '.format(inp)
            self.scr[2].name = inp
            self.conncetion.tx_data += out
            self.scr[2].is_new = False          # TODO Is just set in setup_new_connection
            self.scr = [self.new_user, 2, self.scr[2]]
        elif self.scr[1] == 2:
            inp = self.cmd_inp[0]
            out = '{} saved ...\r' \
                  'Please enter your Locator : '.format(inp)
            self.scr[2].qth = inp
            self.conncetion.tx_data += out
            self.scr = [self.new_user, 3, self.scr[2]]
        elif self.scr[1] == 3:
            inp = self.cmd_inp[0]
            config.db.save_data()
            out = '{} saved ...\r\r' \
                  'Thank you for registering.\r' \
                  'You can change all settings at any time.\r'.format(inp)
            self.scr[2].loc = inp
            self.conncetion.tx_data += out
            self.scr = []
            self.conncetion.tx_data += self.conncetion.promptvar

    def show_own_db_ent(self):
        if self.conncetion.db_entry is None:
            monitor.debug_out('Error show_own_db_ent. No DB Entry..', True)
        else:
            if not self.scr:
                self.conncetion.tx_data += '\r<User Data>\r\r'
                self.conncetion.tx_data += 'Name: {}\r'.format(self.conncetion.db_entry.name)
                self.conncetion.tx_data += 'QTH: {}\r'.format(self.conncetion.db_entry.qth)
                self.conncetion.tx_data += 'Locator: {}\r'.format(self.conncetion.db_entry.loc)
                self.conncetion.tx_data += 'Max Pac: {}\r'.format(self.conncetion.db_entry.max_pac)
                self.conncetion.tx_data += 'Pac Len: {}\r'.format(self.conncetion.db_entry.pac_len)
                # self.conncetion.tx_data += '\r'.join("%s: %s" % item for item in vars(self.conncetion.db_entry).items())
                self.conncetion.tx_data += '\rChange Data ? Type Y for Yes or Enter to continue.> '
                # self.conncetion.tx_data += self.conncetion.promptvar
                self.scr = [self.show_own_db_ent, 1]
            elif self.scr[1] == 1:
                inp = self.cmd_inp[0]
                if inp.upper() == 'Y':
                    self.scr = [self.new_user, 0, self.conncetion.db_entry]  # DUMMY
                    self.scr_run = True
                else:
                    # config.db.save_data()
                    self.scr = []
                    self.tx_cli_msg('Done')
    """
    CLIDefault.cmd_dic = dict(CLIDefault.cmd_dic_default)
    CLIDefault.cmd_dic.update({
        'X': (dummy, 'Dummy'),
    })
    """
    def test11(self):
        self.conncetion.tx_data += '\r'.join("%s: %s" % item for item in vars(self.conncetion.db_entry).items())


####################################################################
# INIT
def init_cli(conn_obj):
    # tmp_cmd_dict = dict(CLIDefault.cmd_dic_default)
    ############################################
    # Default CMD Dict
    tmp_cmd_dict = {
        'Q': (CLIDefault.quit_cmd, '(Q)uit/Bye'),
        'B': (CLIDefault.quit_cmd, '(B)ye/Quit'),
        'D': (CLIDefault.disc_cmd, '(D)isconnect from Station'),
        'MH': (CLIDefault.mh_cmd, '(MH) List'),
        '?': (CLIDefault.list_cmd_help, 'Show available Commands'),
        'H': (CLIDefault.short_help, 'Show this ..'),
        'V': (CLIDefault.vers, '(V)ersion - Software Info'),
    }

    # Node
    if 1 in conn_obj.cli_type:
        tmp_cmd_dict.update({
            'C': (CLIDefault.connect, '(C)onnect to other Station ( !Under Construction! Just for this Port.)'),
            'P': (CLIDefault.port, 'Show (P)orts'),
            'AX': (CLIDefault.ax_clients, 'Show (AX)IP Clients'),
            'AC': (CLIDefault.ax_routes, 'Show (A)XIP (C)lients'),
        })
    # File transfer
    if 3 in conn_obj.cli_type:
        tmp_cmd_dict.update({
            'UP': (CLIDefault.ft_up, '(Up)load Test File'),
            'DO': (CLIDefault.ft_dn, '(Do)wnload Test File'),
            'DT': (CLIDefault.ft_dt, '(D)ownload (T)est Data (b"123456789")'),
        })
    # AXIP
    if 4 in conn_obj.cli_type:
        tmp_cmd_dict.update({
            'UD': (CLIDefault.show_own_db_ent, 'Show own (U)ser (D)atabse entry'),

        })
    # Test
    if 9 in conn_obj.cli_type:
        tmp_cmd_dict.update({
            'T1': (CLIDefault.testfnc, 'Test Packet sender 1'),
            'T2': (CLIDefault.testfnc2, 'Test Packet sender 2'),
            'PA': (CLIDefault.sh_parm, 'Show all (Pa)rameters'),
            'RT': (CLIDefault.rtt_parm, 'Show (RT)T Parameters'),
            'UT': (CLIDefault.test11, 'Show own (U)ser (D)atabse entry Debug'),
        })

    conn_obj.cli.cmd_dic = dict(tmp_cmd_dict)
    # print(conn_obj.cli.cmd_dic)
    """
    conn_obj.cli = {
        1: CLINode,
        4: CLIAXIP,
        9: CLITest,
    }[conn_obj.cli_type](conn_obj)
    """

####################################################################
