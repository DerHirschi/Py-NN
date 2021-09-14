import os
import time

import serial
import socket
import threading
import monitor
from config import *
import ax25enc as ax

# TESTING and DEBUGGING
debug = monitor.debug
test_snd_packet = -1
p_end = False


class AXPort(threading.Thread):
    def __init__(self, port_conf_id=0):
        super(AXPort, self).__init__()
        # Globals
        self.timer_T0 = 0
        self.tx_buffer = []
        self.send_tr = False
        self.ax_Stations = {}
        self.ax_conn = {
            # 'addrStr': {
            #      ConnObj
            # }
        }
        self.port_id = port_conf_id
        self.port_typ = conf_ax_ports[port_conf_id]['typ']
        self.axip_clients = None
        if self.port_typ == 'KISS':
            self.ser_port = conf_ax_ports[port_conf_id]['parm1']
            self.ser_baud = conf_ax_ports[port_conf_id]['parm2']
        elif self.port_typ == 'AXIP':
            self.ser_baud = 1200        # TODO !! Just a dummy value !!
            self.axip_ip = conf_ax_ports[port_conf_id]['parm1']
            self.axip_port = conf_ax_ports[port_conf_id]['parm2']
            self.axip_bcast = conf_ax_ports[port_conf_id]['bcast']
            self.bcast_stations = []
            #################################
            # Init AXIP Client List
            self.axip_clients = AXIPClients(self)
        ########################################
        # AX25 Parameters
        self.parm_max_i_frame = int(DefaultParam().parm_max_i_frame)  # Max I-Frame (all connections) per Cycle
        self.parm_T0 = int(
            DefaultParam().parm_T0)  # T0 (Response Delay Timer) activated if data come in to prev resp. to early
        self.parm_T2 = int(
            DefaultParam().parm_T2)  # T0 (Response Delay Timer) activated if data come in to prev resp. to early
        self.parm_MaxBufferTX = int(DefaultParam().parm_MaxBufferTX)  # Max Frames to send from Buffer

    def run(self):
        #############################################################################
        # MAIN LOOP  / Thread
        #############################################################################
        # global test_snd_packet, tx_buffer, timer_T0
        if self.port_typ == 'KISS':
            pack = b''
            ser = serial.Serial(self.ser_port, self.ser_baud, timeout=0.5)
            while not p_end:
                b = ser.read()
                pack += b
                if b:  # RX ###################################################################################
                    self.set_t0()
                    # set_t2()
                    if ax.conv_hex(b[0]) == 'c0' and len(pack) > 2:
                        monitor.debug_out("----------------Kiss Data IN ----------------------")
                        dekiss_inp = ax.decode_ax25_frame(pack[2:-1])  # DEKISS
                        if dekiss_inp:
                            self.handle_rx(dekiss_inp)
                            ############################
                            # Monitor TODO Better Monitor
                            monitor.monitor(dekiss_inp[1], self.port_id)
                            ############################
                            # MH List and Statistics
                            mh.mh_inp(dekiss_inp, self.port_id)
                            self.timer_T0 = 0
                            monitor.debug_out('################ DEC END ##############################')
                        else:
                            monitor.debug_out("ERROR Dec> " + str(dekiss_inp), True)
                        monitor.debug_out("_________________________________________________")
                        pack = b''
                self.handle_tx()  # TX #############################################################
                if self.tx_buffer:
                    # monitor.debug_out(self.ax_conn)
                    n = 0
                    while self.tx_buffer and n < self.parm_MaxBufferTX:
                        enc = ax.encode_ax25_frame(self.tx_buffer[0][0])
                        ax.send_kiss(ser, enc)
                        mon = ax.decode_ax25_frame(bytes.fromhex(enc))
                        # self.handle_rx(mon)  # Echo TX in Monitor
                        ############################
                        # Monitor TODO Better Monitor
                        monitor.monitor(mon[1], self.port_id)
                        monitor.debug_out("Out> " + str(mon))
                        self.tx_buffer = self.tx_buffer[1:]
                        n += 1

                # TESTING
                """
                if test_snd_packet != -1 and send_tr:
                    ax.send_kiss(ser, ax.encode_ax25_frame(ax_test_pac[test_snd_packet]))
                    test_snd_packet = -1
                """
        elif self.port_typ == 'AXIP':
            axip = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
            axip.bind((self.axip_ip, self.axip_port))
            axip.settimeout(0.5)

            while not p_end:
                try:
                    bytesAddressPair = axip.recvfrom(332)
                    b = bytesAddressPair[0]
                    address = bytesAddressPair[1]
                    # clientMsg = "Message from Client:{}".format(b)
                    # clientIP = "Client IP Address:{}".format(address)

                    if b:  # RX ###################################################################################
                        ###################################
                        # CRC
                        crc = b[-2:]
                        crc = int(ax.bytearray2hexstr(crc[::-1]), 16)
                        msg = b[:-2]
                        calc_crc = ax.crc_x25(msg)
                        ###################################
                        if calc_crc == crc:
                            monitor.debug_out("----------------AXIP Data IN ----------------------")
                            decode_inp = ax.decode_ax25_frame(msg)
                            if decode_inp:
                                self.handle_rx(decode_inp, address)
                                ############################
                                # Monitor TODO Better Monitor
                                monitor.monitor(decode_inp[1], self.port_id)
                                ############################
                                # MH List and Statistics
                                mh.mh_inp(decode_inp, self.port_id)
                                self.timer_T0 = 0
                                monitor.debug_out('################ DEC END ##############################')
                                call_st = decode_inp[0].split(':')[1]
                                ###########################
                                # New Client
                                if call_st not in self.axip_clients.clients.keys():
                                    self.axip_clients.clients[call_st] = {}
                                if call_st not in db.db.keys():
                                    ######################################
                                    # ADD New User in DB
                                    db_e = db.get_entry(call_st)
                                    """
                                    if hasattr(db, 'pac_len'):
                                        db_e.pac_len = self.bcast_stations[0].ax25PacLen
                                    if hasattr(db, 'max_pac'):
                                        db_e.max_pac = self.bcast_stations[0].ax25MaxFrame
                                    """
                                    ###########################################
                                    # New Client Beacon
                                    if self.bcast_stations:
                                        via = []
                                        for el in list(decode_inp[1]['via']):
                                            via.append([el[0], el[1], False])
                                        via.reverse()
                                        txt = '>> Hello {} ! <<\r'\
                                                '> You have to register your Station first for Broadcast Mode <\r'\
                                                '> Please connect to {} to register your Station <\r'.format(
                                                ax.get_call_str(decode_inp[1]['FROM'][0], decode_inp[1]['FROM'][1]),
                                                self.bcast_stations[0].call_str)
                                        self.cron_add(txt, 30, self.bcast_stations[0].call_str,
                                                      ax.get_call_str(decode_inp[1]['FROM'][0], decode_inp[1]['FROM'][1]),
                                                      address, via, 5)
                                else:
                                    if db.db[call_st].is_new:
                                        # print('New User 222222')
                                        if self.bcast_stations:
                                            via = []
                                            # TODO .. need a func for this and above
                                            for el in list(decode_inp[1]['via']):
                                                via.append([el[0], el[1], False])
                                            via.reverse()
                                            txt = '>> Hello {} ! <<\r' \
                                                  '> You have to register your Station first for Broadcast Mode <\r' \
                                                  '> Please connect to {} to register your Station <\r'.format(
                                                ax.get_call_str(decode_inp[1]['FROM'][0], decode_inp[1]['FROM'][1]),
                                                self.bcast_stations[0].call_str)
                                            self.cron_add(txt, 30, self.bcast_stations[0].call_str,
                                                          ax.get_call_str(decode_inp[1]['FROM'][0],
                                                                          decode_inp[1]['FROM'][1]),
                                                          address, via, 5)
                                self.axip_clients.clients[call_st]['addr'] = address
                                self.axip_clients.clients[call_st]['port'] = self.port_id
                                self.axip_clients.clients[call_st]['lastsee'] = time.time()
                                if self.axip_bcast:
                                    # for ke in self.ax_conn.keys():
                                    # axip.sendall(b)
                                    tmp_addr = [address]
                                    for ke in self.axip_clients.clients.keys():
                                        addr = self.axip_clients.clients[ke]['addr']
                                        if addr not in tmp_addr and not db.db[ke].is_new:
                                            print('## SEND RCV BCAST')
                                            axip.sendto(b, addr)
                                            # time.sleep(0.1)
                                            # print('Send 1> ' + str(addr))
                                            tmp_addr.append(addr)

                            else:
                                monitor.debug_out("ERROR Dec> " + str(decode_inp), True)
                            # pack = b''
                        else:
                            monitor.debug_out("ERROR CRC AXIP> " + str(b), True)
                            monitor.debug_out("_________________________________________________")

                except socket.timeout:
                    pass

                self.handle_tx()  # TX #############################################################
                if self.tx_buffer:
                    # monitor.debug_out(self.ax_conn)
                    n = 0
                    while self.tx_buffer and n < self.parm_MaxBufferTX:
                        enc = ax.encode_ax25_frame(self.tx_buffer[0][0])
                        address = self.tx_buffer[0][1]
                        ###################################
                        # CRC
                        enc = bytes.fromhex(enc)
                        calc_crc = ax.crc_x25(enc)
                        calc_crc = bytes.fromhex(hex(calc_crc)[2:].zfill(4))[::-1]
                        ###################################
                        dest_call = ax.get_call_str(self.tx_buffer[0][0]['dest'][0], self.tx_buffer[0][0]['dest'][1])
                        print('### DEST CALL > ' + str(dest_call))
                        if self.axip_bcast and not db.db[dest_call].is_new:
                            print('### SEND BCAST')
                            # axip.sendall(enc + calc_crc)
                            tmp_addr = []
                            for ke in self.axip_clients.clients.keys():
                                # is_new = db.db[ke].is_new
                                addr = self.axip_clients.clients[ke]['addr']
                                if addr not in tmp_addr:
                                    axip.sendto(enc + calc_crc, addr)
                                    # time.sleep(0.1)
                                    tmp_addr.append(addr)

                        else:
                            # print("Send AXIP TTO > " + str(address))
                            ###########################
                            # DEBUG !!!!!!!!!!!!!!!!!!!
                            # UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
                            # UDPClientSocket.sendto(enc + calc_crc, address)
                            ###########################
                            if address:
                                axip.sendto(enc + calc_crc, address)
                        mon = ax.decode_ax25_frame(enc)
                        # self.handle_rx(mon)  # Echo TX in Monitor
                        ############################
                        # Monitor TODO Better Monitor
                        monitor.monitor(mon[1], self.port_id)
                        monitor.debug_out("Out> " + str(mon))
                        self.tx_buffer = self.tx_buffer[1:]
                        n += 1

            axip.close()
        ########################
        # Save Data to File
        mh.save_mh_data()
        ########################
        # Save Client DB
        db.save_data()
        #####################################################
        # TODO Could cause Problems with multiple AXIP Ports
        if self.axip_clients:
            self.axip_clients.save_data()

    def get_tx_packet_item(self, rx_inp=None, conn_id=None):
        if rx_inp:
            via = []
            tm = list(rx_inp['via'])
            tm.reverse()
            for el in tm:
                via.append([el[0], el[1], False])
            return {
                'call': list(rx_inp['TO']),
                'dest': list(rx_inp['FROM']),
                'via': via,
                'out': '',
                'typ': [],                  # ['SABM', True, 0],   # Type, P/F, N(R), N(S)
                'cmd': False,
                'pid': 6,
    
            }
        elif conn_id:
            return {
                'call': self.ax_conn[conn_id].call,
                'dest': self.ax_conn[conn_id].dest,
                'via': self.ax_conn[conn_id].via,
                'out': '',
                'typ': [],                 # ['SABM', True, 0],  # Type, P/F, N(R), N(S)
                'cmd': False,
                'pid': 6,
    
            }
    
    def set_t1(self, conn_id):
        ns = int(self.ax_conn[conn_id].n2)
        srtt = float(self.ax_conn[conn_id].parm_IRTT)
        if self.ax_conn[conn_id].via:
            srtt = int((len(self.ax_conn[conn_id].via) * 2 + 1) * self.ax_conn[conn_id].parm_IRTT)
        if ns > 3:
            self.ax_conn[conn_id].t1 = float(((srtt * (ns + 4)) / 100) + time.time())
        else:
            self.ax_conn[conn_id].t1 = float(((srtt * 3) / 100) + time.time())
        # print('#### T1 > ' + str(self.ax_conn[conn_id].t1 - time.time()))
        self.ax_conn[conn_id].deb_calc_t1 = (srtt, self.ax_conn[conn_id].t1 - time.time())

    def set_t2(self, conn_id):
        # global timer_T2
        # timer_T2 = float(parm_T2 / 100 + time.time())
        self.ax_conn[conn_id].t2 = float(self.ax_conn[conn_id].parm_T2 / 100 + time.time())
        # print('#### T2 > ' + str(self.ax_conn[conn_id].t2 - time.time()))

    def set_t3(self, conn_id):
        self.ax_conn[conn_id].t3 = float(self.ax_conn[conn_id].ax25T3 / 100 + time.time())
        # print('#### T3 > ' + str(self.ax_conn[conn_id].t3 - time.time()))

    def set_t0(self):
        self.timer_T0 = float(self.parm_T0 / 100 + time.time())

    ######################################################################
    # RX Handler
    ######################################################################
    def handle_rx(self, rx_inp, axip_client=()):

        conn_id = ax.reverse_addr_str(rx_inp[0])
        own_call = rx_inp[0].split(':')[0]

        if (own_call in list(self.ax_Stations.keys())) or (conn_id in list(self.ax_conn.keys())):
            # print('## RX HANDLE IN > ' + str(conn_id))
            '''
            if rx_inp[1]['via'] and all(not el[2] for el in rx_inp[1]['via']):
                monitor.debug_out('###### Data In not Digipeated yet !!########')
                monitor.debug_out('')
            '''
            ############################################
            # Check if Packet run through all Digis
            if not rx_inp[1]['via'] or all(el[2] for el in rx_inp[1]['via'])\
                    or (own_call not in list(self.ax_Stations.keys())):     # TODO Looking for the right DIGI-Bit
                # print('### RX HAN DIGI > ' + str(conn_id))

                # Incoming DISC
                if rx_inp[1]['ctl']['hex'] == 0x53:     # DISC p/f True
                    self.DISC_RX(conn_id, rx_inp=rx_inp[1], axip_client=axip_client)  # Handle DISC Request
                #########################################################################################
                # Incoming UI
                # elif inp[1]['ctl']['hex'] == 0x13:                      # UI p/f True
                #     DM_TX(inp[1])                                       # Confirm UI ??? TODO DM or UA ?
                #########################################################################################
                # Incoming connection SABM or SABME
                elif rx_inp[1]['ctl']['hex'] in [0x3f, 0x7f]:              # SABM or SABME p/f True
                    self.SABM_RX(conn_id, rx_inp=rx_inp[1], owncall=own_call, axip_cl=axip_client)   # Handle connect Request
                # Connected Stations
                elif conn_id in self.ax_conn.keys():
                    self.ax_conn[conn_id].axip_client = axip_client
                    self.handle_rx_fm_conn(conn_id, rx_inp[1])
                else:
                    self.DM_TX(rx_inp[1], axip_client=axip_client)
        else:
            ################################################
            # DIGI
            for v in rx_inp[1]['via']:
                # if not v[2] and (any(digi_calls) in [v[0], v[1]]):
                c_str = ax.get_call_str(v[0], v[1])
                if not v[2] and (c_str in digi_calls.keys()):
                    print('DIGI > ' + str(rx_inp[0]))
                    v[2] = True
                    port = digi_calls[c_str]
                    port.DigiPeating(rx_inp[1], axip_cl=axip_client)
                    break
                elif not v[2] and (c_str not in digi_calls.keys()):
                    break

    def handle_rx_fm_conn(self, conn_id, rx_inp):
        monitor.debug_out('')
        monitor.debug_out('###### Conn Data In ########')
        monitor.debug_out(conn_id)
        monitor.debug_out('IN> ' + str(rx_inp))
        self.set_t3(conn_id)
        self.set_t2(conn_id)
        # print('Pac fm connection incoming... ' + conn_id)
        # print('IN> ' + str(rx_inp['FROM']) + ' ' + str(rx_inp['TO']) + ' ' + str(rx_inp['via']) + ' ' + str(rx_inp['ctl']))
        #################################################
        if rx_inp['ctl']['hex'] == 0x73:                   # UA p/f True
            self.UA_RX(conn_id)
        #################################################
        elif rx_inp['ctl']['hex'] == 0x1F:                 # DM p/f True
            self.DM_RX(conn_id)
        #################################################
        elif rx_inp['ctl']['flag'] == 'I':                 # I
            self.I_RX(conn_id, rx_inp)
        #################################################
        elif rx_inp['ctl']['flag'] == 'RR':                # RR
            self.RR_RX(conn_id, rx_inp)
        #################################################
        elif rx_inp['ctl']['flag'] == 'REJ':               # REJ
            self.REJ_RX(conn_id, rx_inp)
        #################################################
        elif rx_inp['ctl']['flag'] == 'FRMR':              # FRMR  TODO
            monitor.debug_out('#### FRMR Rec ###### ' + str(rx_inp))
            monitor.debug_out('#### FRMR Rec ###### ' + str(rx_inp), True)
            print('#### FRMR Rec ###### ' + str(rx_inp))
            self.DISC_TX(conn_id)
        monitor.debug_out('#### Conn Data In END ######')
        monitor.debug_out('')
        # print('~~~~~~RX IN~~~~~~~~~~~~~~')
        # print('')

    def DigiPeating(self, rx_inp, axip_cl=()):
        print('###### DIGI FNC > ' + str(rx_inp))
        pac = {
            'call': rx_inp['FROM'],
            'dest': rx_inp['TO'],
            'via': rx_inp['via'],
            'out': rx_inp['data'][0],
            'cmd': rx_inp['ctl']['cmd'],
            'pid': rx_inp['pid'],
            'typ': [rx_inp['ctl']['flag'], rx_inp['ctl']['pf'], rx_inp['ctl']['nr'], rx_inp['ctl']['ns']]
        }
        if rx_inp['pid']:
            pac['pid'] = int(rx_inp['pid'][1], 16)
    
        # TODO ##############################################################################
        # Maybe extra Buffer or Default Conn_id for Digi to control timing from TXing Packets
        self.tx_buffer.append([pac, axip_cl])
        # TODO ######### tx_buffer.append(pac) Just for testing

    def SABM_TX(self):
        os.system('clear')
        dest = input('Enter Dest. Call\r\n> ').upper()
        # TODO !!! Select right own Call
        conn_id = dest + ':' + ax.get_call_str(DefaultParam.call, DefaultParam.ssid)
        dest = ax.get_ssid(dest)
        print('')
        via = input('Enter via\r\n> ').upper()
        via_list = []
        via = via.split(' ')
        if via == [''] or via == [None]:
            via = []
        for el in via:
            conn_id += ':' + el
            tm = ax.get_ssid(el)
            tm.append(False)        # Digi Trigger ( H BIT )
            via_list.append(tm)
        print(conn_id)
        print(via)
        print(via_list)
    
        if conn_id not in self.ax_conn.keys():
            self.ax_conn[conn_id] = DefaultParam()
            self.ax_conn[conn_id].dest = [dest[0], dest[1]]
            self.ax_conn[conn_id].via = via_list
            self.ax_conn[conn_id].stat = 'SABM'
            tx_pack = self.get_tx_packet_item(conn_id=conn_id)
            tx_pack['typ'] = ['SABM', True]
            tx_pack['cmd'] = True
            self.ax_conn[conn_id].tx = [tx_pack]
            # set_t1(conn_id)
            self.set_t3(conn_id)
            print(self.ax_conn)
            print("OK ..")
        else:
            print('Busy !! There is still a connection to this Station !!!')
            print('')

    def SABM_RX(self, conn_id, rx_inp, owncall, axip_cl=()):
        monitor.debug_out('')
        monitor.debug_out('#### Connect Request fm ' + rx_inp['FROM'][0])
        monitor.debug_out(conn_id)
        monitor.debug_out('')
        print('#### Connect Request fm ' + rx_inp['FROM'][0])
        print(conn_id)
        # Setup NEW conn Data
        if conn_id not in self.ax_conn:
            self.setup_new_conn(conn_id, rx_inp, owncall, axip_addr=axip_cl)
        #############################################################################
        # Verb. wird zurueck gesetzt nach empfangen eines SABM.
        # evtl. bestehenden TX-Buffer speichern um mit der Uebertragung fortzufahren.
        self.ax_conn[conn_id].vs, self.ax_conn[conn_id].vr = 0, 0
        self.ax_conn[conn_id].t1 = 0
        self.ax_conn[conn_id].n2 = 1
        self.ax_conn[conn_id].tx = []
        self.ax_conn[conn_id].tx_data = ''
        self.ax_conn[conn_id].rx_data = []
        self.ax_conn[conn_id].noAck = []
        self.ax_conn[conn_id].snd_RRt3 = False
        self.ax_conn[conn_id].snd_rej = [False, False]
        self.ax_conn[conn_id].ack = [False, False, False]
        self.ax_conn[conn_id].axip_client = axip_cl
        # Set State to Receive Ready
        self.ax_conn[conn_id].stat = 'RR'
        # Answering Conn Req (UA).
        self.ax_conn[conn_id].tx_ctl = [self.UA_frm(rx_inp)]
        #############################################################################
    
        #####################################################################################
        # C-Text
        if self.ax_conn[conn_id].dest[0] in self.ax_conn[conn_id].station_ctexte_var.keys():
            self.ax_conn[conn_id].tx_data += self.ax_conn[conn_id].station_ctexte_var[self.ax_conn[conn_id].dest[0]]
        else:
            self.ax_conn[conn_id].tx_data += self.ax_conn[conn_id].ctextvar
        #####################################################################################

    def confirm_I_Frames(self, conn_id, rx_inp):
        #####################################################################################
        # Python is fucking up with Arrays in For Loop. It jumps over Elements. Why ??
        # ??? Because of Threading and global Vars ???
        no_ack = list(self.ax_conn[conn_id].noAck)             # Wie waere es mit Modulo Restklassen ??
        tmp_tx_buff = list(self.ax_conn[conn_id].tx)
        # print('### conf. VS > ' + str(no_ack))
    
        if no_ack:
            ind_val = (rx_inp['ctl']['nr'] - 1) % 8
            # print('### conf. VS ind_val > ' + str(ind_val))
            if ind_val in no_ack:
                ind = no_ack.index(ind_val) + 1
                tmp_ack = no_ack[:ind]
                # print('### conf. tmp_Ack > ' + str(self.ax_conn[conn_id].noAck))
                #############################################
                # Fetch unconfirmed I Frames in Buffer
                rmv_list = []
                for el in tmp_tx_buff:
                    if el['typ'][0] == 'I' and el['typ'][3] in tmp_ack:
                        rmv_list.append(el)
                #############################################
                # Delete confirmed I Frames from TX- Buffer
                # Delete all VS < VR
                for el in rmv_list:
                    tmp_tx_buff.remove(el)
                    no_ack.remove(el['typ'][3])
                    # TODO RTT Calc just on RR cmd Frame???
                    self.ax_conn[conn_id].parm_RTT = (time.time() - self.ax_conn[conn_id].rtt[int(el['typ'][3])]) * 100
                    # print('######### Parm RTT > ' + str(self.ax_conn[conn_id].parm_RTT))
                    # print('######### Parm IRTT > ' + str(self.ax_conn[conn_id].parm_IRTT))
                    del self.ax_conn[conn_id].rtt[int(el['typ'][3])]
                    # print('######### RTT > ' + str(ax_conn[conn_id].rtt))
    
                self.ax_conn[conn_id].tx = tmp_tx_buff
                self.ax_conn[conn_id].noAck = no_ack
                self.ax_conn[conn_id].vs = rx_inp['ctl']['nr']
        self.ax_conn[conn_id].n2 = 1
        self.ax_conn[conn_id].t1 = 0

    def RR_RX(self, conn_id, rx_inp):
        if self.ax_conn[conn_id].snd_RRt3 and rx_inp['ctl']['pf']:
            self.ax_conn[conn_id].snd_RRt3 = False
        # Confirm I Frames
        elif rx_inp['ctl']['cmd'] or rx_inp['ctl']['pf']:
            self.ax_conn[conn_id].ack = [True, rx_inp['ctl']['pf'], False]
        self.confirm_I_Frames(conn_id, rx_inp)
        self.ax_conn[conn_id].t1 = 0

    def RR_TX_T3(self, conn_id):
        # T3 is done ( Hold connection )
        # TODO RTT Calc just on RR cmd Frame???
        self.ax_conn[conn_id].ack = [False, True, True]
        self.ax_conn[conn_id].tx_ctl = [self.RR_frm(conn_id)] + list(self.ax_conn[conn_id].tx_ctl)
        self.ax_conn[conn_id].snd_RRt3 = True
        self.set_t1(conn_id)

    def REJ_RX(self, conn_id, rx_inp):
        self.confirm_I_Frames(conn_id, rx_inp)

    def REJ_TX(self, conn_id):
        self.ax_conn[conn_id].tx_ctl.append(self.REJ_frm(conn_id, self.ax_conn[conn_id].rej[1], False))
        self.ax_conn[conn_id].rej = [False, False]
        print('###### REJ_TX > ' + str(conn_id))

    def I_RX(self, conn_id, rx_inp):
        if rx_inp['ctl']['ns'] == self.ax_conn[conn_id].vr:
            self.ax_conn[conn_id].rx_data.append(rx_inp['data'])
            self.ax_conn[conn_id].vr = (1 + self.ax_conn[conn_id].vr) % 8
            self.ax_conn[conn_id].t1 = 0
            self.confirm_I_Frames(conn_id, rx_inp)
            if rx_inp['ctl']['pf']:
                self.ax_conn[conn_id].ack = [False, True, False]
                # Send single RR if P Bit is received
                self.tx_buffer.append([self.RR_frm(conn_id), self.ax_conn[conn_id].axip_client])
            else:
                self.ax_conn[conn_id].ack = [True, self.ax_conn[conn_id].ack[1], False]
    
            # print('###### I-Frame > ' + str(rx_inp['data']))
        else:
            print('###### REJ_TX inp > ' + str(rx_inp))
            self.ax_conn[conn_id].rej = [True, rx_inp['ctl']['pf']]

    def I_TX(self, conn_id, data=''):
        if self.ax_conn[conn_id].stat != 'RR':
            return False
        if len(self.ax_conn[conn_id].noAck) >= 7:
            return False
        self.ax_conn[conn_id].tx.append(self.I_frm(conn_id, data))
        self.ax_conn[conn_id].vs = int((1 + self.ax_conn[conn_id].vs) % 8)
        self.ax_conn[conn_id].n2 = 1
        return True
    
    def DM_TX(self, rx_inp, pf_bit=True, axip_client=()):    # !!!!!!!!!!! Dummy. !! Not Tested  !!!!!!!!!!!!!
        self.tx_buffer.append([self.DM_frm(rx_inp, pf_bit), axip_client])
        # Will send if Station is Busy or can't request SABM or receive any other Pac as SABM, UI
        # Also will send to confirm a UI Pac if station is not connected

    def DM_RX(self, conn_id):
        if self.ax_conn[conn_id].stat == 'SABM':
            print('#### Called Station is Busy ..... ######')
        self.ax_conn[conn_id] = None
        del self.ax_conn[conn_id]

    def UA_RX(self, conn_id):
        self.ax_conn[conn_id].n2 = 1
        self.ax_conn[conn_id].t1 = 0
        self.ax_conn[conn_id].vs, self.ax_conn[conn_id].vr = 0, 0
        if self.ax_conn[conn_id].stat == 'SABM':
            self.ax_conn[conn_id].tx = self.ax_conn[conn_id].tx[1:]          # Not lucky with that solution TODO
            self.ax_conn[conn_id].stat = 'RR'
            monitor.debug_out('#### Connection established ..... ######')
            print('#### Connection established ..... ######')
        elif self.ax_conn[conn_id].stat == 'DISC':
            monitor.debug_out('#### Disc confirmed ..... ######')
            # monitor.debug_out('ax_conn[id][tx]> ' + str(ax_conn[conn_id].tx))
            print('#### Disc confirmed ..... ######')
            self.ax_conn[conn_id] = None
            del self.ax_conn[conn_id]

    def DISC_TX(self, conn_id):
        monitor.debug_out('')
        monitor.debug_out('#### DISCO Send ..... ######')
        monitor.debug_out(conn_id)
        print('#### DISCO Send to ' + self.ax_conn[conn_id].dest[0])
        print(conn_id)
        if self.ax_conn[conn_id].stat == 'RR':
            self.ax_conn[conn_id].ack = [False, False, False]
            self.ax_conn[conn_id].rej = [False, False]
            self.ax_conn[conn_id].stat = 'DISC'
            if self.ax_conn[conn_id].cli:
                self.ax_conn[conn_id].cli.stat = 'HOLD'
            self.ax_conn[conn_id].n2 = 1
            self.ax_conn[conn_id].t1 = 0
            self.ax_conn[conn_id].tx_bin = bytearray(0)
            self.ax_conn[conn_id].tx_data = ''
            # ax_conn[conn_id].noAck = []
            self.ax_conn[conn_id].tx = [self.DISC_frm(conn_id)]
        elif self.ax_conn[conn_id].stat == 'SABM':
            self.tx_buffer.append([self.DISC_frm(conn_id), self.ax_conn[conn_id].axip_client])
            self.ax_conn[conn_id] = None
            del self.ax_conn[conn_id]
        elif self.ax_conn[conn_id].stat == 'DISC' and self.ax_conn[conn_id].n2 > self.ax_conn[conn_id].ax25N2:
            self.tx_buffer.append([self.DISC_frm(conn_id), self.ax_conn[conn_id].axip_client])
            self.ax_conn[conn_id] = None
            del self.ax_conn[conn_id]

    def DISC_RX(self, conn_id, rx_inp, axip_client=()):
        monitor.debug_out('')
        monitor.debug_out('#### DISCO Request ..... ######')
        monitor.debug_out(conn_id)
        print('#### DISCO Request fm ' + rx_inp['FROM'][0])
        print(conn_id)
        # Answering DISC
        if conn_id in self.ax_conn.keys():
            self.tx_buffer.append([dict(self.UA_frm(rx_inp)), tuple(self.ax_conn[conn_id].axip_client)])       # UA_TX
            for k in list(self.ax_conn[conn_id].node_links.keys()):
                self.ax_conn[conn_id].node_links[k].link.node_links[conn_id].disc()
                """
                if self.ax_conn[conn_id].node_links[k].link.node_links[conn_id].caller_id != conn_id:
                    self.ax_conn[conn_id].node_links[k].link.node_links[conn_id].link.cli.state = 'DISC'
                    print('CLI DISC> ' + str(conn_id))
                """
                self.ax_conn[conn_id].node_links[k].disc()
            # TODO deketed connection cause problems after disco in non BCAST Mode
            # if self.port_typ != 'AXIP':
            del self.ax_conn[conn_id]  # TODO AXIP non BCAST MODE
        else:
            axip_client = db.get_entry(ax.get_call_str(rx_inp['FROM'][0], rx_inp['FROM'][1])).last_axip_addr
            self.tx_buffer.append([self.DM_frm(rx_inp), axip_client])
    #######################################################################

    def UI_frm(self, frm, to, out, via=None, axip_cl=()):
        # UI Frame ( Beacon )
        if via is None:
            via = []
        self.tx_buffer.append([{
            'call': frm,
            'dest': to,
            'via': via,
            'out': out,
            'typ': ['UI', True],
            'cmd': False,
            'pid': 6,
        }, axip_cl])

    def UA_frm(self, rx_inp):
        # Answering Conn Req. or Disc Frame
        pac = self.get_tx_packet_item(rx_inp=rx_inp)
        pac['typ'] = ['UA', rx_inp['ctl']['pf']]
        pac['cmd'] = False
        return pac

    def I_frm(self, conn_id, data=''):
        pac = self.get_tx_packet_item(conn_id=conn_id)
        # VR will be set again just before sending !!!
        # print('#### I-Frm vs > ' + str(ax_conn[conn_id].vs) )
        # print('#### I-Frm noAck > ' + str(ax_conn[conn_id].noAck) )
        if self.ax_conn[conn_id].noAck:
            vs = int((self.ax_conn[conn_id].noAck[-1] + 1) % 8)
        else:
            vs = int(self.ax_conn[conn_id].vs)
        # print('#### I-Frm vs calc  > ' + str(vs))
        self.ax_conn[conn_id].noAck.append(vs)
        pac['typ'] = ['I', False, self.ax_conn[conn_id].vr, vs]
        pac['cmd'] = True
        pac['pid'] = 6
        pac['out'] = data
        return pac

    def DM_frm(self, rx_inp, f_bit=None):
        # Answering DISC
        if f_bit is None:
            f_bit = rx_inp['ctl']['pf']
        pac = self.get_tx_packet_item(rx_inp=rx_inp)
        pac['typ'] = ['DM', f_bit]
        pac['cmd'] = False
        return pac

    def DISC_frm(self, conn_id):
        # DISC Frame
        pac = self.get_tx_packet_item(conn_id=conn_id)
        pac['typ'] = ['DISC', True]
        pac['cmd'] = True
        return pac

    def RR_frm(self, conn_id):
        # RR Frame
        pac = self.get_tx_packet_item(conn_id=conn_id)
        pac['typ'] = ['RR', self.ax_conn[conn_id].ack[1], self.ax_conn[conn_id].vr]
        pac['cmd'] = self.ax_conn[conn_id].ack[2]
        # print('######## Send RR >')
        self.ax_conn[conn_id].ack = [False, False, False]
        return pac

    def REJ_frm(self, conn_id, pf_bit=False, cmd=False):
        # REJ Frame
        pac = self.get_tx_packet_item(conn_id=conn_id)
        pac['typ'] = ['REJ', pf_bit, self.ax_conn[conn_id].vr]
        pac['cmd'] = cmd
        # ax_conn[conn_id].rej = [False, False]
        print('######## Send REJ >')
        print(pac)
        print('')
        return pac

    #############################################################################
    #############################################################################

    def setup_new_conn(self, conn_id, rx_inp, mycall, axip_addr=()):
        tmp = self.ax_Stations[mycall]()
        from_call, to_call = rx_inp['FROM'], rx_inp['TO']
        tmp.dest = [from_call[0], from_call[1]]
        tmp.db_entry = db.get_entry(ax.get_call_str(tmp.dest))
        via = []
        for el in rx_inp['via']:
            via.append([el[0], el[1], False])
        via.reverse()
        tmp.via = via
        tmp.vs, tmp.vr = 0, 0
        tmp.t1 = 0
        tmp.n2 = 1
        tmp.tx = []
        tmp.tx_data = ''
        tmp.rx_data = []
        tmp.noAck = []
        tmp.snd_RRt3 = False
        tmp.snd_rej = [False, False]
        tmp.ack = [False, False, False]
        tmp.port = self

        if axip_addr:
            tmp.db_entry.last_axip_addr = axip_addr
        tmp.db_entry.axip_addr = axip_addr
        ####################################
        # TODO Broadcast New User
        # print(tmp.db_entry)
        # print(tmp.db_entry.is_new)
        if tmp.db_entry.is_new:
            print('NEW USER CONNECTED !!!')
            # Del New User Beacon
            # TODO Beacon ll still added again till user has registration complete
            tmp.db_entry.is_new = False
            self.cron_del(tmp.db_entry.call_str)
            # Setup New User CLI TODO
            tmp.cli.scr = [tmp.cli.new_user, 0, tmp.db_entry]    # DUMMY
            tmp.cli.scr_run = True    # DUMMY
            # ADD User zu User C TEXT ( New User CTEXT )
            tmp.station_ctexte_var[tmp.dest[0]] = 'HELLO NEW USER ..BLA BLA'
            ####################################
            # tmp.db_entry.is_new = False
        tmp.conn_id = conn_id
        self.ax_conn[conn_id] = tmp
        self.set_t3(conn_id)
        print('\r\n'.join("%s: %s" % item for item in vars(self.ax_conn[conn_id].db_entry).items()))

    def disc_all_stations(self):
        tmp = self.ax_conn.keys()
        for conn_id in list(tmp):
            self.DISC_TX(conn_id)

    def tx_data2tx_buffer(self, conn_id):
        if self.ax_conn[conn_id].tx_bin:
            data = bytearray(self.ax_conn[conn_id].tx_bin)
            tr = True
        else:
            data = str(self.ax_conn[conn_id].tx_data)
            tr = False
        if data:
            if self.ax_conn[conn_id].db_entry.max_pac:
                maxFrm = int(self.ax_conn[conn_id].db_entry.max_pac)
            else:
                maxFrm = int(self.ax_conn[conn_id].ax25MaxFrame)
            free_txbuff = maxFrm - len(self.ax_conn[conn_id].noAck)
            for i in range(free_txbuff):
                if data:
                    if self.ax_conn[conn_id].db_entry.pac_len:
                        paclen = int(self.ax_conn[conn_id].db_entry.pac_len)
                    else:
                        paclen = int(self.ax_conn[conn_id].ax25PacLen)

                    if self.I_TX(conn_id, data[:paclen]):
                        data = data[paclen:]
                    else:
                        break
                else:
                    break
            if tr:
                self.ax_conn[conn_id].tx_bin = data
            else:
                self.ax_conn[conn_id].tx_data = data

    def send_Ack(self, id_in):
        if self.ax_conn[id_in].stat == 'RR':
            ######################################################
            # Send REJ
            if self.ax_conn[id_in].rej[0]:
                self.REJ_TX(id_in)
            ######################################################
            # Send Ack if not sendet with I Frame
            elif self.ax_conn[id_in].ack[0]:
                self.tx_buffer.append([self.RR_frm(id_in), self.ax_conn[id_in].axip_client])

    #############################################################################
    # CRON
    #############################################################################
    def cron_add(self, text, period, from_call_str, to_call_str='ALL', axip_cl=(), via=None, n_times=-1):
        """
        cron_pacs = {
           'callstr': [[pac, from, period, next_send, axip]]
        }
        """
        if via is None:
            via = []
        print('Cron Set')
        if to_call_str in cron_pacs.keys():
            for el in cron_pacs[to_call_str]:
                if text == el[0] and from_call_str == el[1] and axip_cl == el[4] and via == el[5]:
                    print('Add Again')
                    return
            cron_pacs[to_call_str].append([text, from_call_str, period, time.time(), axip_cl, via, n_times])
            print('Add Again 2')

        else:
            cron_pacs[to_call_str] = [[text, from_call_str, period, time.time(), axip_cl, via, n_times]]

    def cron_del(self, to_call_str):
        print('Del Crone')

        if to_call_str in cron_pacs.keys():
            print('Del Crone')
            print(str(cron_pacs))
            del cron_pacs[to_call_str]
            print(str(cron_pacs))

    def cron_main(self):
        for k in list(cron_pacs.keys()):
            del_ind = []
            for el in cron_pacs[k]:
                if el[3] < time.time():
                    print('Crone Triggert: ' + str(el))
                    el[3] = time.time() + el[2]
                    if k == 'ALL':
                        for ke in self.axip_clients.clients.keys():
                            addr = self.axip_clients.clients[ke]['addr']
                            self.UI_frm(ax.get_ssid(el[1]),
                                        ax.get_ssid(k), el[0], el[5], addr)
                    else:
                        self.UI_frm(ax.get_ssid(el[1]),
                                    ax.get_ssid(k), el[0], el[5], el[4])
                    if el[6] != -1:
                        if el[6] == 1:
                            del_ind.append(el)
                        else:
                            el[6] -= 1
                for ind in del_ind:
                    cron_pacs[k].remove(ind)

    #############################################################################
    # TX
    #############################################################################
    def handle_tx(self):
        max_i_frame_c_f_all_conns = 0
        disc_keys = []
        pac_c = 0

        #############################################
        # Check T0
        if time.time() > self.timer_T0 or self.timer_T0 == 0:
            #############################################
            # Crone ( Beacons )
            self.cron_main()
            for conn_id in list(self.ax_conn.keys()):
                # max_f = 0
                #############################
                # Dead Link Check
                for ke in self.ax_conn[conn_id].node_links.keys():
                    if conn_id != self.ax_conn[conn_id].node_links[ke].caller_id and\
                                self.ax_conn[conn_id].node_links[ke].stat == 'DISC' and\
                                self.ax_conn[conn_id].stat != 'DISC':
                        print(">Dead Link>>>>>> " + str(ke))
                        self.DISC_TX(conn_id)
                #############################################
                # CLI
                self.ax_conn[conn_id].handle_cli()
                #############################################
                # Check T2
                if time.time() > self.ax_conn[conn_id].t2 or self.ax_conn[conn_id].t2 == 0:
                    if pac_c > self.parm_MaxBufferTX:
                        self.send_Ack(conn_id)
                        # set_t2(conn_id)
                        break
                    n2 = int(self.ax_conn[conn_id].n2)
                    t1 = float(self.ax_conn[conn_id].t1)
                    snd_tr = False
    
                    ####################################################################
                    # T3
                    '''
                    if (time.time() > ax_conn[conn_id].t3 or ax_conn[conn_id].snd_RRt3)\
                            and (not ax_conn[conn_id].tx_ctl and not ax_conn[conn_id].tx_ctl)\
                            and (time.time() > t1 or t1 == 0):
                    '''
                    if (time.time() > self.ax_conn[conn_id].t3 or self.ax_conn[conn_id].snd_RRt3) \
                            and not self.ax_conn[conn_id].tx_ctl \
                            and (time.time() > t1 or t1 == 0):  # TODO .. ?? Check tx_ctl ??
                        self.RR_TX_T3(conn_id)
                    elif not self.ax_conn[conn_id].snd_RRt3:
                        ####################################################################
                        self.tx_data2tx_buffer(conn_id)      # Fill free TX "Slots" with data
                        ####################################################################
                    ####################################################################
                    # CTL Frames ( Not T1 controlled ) just T2
                    tx_ctl = list(self.ax_conn[conn_id].tx_ctl)
                    for el in tx_ctl:
                        self.tx_buffer.append([el, self.ax_conn[conn_id].axip_client])
                        self.ax_conn[conn_id].tx_ctl = self.ax_conn[conn_id].tx_ctl[1:]
                        pac_c += 1
                        if self.ax_conn[conn_id].snd_RRt3:
                            break
                    #############################################
                    # Timeout and N2 out
                    if n2 > self.ax_conn[conn_id].ax25N2 and (time.time() > t1 != 0):
                        # DISC ???? TODO Testing
                        monitor.debug_out('#### Connection failure ..... ######' + conn_id)
                        print('#### Connection failure ..... ######' + conn_id)
                        self.ax_conn[conn_id].ack = [False, False, False]
                        self.ax_conn[conn_id].rej = [False, False]
                        disc_keys.append(conn_id)
                        snd_tr = True
                    #############################################
                    if not self.ax_conn[conn_id].snd_RRt3:
                        ind = 0
                        tmp = list(self.ax_conn[conn_id].tx)
                        for el in tmp:
                            if pac_c > self.parm_MaxBufferTX:
                                self.send_Ack(conn_id)
                                # set_t2(conn_id)
                                break
                            if len(el['typ']) > 2:
                                el['typ'][2] = self.ax_conn[conn_id].vr
                            #############################################
                            # I Frames - T1 controlled and N2 counted
                            if time.time() > t1 or t1 == 0:
                                el = dict(el)
                                if el['typ'][0] == 'I' and max_i_frame_c_f_all_conns < self.parm_max_i_frame:
                                    if not int(el['typ'][3]) in self.ax_conn[conn_id].rtt.keys():
                                        self.ax_conn[conn_id].rtt[int(el['typ'][3])] = time.time()
                                    #########################################
                                    # Set P Bit = True if I-Frame is sendet
                                    tm = el['typ']
                                    self.ax_conn[conn_id].tx[ind]['typ'] = [tm[0], True, tm[2], tm[3]]
                                    #########################################
                                    if not self.ax_conn[conn_id].ack[1]:
                                        self.ax_conn[conn_id].ack = [False, False, False]
    
                                    max_i_frame_c_f_all_conns += 1
                                    # max_f += 1
                                self.tx_buffer.append([el, self.ax_conn[conn_id].axip_client])
                                snd_tr = True
                                pac_c += 1
    
                            ######################################################
                            # On SABM Stat just send first element from TX-Buffer.
                            if self.ax_conn[conn_id].stat in ['SABM', 'DISC']:
                                break
    
                            ind += 1
                        self.send_Ack(conn_id)
                    if snd_tr:
                        self.set_t1(conn_id)
                        # set_t2(conn_id)
                        self.set_t3(conn_id)
                        self.ax_conn[conn_id].n2 = n2 + 1

            ######################################################
            # Send Discs
            for dk in disc_keys:
                self.DISC_TX(dk)
    
    #############################################################################

##################################################################################################################

##################################################################################################################
# INIT
##################################################################################################################
# conf_stations()

# for k in Stations.keys():
#     print(k)
##################################################################################################################

i = input("T = Test\n\rEnter = Go\n\r> ")
if i == 't' or i == 'T':
    #enc = ax.encode_ax25_frame(ax_test_pac[test_snd_packet])
    #print(ax.decode_ax25_frame(bytes.fromhex(enc)))
    # ERROR FRAME> print(ax.decode_ax25_frame(b'\xc0\x00\x95ki^\x11\x19\xafw%!\xc5\xf7\xb7\x88S\n\x18W\xca\xd5\xdf\x87<\xc9}\x1bW\xc3\xcd\xad\x1d<$\xa5\x15\xef\x8aXS\xc0'[2:-1]))
    print(ax.decode_ax25_frame(b'\xc0\x00\xa6\xa8\x82\xa8\xaa\xa6\xe0\x88\xb0`\xa6\x82\xaea\x13\xf0Links:  0, Con\xc0'[2:-1]))
    # b'u\x95ki^\x11\x19\xafw%!\xc5\xf7\xb7\x88S\n\x18W\xca\xd5\xdf\x87<\xc9}\x1bW\xc3\xcd\xad\x1d<$\xa5\x15\xef\x8aXS'
else:
    # Debug GUI VARS
    sel_station = ''

    os.system('clear')
    #####################################################################################
    # Init Ports and Stations ( Calls )
    #####################################################################################
    print('# Init Ports')
    n = 0
    for k in conf_ax_ports.keys():
        # Ports
        ax_ports[n] = AXPort(k)
        for stat in conf_ax_ports[k]['stat_list']:
            # Stations
            if stat.ssid:
                call_str = ax.get_call_str(stat.call, stat.ssid)
                stat.call_str = call_str
                stat.port_conf_id = k
                ax_ports[n].ax_Stations[call_str] = stat
                if stat.digi:
                    # digi_calls.append([[stat.call, stat.ssid], ax_ports[k]])
                    digi_calls[call_str] = ax_ports[n]
                if stat.bcast_srv:
                    ax_ports[n].bcast_stations.append(stat)
                    # bcast_calls[call_str] = ax_ports[n]

            else:
                #########################################
                # If no SSID make all SSIDs connectable
                for ssid in range(16):
                    call_str = ax.get_call_str(stat.call, ssid)
                    stat.call_str = call_str
                    stat.port_conf_id = k
                    ax_ports[n].ax_Stations[call_str] = stat
                    if stat.digi:
                        digi_calls[call_str] = ax_ports[n]
                    if stat.bcast_srv:
                        ax_ports[n].bcast_stations.append(stat)
                        # bcast_calls[call_str] = ax_ports[n]
        ax_ports[n].start()
        n += 1
    #####################################################################################
    # Init END !!!
    #####################################################################################

    # ax_ports[k].ax_Stations
    # kiss = AXPort(("/tmp/ptyAX5", 9600))
    kiss = ax_ports[0]

    try:
        # kiss.start()

        while not p_end:

            print("_______________________________________________")
            print('Selected Connection > ' + sel_station)
            print("_______________________________________________")

            i = input("Q  = Quit\n\r"
                      "0-5 = Send Packet\n\r"
                      "T  = Fill TX Buffer with Testdata\n\r"
                      "TB = Test Beacon (UI Packet)\n\r"
                      "P  = Print ConnStation Details\n\r"
                      "L  = Print Connected Stations\n\r"
                      "B  = Print TX-Buffer\n\r"
                      "R  = Print RX-Buffer\n\r"
                      "RD = Delete RX-Buffer\n\r"
                      "P  = Show Ports\n\r"
                      "C  = conncet\n\r"
                      "D  = Disconnect all Stations\n\r"
                      "DS = Disconnect selected Station\n\r"
                      "ST = Select Connected Stations\n\r"
                      "S  = Send Packet\n\r"
                      "SL = Send Packet Loop of 7 Pacs\n\r"
                      "\n\r> ")
            if i.upper() == 'Q':
                for k in ax_ports.keys():
                    ax_ports[k].disc_all_stations()
                # kiss.disc_all_stations()
                p_end = True
                break
            else:
                os.system('clear')

            if i.upper() == 'D':
                for k in ax_ports.keys():
                    print('############  Disc send to : ' + str(ax_ports[k].ax_conn.keys()))
                    ax_ports[k].disc_all_stations()
                # kiss.disc_all_stations()
            elif i.upper() == 'ST':
                c = 1
                print('')
                for k in kiss.ax_conn.keys():
                    print(str(c) + ' > ' + str(k))
                    c += 1
                print('~~~~~~~~~~~~~~~~~~~~~~~~~')
                print('')
                inp = input('Select Station > ')
                if inp.isdigit():
                    sel_station = list(kiss.ax_conn.keys())[int(inp) - 1]
                    os.system('clear')
                    print('Ok ..')
                    print('Selected Connection > ' + sel_station)
                else:
                    os.system('clear')
                    print('Type in Number !!')
            elif i.upper() == 'C':
                kiss.SABM_TX()
            elif i.isdigit():
                test_snd_packet = int(i)
                send_tr = True
                while test_snd_packet != -1:
                    time.sleep(0.01)
                send_tr = False
                print("Ok ..")
            elif not sel_station:
                if list(kiss.ax_conn.keys()):
                    sel_station = list(kiss.ax_conn.keys())[0]
                else:
                    print('Please connect to a Station first !')
            #################################################################
            # Station Actions
            #################################################################

            elif i.upper() == 'TB':     # Test Beacon
                kiss.tx_buffer = [ax_test_pac, ()]
                print("OK ..")

            elif i.upper() == 'S':
                inp2 = input('> ')
                inp2 += '\r'
                kiss.I_TX(sel_station, inp2)
            elif i.upper() == 'SL':
                for c in list(range(7)):
                    kiss.I_TX(sel_station, (str(c) + '\r'))
                print('Ok ..')

            elif i.upper() == 'DS':
                print('############  Disc send to : ' + str(sel_station))
                kiss.DISC_TX(sel_station)
            elif i.upper() == 'P':
                print('')
                print(str(sel_station))
                # for e in vars(ax_conn[sel_station]):
                    # print(str(e))
                print('<Connection>')
                print('\r\n'.join("%s: %s" % item for item in vars(kiss.ax_conn[sel_station]).items()))

                print('~~~~~~~~~~~~~~~~~~~~~~~~~')
                print('<CLI>')
                print('\r\n'.join("%s: %s" % item for item in vars(kiss.ax_conn[sel_station].cli).items()))

                print('<Links>')
                for k in kiss.ax_conn[sel_station].node_links.keys():
                    print('\r\n<{}>\r\n'.format(k))
                    print('\r\n'.join("%s: %s" % item for item in vars(kiss.ax_conn[sel_station].node_links[k]).items()))
                print('~~~~~~~~~~~~~~~~~~~~~~~~~')

            elif i.upper() == 'L':
                print('')
                for k in kiss.ax_conn.keys():
                    print(str(k))
                print('~~~~~~~~~~~~~~~~~~~~~~~~~')
                print('')

            elif i.upper() == 'T':
                inp = input('How many Packets should be send ? > ')
                if inp.isdigit():
                    test_data = ''
                    for c in range(int(inp)):
                        for i in range(kiss.ax_conn[sel_station].ax25PacLen):
                            test_data += str(c % 10)

                    print(str(sel_station) + ' -- send > ' + str(len(test_data)) + ' Bytes !!!!')
                    kiss.ax_conn[sel_station].tx_data += test_data
                    print('~~~~~~~~~~~~~~~~~~~~~~~~~')
                    print('')
                else:
                    print('Please enter a DIGIT ..!')
            elif i.upper() == 'B':
                for k in kiss.ax_conn.keys():
                    print(str(k) + ' tx_ctl > ' + str(kiss.ax_conn[k].tx_ctl))
                    print(str(k) + ' tx > ' + str(kiss.ax_conn[k].tx))
                    print('~~~~~~~~~~~~~~~~~~~~~~~~~')
                    print('')
            elif i.upper() == 'R':
                print(str(sel_station) + ' RX > \r\n' + kiss.ax_conn[sel_station]['rx_data'])
                print('~~~~~~~~~~~~~~~~~~~~~~~~~')
                print('')
                print('Ok ...')
            elif i.upper() == 'RD':
                for k in kiss.ax_conn.keys():
                    kiss.ax_conn[k]['rx'] = []
                print('Ok ...')

    except KeyboardInterrupt:
        kiss.disc_all_stations()
        p_end = True
        print("Ende ..")
