# TODO Confirm Algo haut nicht hin
import ax25enc as ax
import threading
import time
import os
import monitor
import serial

ser_port = "/tmp/ptyAX5"
ser_baud = 1200
MyCallStr1 = 'MD3SAW-11'            # Call for outgoing connects
MyCallStr2 = ['MD3SAW-8', 'MD3SAW-9', 'MD3SAW-10']          # Calls for requests

MyCall = ax.get_ssid(MyCallStr1)
Calls = [MyCallStr1] + MyCallStr2
# TEST DATA
ax_test_pac = [{
    'call': ['MD2SAW', 8],
    'dest': ['APRS', 0],
    'via': [['DX0SAW', 0, False]],
    'out': '< TEST fm MD2SAW ( JO52NU ) >',
    'typ': ['UI', True],
    'cmd': True,
    'pid': 6
},
{   # 1
    'call': ['MD2SAW', 8],
    'dest': ['DX0SAW', 0],
    'via': [['CB0SAW', 0, True]],
    'out': '',
    'typ': ['UA', True],
    'cmd': True,
    'pid': 6
},
{   # 2
    'call': ['MD2SAW', 8],
    'dest': ['DNX527', 0],
    'via': [],
    'out': 'TEST',
    'typ': ['TEST', True],
    'cmd': True,
    'pid': 6
},
{   # 3
    'call': ['MD2SAW', 8],
    'dest': ['DX0SAW', 0],
    'via': [],
    'out': '< TEST fm MD2SAW ( JO52NU ) >',
    'typ': ['UI', True],
    'cmd': True,
    'pid': 6
}]
'''
pid
1 = yy01yyyy AX.25 Layer 3 implementiert.
2 = yy10yyyy AX.25 Layer 3 implementiert.
3 = 11001100 Internet Protokoll Datagramm Layer 3 implementiert.
4 = 11001101 Adress Resolution Protokoll Layer 3 implementiert.
5 = 11001111 NET/ROM Protokoll Layer 3/4 implementiert.
6 = 11110000 Kein Layer 3 implementiert.
7 = 11111111 Fluchtsymbol, das nächste Byte enthält weitere Layer 3 Protokoll Informationen.
'''
# TEST DATA
# TESTING and DEBUGGING
debug = monitor.debug
test_snd_packet = -1
# Globals
ax25MaxBufferTX = 20                    # Max Frames to send from Buffer
ax25MaxFrame = 3                        # Max (I) Frames
ax25TXD = 50                            # TX Delay for RTT Calculation
# ax25MaxTXtime = 30
parm_max_i_frame = 14                   # Max I-Frame (all connections) per Cycle
parm_N2 = 5                             # Max Try    Default 20
parm_baud = ser_baud                    # Baud for RTT Calculation
parm_T2 = 4000 / (parm_baud / 100)      # T2 (Response Delay Timer) Default: 2888 / (parm_baud / 100)
parm_T0 = 2888 / (parm_baud / 100)      # T0 (Response Delay Timer) activated if data come in to prev resp. to early
# parm_IRTT = 550                       # Initial-Round-Trip-Time
parm_IRTT = (parm_T2 + ax25TXD) * 2     # Initial-Round-Trip-Time (Auto Parm) (bei DAMA wird T2*2 genommen)/NO DAMA YET
# ax25MaxRetry = 20

timer_T0 = 0
tx_buffer = []
rx_buffer = {}
p_end, send_tr = False, False
ax_conn = {
    # 'addrStr': {
    #    'tx': [],
    #    'rx': [],
    #    't1': 0.0,
    #    'nr': 0,
    #    'ns': 0,
    #    'pf': True,
    # }
}


def get_conn_item():
    return {
        'call': [MyCall[0], MyCall[1]],
        'dest': ['', 0],
        'via': [],
        'tx': [],
        'tx_ctl': [],
        'rx': [],       # Not needed till yet
        'rx_data': '',
        'stat': '',
        'vs': 0,
        'vr': 0,
        'noAck': [],
        'Ack': False,
        'REJ': False,
        'T1': 0,
        'T2': 0,
        'T3': 0.0,
        'N2': 1,
        'max_frame_c': 1

    }


def get_tx_packet_item(inp=None, conn_id=None):
    if inp:
        # print('INP !!!! > ' + str(inp))
        via = []
        tm = inp['via']
        tm.reverse()
        for el in tm:
            via.append([el[0], el[1], False])
        return {
            'call': inp['TO'],
            'dest': inp['FROM'],
            'via': via,
            'out': '',
            'typ': [],                  # ['SABM', True, 0],   # Type, P/F, N(R), N(S)
            'cmd': False,
            'pid': 6,
            'nr': 0,
            'ns': 0

        }
    elif conn_id:
        return {
            'call': ax_conn[conn_id]['call'],
            'dest': ax_conn[conn_id]['dest'],
            'via': ax_conn[conn_id]['via'],
            'out': '',
            'typ': [],                 # ['SABM', True, 0],  # Type, P/F, N(R), N(S)
            'cmd': False,
            'pid': 6,
            'nr': 0,
            'ns': 0

        }


def set_t1(conn_id):
    ns = ax_conn[conn_id]['N2']
    srtt = parm_IRTT
    if ax_conn[conn_id]['via']:
        srtt = (len(ax_conn[conn_id]['via']) * 2 + 1) * parm_IRTT
    if ns > 3:
        ax_conn[conn_id]['T1'] = ((srtt * (ns + 4)) / 100) + time.time()
    else:
        ax_conn[conn_id]['T1'] = ((srtt * 3) / 100) + time.time()


def set_t2(conn_id):
    ax_conn[conn_id]['T2'] = parm_T2 / 100 + time.time()


def set_t0():
    global timer_T0
    timer_T0 = parm_T0 / 100 + time.time()


def handle_rx(inp):
    set_t0()
    monitor.monitor(inp[1])
    conn_id = ax.reverse_addr_str(inp[0])
    if inp[0].split(':')[0] in Calls:
        if inp[1]['via'] and all(not el[2] for el in inp[1]['via']):
            monitor.debug_out('###### Data In not Digipeated yet !!########')
            monitor.debug_out('')
        else:
            # Connected Stations
            if conn_id in ax_conn.keys():
                handle_rx_fm_conn(conn_id, inp[1])
            #########################################################################################
            # !!! Same Action underneath !!! inp[1]['ctl']['hex'] not in [0x3f, 0x7f, 0x53, 0x13] !?!
            #########################################################################################
            # Incoming UI
            # elif inp[1]['ctl']['hex'] == 0x13:                      # UI p/f True
            #     DM_TX(inp[1])                                       # Confirm UI ??? TODO DM or UA ?
            #########################################################################################
            # elif inp[1]['ctl']['hex'] not in [0x3f, 0x7f, 0x53, 0x13]:   # NOT SABM, SABME, DISC, UI p/f True
            #     DM_TX(inp[1])
            # Incoming connection SABM or SABME
            elif inp[1]['ctl']['hex'] in [0x3f, 0x7f]:              # SABM or SABME p/f True
                SABM_RX(conn_id, inp=inp[1])                        # Handle connect Request
            # Incoming DISC
            elif inp[1]['ctl']['hex'] == 0x53:                      # DISC p/f True
                DISC_RX(conn_id, inp=inp[1])                        # Handle DISC Request
            else:
                DM_TX(inp[1])


def handle_rx_fm_conn(conn_id, inp):
    monitor.debug_out('')
    monitor.debug_out('###### Conn Data In ########')
    monitor.debug_out(conn_id)
    monitor.debug_out('IN> ' + str(inp))
    print('Pac fm connection incoming... ' + conn_id)
    print('IN> ' + str(inp['FROM']) + ' ' + str(inp['TO']) + ' ' + str(inp['via']) + ' ' + str(inp['ctl']))
    #################################################
    # DEBUG !!   ?? Alle Pakete speichern ??
    ax_conn[conn_id]['rx'].append(inp)
    #################################################
    if inp['ctl']['hex'] == 0x73:                   # UA p/f True
        UA_RX(conn_id)
    #################################################
    elif inp['ctl']['hex'] == 0x1F:                 # DM p/f True
        DM_RX(conn_id)
    #################################################
    elif inp['ctl']['flag'] == 'I':                 # I
        I_RX(conn_id, inp)
    #################################################
    elif inp['ctl']['flag'] == 'RR':                # RR
        RR_RX(conn_id, inp)
    #################################################
    elif inp['ctl']['flag'] == 'REJ':                # REJ
        REJ_RX(conn_id, inp)

    # monitor.debug_out(ax_conn[conn_id])
    monitor.debug_out('#### Conn Data In END ######')
    monitor.debug_out('')
    if conn_id in ax_conn.keys():
        print('~~~~~~RX IN~~~~~~~~~~~~~~')
        for e in ax_conn[conn_id].keys():
            print(str(e) + ' > ' + str(ax_conn[conn_id][e]))
        print('~~~~~~RX IN~~~~~~~~~~~~~~')
        print('')


def SABM_TX():
    os.system('clear')
    dest = input('Enter Dest. Call\r\n> ').upper()
    conn_id = dest + ':' + ax.get_call_str(MyCall[0], MyCall[1])
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

    if conn_id not in ax_conn.keys():
        ax_conn[conn_id] = get_conn_item()
        ax_conn[conn_id]['dest'] = [dest[0], dest[1]]
        call = ax_conn[conn_id]['call']
        ax_conn[conn_id]['call'] = [call[0], call[1]]
        ax_conn[conn_id]['via'] = via_list
        ax_conn[conn_id]['stat'] = 'SABM'
        tx_pack = get_tx_packet_item(conn_id=conn_id)
        tx_pack['typ'] = ['SABM', True]
        tx_pack['cmd'] = True
        ax_conn[conn_id]['tx'] = [tx_pack]
        # set_t1(conn_id)
        print(ax_conn)
        print("OK ..")
    else:
        print('Busy !! There is still a connection to this Station !!!')
        print('')


def SABM_RX(conn_id, inp):
    monitor.debug_out('')
    monitor.debug_out('#### Connect Request ..... ######')
    monitor.debug_out(conn_id)
    print('#### Connect Request fm ' + inp['FROM'][0])
    print(conn_id)
    # Setup NEW conn Data
    if conn_id not in ax_conn:
        setup_new_conn(conn_id, inp)

    # Answering Conn Req (UA).
    ax_conn[conn_id]['tx_ctl'].append(UA_frm(inp))
    # Set State to Receive Ready
    ax_conn[conn_id]['stat'] = 'RR'

    #############################################################################
    # Verb. wird zurueck gesetzt nach empfangen eines SABM.
    # evtl. bestehenden TX-Buffer speichern um mit der Uebertragung fortzufahren.
    ax_conn[conn_id]['vs'], ax_conn[conn_id]['vr'] = 0, 0
    ax_conn[conn_id]['N2'] = 1
    ax_conn[conn_id]['tx'] = []
    #############################################################################

    #####################################################################################
    # C-Text
    # ax_conn[conn_id]['tx'].append(I_frm(conn_id, '############# TEST ###############'))
    I_TX(conn_id, '############# TEST ###############')
    #####################################################################################

    monitor.debug_out(ax_conn[conn_id])
    monitor.debug_out('#### Incoming Conn Data In END ######')
    monitor.debug_out('')


def confirm_I_Frames(conn_id, inp):
    # conf_vs = []
    '''
    ######################################################################
    # Confirm multiple Frames
    # TODO Testing with multiple Frames
    # TODO Debugging !!!
    if ax_conn[conn_id]['vs'] > inp['ctl']['nr']:
        for i in list(range(inp['ctl']['nr'], 8)):
            conf_vs.append(i)
        for i in list(range(0, (ax_conn[conn_id]['vs']))):
            conf_vs.append(i)
    elif inp['ctl']['nr'] > ax_conn[conn_id]['vs']:
        for i in list(range(ax_conn[conn_id]['vs'], (inp['ctl']['nr']))):
            conf_vs.append(i)
    else:
        conf_vs.append(inp['ctl']['nr'])
    ######################################################################
    '''
    if ax_conn[conn_id]['noAck']:
        tmp_ack = ax_conn[conn_id]['noAck'][:ax_conn[conn_id]['noAck'].index(inp['ctl']['nr'] - 1) + 1]

        print('### CONF inp > ' + str(inp['ctl']['nr']))
        print('### CONF ax_conn > ' + str(ax_conn[conn_id]['vr']))
        ax_conn[conn_id]['vs'] = inp['ctl']['nr']
        ###########################################
        # Delete confirmed I Frames from TX- Buffer
        tmp = ax_conn[conn_id]['tx']
        print('### conf. VS > ' + str(ax_conn[conn_id]['noAck']))
        print('### CONF TX Buffer > ' + str(ax_conn[conn_id]['tx']))
        # Delete all VS < VR
        for el in tmp:
            if el['typ'][0] == 'I' and (el['typ'][3] in tmp_ack):
                ax_conn[conn_id]['noAck'].remove(el['typ'][3])
                ax_conn[conn_id]['tx'].remove(el)
                ax_conn[conn_id]['max_frame_c'] -= 1
        ###########################################
    ax_conn[conn_id]['N2'] = 1


def RR_RX(conn_id, inp):
    # Hold connection
    if inp['ctl']['pf']:
        ax_conn[conn_id]['vs'] = inp['ctl']['nr']
        ax_conn[conn_id]['N2'] = 1
    if inp['ctl']['cmd']:
        ax_conn[conn_id]['tx_ctl'].append(RR_frm(conn_id, True, False))
        ax_conn[conn_id]['T1'] = 0

    # Confirm I Frames
    elif not inp['ctl']['cmd'] and not inp['ctl']['pf']:
        confirm_I_Frames(conn_id, inp)
        ax_conn[conn_id]['T1'] = 0

    set_t2(conn_id)


def RR_TX_T3(conn_id):      # TODO !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    # T3 is done ( Hold connection )
    ax_conn[conn_id]['tx'].append(RR_frm(conn_id, True, True))


def REJ_RX(conn_id, inp):
    confirm_I_Frames(conn_id, inp)
    set_t2(conn_id)
    ax_conn[conn_id]['T1'] = 0
    print('###### REJ_RX > ' + str(inp))


def REJ_TX(conn_id):
    if not ax_conn[conn_id]['REJ']:
        ax_conn[conn_id]['tx_ctl'].append(REJ_frm(conn_id, False, False))
        ax_conn[conn_id]['REJ'] = True
        set_t2(conn_id)
        ax_conn[conn_id]['T1'] = 0
        print('###### REJ_TX > ' + str(ax_conn[conn_id]['tx_ctl']))


def I_RX(conn_id, inp):
    if inp['ctl']['ns'] == ax_conn[conn_id]['vr']:
        ax_conn[conn_id]['rx_data'] += str(inp['data'])
        ax_conn[conn_id]['vr'] = (1 + ax_conn[conn_id]['vr']) % 8
        ax_conn[conn_id]['Ack'] = True
        ax_conn[conn_id]['T1'] = 0
        set_t2(conn_id)
        confirm_I_Frames(conn_id, inp)
        print('###### I-Frame > ' + str(inp['data']))
    else:
        REJ_TX(conn_id)
        print('###### REJ_TX inp > ' + str(inp))


def I_TX(conn_id, data=''):
    if ax_conn[conn_id]['stat'] != 'RR':    # TODO State of Receiver
        return False
    # TODO CHECK !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    if len(ax_conn[conn_id]['noAck']) > 7:
        return False
    ax_conn[conn_id]['tx'].append(I_frm(conn_id, data))
    ax_conn[conn_id]['noAck'].append(ax_conn[conn_id]['vs'])
    ax_conn[conn_id]['vs'] = (1 + ax_conn[conn_id]['vs']) % 8
    ax_conn[conn_id]['T1'] = 0
    ax_conn[conn_id]['N2'] = 1
    return True


def DM_TX(inp, pf_bit=True):    # !!!!!!!!!!! Dummy. !! Not Tested  !!!!!!!!!!!!!
    tx_buffer.append(DM_frm(inp, pf_bit))
    # Will send if Station is Busy or can't request SABM or receive any other Pac as SABM, UI
    # Also will send to confirm a UI Pac if station is not connected


def DM_RX(conn_id):
    if ax_conn[conn_id]['stat'] == 'SABM':
        print('#### Called Station is Busy ..... ######')
    del ax_conn[conn_id]


def UA_RX(conn_id):
    ax_conn[conn_id]['N2'] = 1
    ax_conn[conn_id]['T1'] = 0
    # set_t1(conn_id)
    ax_conn[conn_id]['vs'], ax_conn[conn_id]['vr'] = 0, 0
    if ax_conn[conn_id]['stat'] == 'SABM':
        ax_conn[conn_id]['tx'].pop(0)           # Not lucky with that solution TODO
        ax_conn[conn_id]['stat'] = 'RR'
        monitor.debug_out('#### Connection established ..... ######')
        monitor.debug_out('ax_conn[id][tx]> ' + str(ax_conn[conn_id]['tx']))
        print('#### Connection established ..... ######')
    elif ax_conn[conn_id]['stat'] == 'DISC':
        monitor.debug_out('#### Disc confirmed ..... ######')
        monitor.debug_out('ax_conn[id][tx]> ' + str(ax_conn[conn_id]['tx']))
        print('#### Disc confirmed ..... ######')
        del ax_conn[conn_id]


def DISC_TX(conn_id):
    monitor.debug_out('')
    monitor.debug_out('#### DISCO Send ..... ######')
    monitor.debug_out(conn_id)
    print('#### DISCO Send to ' + ax_conn[conn_id]['dest'][0])
    print(conn_id)
    # Answering DISC
    # tx_buffer.append(DISC_frm(conn_id))
    if ax_conn[conn_id]['stat'] == 'RR':
        ax_conn[conn_id]['stat'] = 'DISC'
        ax_conn[conn_id]['N2'] = 1
        # set_t1(conn_id)
        ax_conn[conn_id]['tx'] = [DISC_frm(conn_id)]
    elif ax_conn[conn_id]['stat'] == 'SABM':
        tx_buffer.append(DISC_frm(conn_id))
        del ax_conn[conn_id]


def DISC_RX(conn_id, inp):
    monitor.debug_out('')
    monitor.debug_out('#### DISCO Request ..... ######')
    monitor.debug_out(conn_id)
    print('#### DISCO Request fm ' + inp['FROM'][0])
    print(conn_id)
    # Answering DISC
    if conn_id in ax_conn.keys():
        tx_buffer.append(UA_frm(inp))       # UA_TX
        del ax_conn[conn_id]
    else:
        tx_buffer.append(DM_frm(inp))


def setup_new_conn(conn_id, inp_data):
    ax_conn[conn_id] = get_conn_item()
    from_call, to_call = inp_data['FROM'], inp_data['TO']
    ax_conn[conn_id]['dest'] = [from_call[0], from_call[1]]
    ax_conn[conn_id]['call'] = [to_call[0], to_call[1]]
    for el in inp_data['via']:
        ax_conn[conn_id]['via'].append([el[0], el[1], False])
    ax_conn[conn_id]['via'].reverse()
    #######################################
    # Debug !!!!
    ax_conn[conn_id]['rx'] = [inp_data]
    #######################################

#######################################################################


def UA_frm(inp):
    # Answering Conn Req. or Disc Frame
    pac = get_tx_packet_item(inp=inp)
    pac['typ'] = ('UA', inp['ctl']['pf'])
    pac['cmd'] = False
    return pac


def I_frm(conn_id, data=''):
    pac = get_tx_packet_item(conn_id=conn_id)
    # VR will be set again just before sending !!!
    pac['typ'] = ['I', False, ax_conn[conn_id]['vr'], ax_conn[conn_id]['vs']]
    pac['cmd'] = True
    pac['pid'] = 6
    pac['out'] = data
    return pac


def DM_frm(inp, f_bit=None):
    # Answering DISC
    if f_bit is None:
        f_bit = inp['ctl']['pf']
    pac = get_tx_packet_item(inp=inp)
    pac['typ'] = ['DM', f_bit]
    pac['cmd'] = False
    return pac


def DISC_frm(conn_id):
    # DISC Frame
    pac = get_tx_packet_item(conn_id=conn_id)
    pac['typ'] = ['DISC', True]
    pac['cmd'] = True
    return pac


def RR_frm(conn_id, pf_bit=False, cmd=False):
    # RR Frame
    pac = get_tx_packet_item(conn_id=conn_id)
    pac['typ'] = ['RR', pf_bit, ax_conn[conn_id]['vr']]
    pac['cmd'] = cmd
    print('')
    print('######## Send RR >')
    print(pac)
    print('')
    print('~~~~~~Send RR~~~~~~~~~~~~')
    for e in ax_conn[conn_id].keys():
        print(str(e) + ' > ' + str(ax_conn[conn_id][e]))
    print('~~~~~~Send RR~~~~~~~~~~~~')
    print('')
    return pac


def REJ_frm(conn_id, pf_bit=False, cmd=False):
    # REJ Frame
    pac = get_tx_packet_item(conn_id=conn_id)
    pac['typ'] = ['REJ', pf_bit, ax_conn[conn_id]['vr']]
    pac['cmd'] = cmd
    print('')
    print('######## Send REJ >')
    print(pac)
    print('')
    return pac


#############################################################################


def disc_all_stations():
    tmp = ax_conn.keys()
    for conn_id in list(tmp):
        DISC_TX(conn_id)

#############################################################################


def handle_tx():
    max_i_frame_c_f_all_conns = 0
    disc_keys = []
    pac_c = 0

    def send_Ack(conn_id):
        ######################################################
        # Send Ack if not sendet with I Frame
        if ax_conn[conn_id]['Ack']:
            tx_buffer.append(RR_frm(conn_id, False, False))
            ax_conn[conn_id]['Ack'] = False

    for conn_id in ax_conn.keys():
        if (time.time() > ax_conn[conn_id]['T2'] or ax_conn[conn_id]['T2'] == 0)\
                and (time.time() > timer_T0 or timer_T0 == 0):
            if pac_c > ax25MaxBufferTX:
                send_Ack(conn_id)
                break
            #############################################
            # CTL Frames ( Not T1 controlled ) just T2
            tx_ctl = ax_conn[conn_id]['tx_ctl']
            for el in tx_ctl:
                if pac_c > ax25MaxBufferTX:
                    send_Ack(conn_id)
                    break
                tx_buffer.append(el)
                ax_conn[conn_id]['tx_ctl'].pop(0)
                pac_c += 1
            #############################################
            snd_tr = False
            tmp = ax_conn[conn_id]['tx']
            for el in tmp:
                if pac_c > ax25MaxBufferTX:
                    send_Ack(conn_id)
                    break
                #############################################
                # Timeout and N2 out
                if ax_conn[conn_id]['N2'] > parm_N2 and time.time() > ax_conn[conn_id]['T1'] != 0:
                    # DISC ???? TODO Testing
                    monitor.debug_out('#### Connection failure ..... ######' + conn_id)
                    print('#### Connection failure ..... ######' + conn_id)
                    disc_keys.append(conn_id)
                    break
                # if el is RR Frame
                # elif .......
                #############################################
                # I Frames - T1 controlled and N2 counted
                if time.time() > ax_conn[conn_id]['T1'] or ax_conn[conn_id]['T1'] == 0:
                    if el['typ'][0] == 'I' \
                            and ax_conn[conn_id]['max_frame_c'] < ax25MaxFrame \
                            and max_i_frame_c_f_all_conns < parm_max_i_frame:
                        el['typ'][2] = ax_conn[conn_id]['vr']
                        ax_conn[conn_id]['max_frame_c'] += 1
                        max_i_frame_c_f_all_conns += 1
                        tx_buffer.append(el)
                        snd_tr = True
                        ax_conn[conn_id]['Ack'] = False
                    else:
                        tx_buffer.append(el)
                        snd_tr = True
                    pac_c += 1

                ######################################################
                # On SABM Stat just send first element from TX-Buffer.
                if ax_conn[conn_id]['stat'] in ['SABM', 'DISC']:
                    break
            send_Ack(conn_id)
            # TODO Check !!
            if snd_tr:
                set_t1(conn_id)
                set_t2(conn_id)
                # ax_conn[conn_id]['T2'] = 0
                ax_conn[conn_id]['N2'] += 1

    ######################################################
    # Send Discs
    for dk in disc_keys:
        DISC_TX(dk)


        '''
        for el in tmp:
            tx_buffer.append(el)
            ax_conn[ke]['tx'] = ax_conn[ke]['tx'][1:]
        '''
#############################################################################


def read_kiss():
    global test_snd_packet, tx_buffer
    pack = b''
    ser = serial.Serial(ser_port, ser_baud, timeout=1)
    while not p_end:
        b = ser.read()
        pack += b
        if b:           # RX ###################################################################################
            if ax.conv_hex(b[0]) == 'c0' and len(pack) > 2:
                monitor.debug_out("----------------Kiss Data IN ----------------------")
                inp = ax.decode_ax25_frame(pack[2:-1])      # DEKISS
                if inp:
                    handle_rx(inp)
                    '''
                    ############ TEST ##############
                    if inp[0] in rx_buffer.keys():
                        rx_buffer[inp[0]].append(inp[1])
                    else:
                        rx_buffer[inp[0]] = [inp[1]]
                    ########## TEST ENDE ###########
                    '''
                    monitor.debug_out('################ DEC END ##############################')
                else:
                    monitor.debug_out("ERROR Dec> " + str(inp), True)
                monitor.debug_out("_________________________________________________")
                pack = b''

        handle_tx()          # TX #############################################################
        if tx_buffer:
            monitor.debug_out(ax_conn)
            c = 0
            while tx_buffer and c < ax25MaxBufferTX:
                enc = ax.encode_ax25_frame(tx_buffer[0])
                ax.send_kiss(ser, enc)
                mon = ax.decode_ax25_frame(bytes.fromhex(enc))
                handle_rx(mon)              # Echo TX in Monitor
                monitor.debug_out("Out> " + str(mon))
                tx_buffer = tx_buffer[1:]
                c += 1

        # TESTING
        if test_snd_packet != -1 and send_tr:
            ax.send_kiss(ser, ax.encode_ax25_frame(ax_test_pac[test_snd_packet]))
            test_snd_packet = -1
            while send_tr:
                time.sleep(0.01)


##################################################################################################################

i = input("T = Test\n\rEnter = Go\n\r> ")
if i == 't' or i == 'T':
    #enc = ax.encode_ax25_frame(ax_test_pac[test_snd_packet])
    #print(ax.decode_ax25_frame(bytes.fromhex(enc)))
    # ERROR FRAME> print(ax.decode_ax25_frame(b'\xc0\x00\x95ki^\x11\x19\xafw%!\xc5\xf7\xb7\x88S\n\x18W\xca\xd5\xdf\x87<\xc9}\x1bW\xc3\xcd\xad\x1d<$\xa5\x15\xef\x8aXS\xc0'[2:-1]))
    print(ax.decode_ax25_frame(b'\xc0\x00\xa6\xa8\x82\xa8\xaa\xa6\xe0\x88\xb0`\xa6\x82\xaea\x13\xf0Links:  0, Con\xc0'[2:-1]))
    # b'u\x95ki^\x11\x19\xafw%!\xc5\xf7\xb7\x88S\n\x18W\xca\xd5\xdf\x87<\xc9}\x1bW\xc3\xcd\xad\x1d<$\xa5\x15\xef\x8aXS'
    pass
else:
    os.system('clear')
    try:
        th = threading.Thread(target=read_kiss).start()
        while not p_end:
            print("_______________________________________________")
            print('')
            i = input("Q = Quit\n\r"
                      "0-5 = Send Packet\n\r"
                      "T = Fill TX Buffer with Testdata\n\r"
                      "P = Print ConnStation Details\n\r"
                      "L = Print Connected Stations\n\r"
                      "B = Print TX-Buffer\n\r"
                      "R = Print RX-Buffer\n\r"
                      "RD= Delete RX-Buffer\n\r"
                      "C = conncet\n\r"
                      "D = Disconnect all Stations\n\r"
                      "S = Send Packet\n\r"
                      "\n\r> ")
            if i.upper() == 'Q':
                disc_all_stations()
                p_end = True
                break
            else:
                os.system('clear')

            if i.upper() == 'T':
                tx_buffer = ax_test_pac
                print("OK ..")
            elif i.upper() == 'C':
                SABM_TX()
            elif i.upper() == 'S':
                inp2 = input('> ')
                inp2 += '\r'
                I_TX(list(ax_conn.keys())[0], inp2)
            elif i.upper() == 'D':
                print('############  Disc send to : ' + str(ax_conn.keys()))
                disc_all_stations()
            elif i.upper() == 'P':
                for k in ax_conn.keys():
                    print('')
                    print(str(k))
                    for e in ax_conn[k].keys():
                        print(str(e) + ' > ' + str(ax_conn[k][e]))
                    print('~~~~~~~~~~~~~~~~~~~~~~~~~')
                    print('')
            elif i.upper() == 'L':
                for k in ax_conn.keys():
                    print('')
                    print(str(k))
                    print('~~~~~~~~~~~~~~~~~~~~~~~~~')
            elif i.upper() == 'T':
                for k in ax_conn.keys():
                    print(str(k) + ' > ' + str(ax_conn[k]['tx']))
                    print('~~~~~~~~~~~~~~~~~~~~~~~~~')
                    print('')
            elif i.upper() == 'B':
                for k in ax_conn.keys():
                    print(str(k) + ' tx_ctl > ' + str(ax_conn[k]['tx_ctl']))
                    print(str(k) + ' tx > ' + str(ax_conn[k]['tx']))
                    print('~~~~~~~~~~~~~~~~~~~~~~~~~')
                    print('')
            elif i.upper() == 'R':
                for k in ax_conn.keys():
                    for d in ax_conn[k]['rx']:
                        print(str(k) + ' RX > ' + str(d))
                    print('~~~~~~~~~~~~~~~~~~~~~~~~~')
                    print('')
                print('Ok ...')
            elif i.upper() == 'RD':
                for k in ax_conn.keys():
                    ax_conn[k]['rx'] = []
                print('Ok ...')
            elif i.isdigit():
                test_snd_packet = int(i)
                send_tr = True
                while test_snd_packet != -1:
                    time.sleep(0.01)
                send_tr = False
                print("Ok ..")

    except KeyboardInterrupt:
        disc_all_stations()
        p_end = True
        print("Ende ..")
