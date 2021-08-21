from config import *
import os
import time
import serial
import threading
import monitor


# TESTING and DEBUGGING
debug = monitor.debug
test_snd_packet = -1

# Globals
timer_T0 = 0
tx_buffer = []
p_end, send_tr = False, False
ax_conn = {
    # 'addrStr': {
    #      ConnObj
    # }
}


def get_tx_packet_item(rx_inp=None, conn_id=None):
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
            'call': ax_conn[conn_id].call,
            'dest': ax_conn[conn_id].dest,
            'via': ax_conn[conn_id].via,
            'out': '',
            'typ': [],                 # ['SABM', True, 0],  # Type, P/F, N(R), N(S)
            'cmd': False,
            'pid': 6,

        }


def set_t1(conn_id):
    ns = ax_conn[conn_id].n2
    srtt = float(ax_conn[conn_id].parm_IRTT)
    if ax_conn[conn_id].via:
        srtt = int((len(ax_conn[conn_id].via) * 2 + 1) * ax_conn[conn_id].parm_IRTT)
    if ns > 3:
        ax_conn[conn_id].t1 = float(((srtt * (ns + 4)) / 100) + time.time())
    else:
        ax_conn[conn_id].t1 = float(((srtt * 3) / 100) + time.time())


def set_t2(conn_id):
    ax_conn[conn_id].t2 = float(ax_conn[conn_id].parm_T2 / 100 + time.time())


def set_t3(conn_id):
    ax_conn[conn_id].t3 = float(ax_conn[conn_id].ax25T3 / 100 + time.time())


def set_t0():
    global timer_T0
    timer_T0 = float(parm_T0 / 100 + time.time())


def tx_data2tx_buffer(conn_id):
    data = str(ax_conn[conn_id].tx_data)
    paclen = int(ax_conn[conn_id].ax25PacLen)
    if data:
        free_txbuff = 7 - len(ax_conn[conn_id].noAck)
        for i in range(free_txbuff):
            if data:
                if I_TX(conn_id, data[:paclen]):
                    data = data[paclen:]
                else:
                    break
            else:
                break

        ax_conn[conn_id].tx_data = data


def handle_rx(rx_inp):
    monitor.monitor(rx_inp[1])
    conn_id = ax.reverse_addr_str(rx_inp[0])
    own_call = rx_inp[0].split(':')[0]
    if own_call in Stations.keys():
        '''
        if rx_inp[1]['via'] and all(not el[2] for el in rx_inp[1]['via']):
            monitor.debug_out('###### Data In not Digipeated yet !!########')
            monitor.debug_out('')
        '''
        ############################################
        # Check if Packet run through all Digis
        if not rx_inp[1]['via'] or all(el[2] for el in rx_inp[1]['via']):
            # Incoming DISC
            if rx_inp[1]['ctl']['hex'] == 0x53:     # DISC p/f True
                DISC_RX(conn_id, rx_inp=rx_inp[1])  # Handle DISC Request
            #########################################################################################
            # Incoming UI
            # elif inp[1]['ctl']['hex'] == 0x13:                      # UI p/f True
            #     DM_TX(inp[1])                                       # Confirm UI ??? TODO DM or UA ?
            #########################################################################################
            # Incoming connection SABM or SABME
            elif rx_inp[1]['ctl']['hex'] in [0x3f, 0x7f]:              # SABM or SABME p/f True
                SABM_RX(conn_id, rx_inp=rx_inp[1], owncall=own_call)   # Handle connect Request
            # Connected Stations
            elif conn_id in ax_conn.keys():
                handle_rx_fm_conn(conn_id, rx_inp[1])
            else:
                DM_TX(rx_inp[1])
    else:
        ################################################
        # DIGI
        for v in rx_inp[1]['via']:
            if not v[2] and [v[0], v[1]] in digi_calls:
                v[2] = True
                print('DIGI > ' + str(rx_inp[0]))
                DigiPeating(rx_inp[1])
                break
            elif not v[2] and [v[0], v[1]] not in digi_calls:
                break


def handle_rx_fm_conn(conn_id, rx_inp):
    monitor.debug_out('')
    monitor.debug_out('###### Conn Data In ########')
    monitor.debug_out(conn_id)
    monitor.debug_out('IN> ' + str(rx_inp))
    set_t3(conn_id)
    set_t2(conn_id)
    print('Pac fm connection incoming... ' + conn_id)
    print('IN> ' + str(rx_inp['FROM']) + ' ' + str(rx_inp['TO']) + ' ' + str(rx_inp['via']) + ' ' + str(rx_inp['ctl']))
    #################################################
    if rx_inp['ctl']['hex'] == 0x73:                   # UA p/f True
        UA_RX(conn_id)
    #################################################
    elif rx_inp['ctl']['hex'] == 0x1F:                 # DM p/f True
        DM_RX(conn_id)
    #################################################
    elif rx_inp['ctl']['flag'] == 'I':                 # I
        I_RX(conn_id, rx_inp)
    #################################################
    elif rx_inp['ctl']['flag'] == 'RR':                # RR
        RR_RX(conn_id, rx_inp)
    #################################################
    elif rx_inp['ctl']['flag'] == 'REJ':                # REJ
        REJ_RX(conn_id, rx_inp)

    monitor.debug_out('#### Conn Data In END ######')
    monitor.debug_out('')
    print('~~~~~~RX IN~~~~~~~~~~~~~~')
    print('')


def DigiPeating(rx_inp):
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
    tx_buffer.append(pac)
    # TODO ######### tx_buffer.append(pac) Just for testing


def SABM_TX():
    os.system('clear')
    dest = input('Enter Dest. Call\r\n> ').upper()
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

    if conn_id not in ax_conn.keys():
        ax_conn[conn_id] = DefaultParam()
        ax_conn[conn_id].dest = [dest[0], dest[1]]
        ax_conn[conn_id].via = via_list
        ax_conn[conn_id].stat = 'SABM'
        tx_pack = get_tx_packet_item(conn_id=conn_id)
        tx_pack['typ'] = ['SABM', True]
        tx_pack['cmd'] = True
        ax_conn[conn_id].tx = [tx_pack]
        # set_t1(conn_id)
        set_t3(conn_id)
        print(ax_conn)
        print("OK ..")
    else:
        print('Busy !! There is still a connection to this Station !!!')
        print('')


def SABM_RX(conn_id, rx_inp, owncall):
    monitor.debug_out('')
    monitor.debug_out('#### Connect Request fm ' + rx_inp['FROM'][0])
    monitor.debug_out(conn_id)
    monitor.debug_out('')
    print('#### Connect Request fm ' + rx_inp['FROM'][0])
    print(conn_id)
    # Setup NEW conn Data
    if conn_id not in ax_conn:
        setup_new_conn(conn_id, rx_inp, owncall)
    #############################################################################
    # Verb. wird zurueck gesetzt nach empfangen eines SABM.
    # evtl. bestehenden TX-Buffer speichern um mit der Uebertragung fortzufahren.
    ax_conn[conn_id].vs, ax_conn[conn_id].vr = 0, 0
    ax_conn[conn_id].t1 = 0
    ax_conn[conn_id].n2 = 1
    ax_conn[conn_id].tx = []
    # Set State to Receive Ready
    ax_conn[conn_id].stat = 'RR'
    # Answering Conn Req (UA).
    ax_conn[conn_id].tx_ctl = [UA_frm(rx_inp)]
    #############################################################################

    #####################################################################################
    # C-Text
    ax_conn[conn_id].tx_data += ax_conn[conn_id].ctext
    #####################################################################################


def confirm_I_Frames(conn_id, rx_inp):
    #####################################################################################
    # Python is fucking up with Arrays in For Loop. It jumps over Elements. Why ??
    # ??? Because of Threading and global Vars ???
    no_ack = list(ax_conn[conn_id].noAck)             # Wie waere es mit Modulo Restklassen ??
    tmp_tx_buff = list(ax_conn[conn_id].tx)
    if no_ack:
        ind_val = (rx_inp['ctl']['nr'] - 1) % 8
        if ind_val in no_ack:
            ind = no_ack.index(ind_val) + 1
            tmp_ack = no_ack[:ind]
            print('### conf. VS > ' + str(no_ack))
            print('### conf. tmp_Ack > ' + str(tmp_ack))
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
            ax_conn[conn_id].tx = tmp_tx_buff
            ax_conn[conn_id].noAck = no_ack
            ax_conn[conn_id].vs = rx_inp['ctl']['nr']
    ax_conn[conn_id].n2 = 1


def RR_RX(conn_id, rx_inp):
    if ax_conn[conn_id].snd_RRt3 and rx_inp['ctl']['pf']:
        ax_conn[conn_id].snd_RRt3 = False
        print('#### Recv T3 RR Requ.')
    # Confirm I Frames
    elif rx_inp['ctl']['cmd'] or rx_inp['ctl']['pf']:
        ax_conn[conn_id].ack = [True, rx_inp['ctl']['pf'], False]
    confirm_I_Frames(conn_id, rx_inp)
    ax_conn[conn_id].t1 = 0
    # set_t2(conn_id)


def RR_TX_T3(conn_id):
    # T3 is done ( Hold connection )
    ax_conn[conn_id].ack = [False, True, True]
    # tx_buffer.append(RR_frm(conn_id))
    ax_conn[conn_id].tx_ctl = [RR_frm(conn_id)] + list(ax_conn[conn_id].tx_ctl)
    ax_conn[conn_id].snd_RRt3 = True
    set_t1(conn_id)
    print('#### Send T3 RR Requ.')


def REJ_RX(conn_id, rx_inp):
    confirm_I_Frames(conn_id, rx_inp)
    # set_t2(conn_id)
    ax_conn[conn_id].t1 = 0
    print('###### REJ_RX > ' + str(rx_inp))


def REJ_TX(conn_id):
    ax_conn[conn_id].tx_ctl.append(REJ_frm(conn_id, ax_conn[conn_id].rej[1], False))
    ax_conn[conn_id].rej = [False, False]
    print('###### REJ_TX > ' + str(conn_id))


def I_RX(conn_id, rx_inp):
    if rx_inp['ctl']['ns'] == ax_conn[conn_id].vr:
        ax_conn[conn_id].rx_data += str(rx_inp['data'])
        ax_conn[conn_id].vr = (1 + ax_conn[conn_id].vr) % 8
        ax_conn[conn_id].t1 = 0
        # set_t2(conn_id)
        confirm_I_Frames(conn_id, rx_inp)
        if rx_inp['ctl']['pf']:
            # ax_conn[conn_id].ack = [False, ax_conn[conn_id].ack[1], False]
            ax_conn[conn_id].ack = [False, True, False]
            # Send single RR if P Bit is received
            tx_buffer.append(RR_frm(conn_id))
        else:
            ax_conn[conn_id].ack = [True, ax_conn[conn_id].ack[1], False]

        print('###### I-Frame > ' + str(rx_inp['data']))
    else:
        '''
        ######################################
        # If RX Send sequence is f** up
        if (rx_inp['ctl']['ns']) == (ax_conn[conn_id].vr - 1) % 8:
            # ax_conn[conn_id].ack = [True, ax_conn[conn_id].ack[1], False] # TODO Needed????
            # P/F True to get back in sequence ?
            ax_conn[conn_id].rej = [True, True]
        else:
            print('###### REJ_TX inp > ' + str(rx_inp))
            ax_conn[conn_id].rej = [True, ax_conn[conn_id].rej[1]]
        '''
        print('###### REJ_TX inp > ' + str(rx_inp))
        ax_conn[conn_id].rej = [True, rx_inp['ctl']['pf']]
    # set_t2(conn_id)


def I_TX(conn_id, data=''):
    if ax_conn[conn_id].stat != 'RR':
        return False
    if len(ax_conn[conn_id].noAck) >= 7:
        return False
    ax_conn[conn_id].tx.append(I_frm(conn_id, data))
    ax_conn[conn_id].vs = (1 + ax_conn[conn_id].vs) % 8
    # ax_conn[conn_id].t1 = 0
    ax_conn[conn_id].n2 = 1
    # set_t2(conn_id)
    return True


def DM_TX(rx_inp, pf_bit=True):    # !!!!!!!!!!! Dummy. !! Not Tested  !!!!!!!!!!!!!
    tx_buffer.append(DM_frm(rx_inp, pf_bit))
    # Will send if Station is Busy or can't request SABM or receive any other Pac as SABM, UI
    # Also will send to confirm a UI Pac if station is not connected


def DM_RX(conn_id):
    if ax_conn[conn_id].stat == 'SABM':
        print('#### Called Station is Busy ..... ######')
    del ax_conn[conn_id]


def UA_RX(conn_id):
    ax_conn[conn_id].n2 = 1
    ax_conn[conn_id].t1 = 0
    ax_conn[conn_id].vs, ax_conn[conn_id].vr = 0, 0
    if ax_conn[conn_id].stat == 'SABM':
        ax_conn[conn_id].tx = ax_conn[conn_id].tx[1:]          # Not lucky with that solution TODO
        ax_conn[conn_id].stat = 'RR'
        monitor.debug_out('#### Connection established ..... ######')
        # monitor.debug_out('ax_conn[id][tx]> ' + str(ax_conn[conn_id].tx))
        print('#### Connection established ..... ######')
    elif ax_conn[conn_id].stat == 'DISC':
        monitor.debug_out('#### Disc confirmed ..... ######')
        # monitor.debug_out('ax_conn[id][tx]> ' + str(ax_conn[conn_id].tx))
        print('#### Disc confirmed ..... ######')
        del ax_conn[conn_id]


def DISC_TX(conn_id):
    monitor.debug_out('')
    monitor.debug_out('#### DISCO Send ..... ######')
    monitor.debug_out(conn_id)
    print('#### DISCO Send to ' + ax_conn[conn_id].dest[0])
    print(conn_id)
    # Answering DISC
    if ax_conn[conn_id].stat == 'RR':
        ax_conn[conn_id].ack = [False, False, False]
        ax_conn[conn_id].rej = [False, False]
        ax_conn[conn_id].stat = 'DISC'
        ax_conn[conn_id].n2 = 1
        ax_conn[conn_id].tx = [DISC_frm(conn_id)]
    elif ax_conn[conn_id].stat == 'SABM':
        tx_buffer.append(DISC_frm(conn_id))
        del ax_conn[conn_id]
    elif ax_conn[conn_id].stat == 'DISC' and ax_conn[conn_id].n2 > ax_conn[conn_id].ax25N2:
        tx_buffer.append(DISC_frm(conn_id))
        del ax_conn[conn_id]


def DISC_RX(conn_id, rx_inp):
    monitor.debug_out('')
    monitor.debug_out('#### DISCO Request ..... ######')
    monitor.debug_out(conn_id)
    print('#### DISCO Request fm ' + rx_inp['FROM'][0])
    print(conn_id)
    # Answering DISC
    if conn_id in ax_conn.keys():
        tx_buffer.append(UA_frm(rx_inp))       # UA_TX
        del ax_conn[conn_id]
    else:
        tx_buffer.append(DM_frm(rx_inp))


def setup_new_conn(conn_id, rx_inp, mycall):
    tmp = Stations[mycall]()
    from_call, to_call = rx_inp['FROM'], rx_inp['TO']
    tmp.dest = [from_call[0], from_call[1]]
    # TODO on SSID 0 allow multiple connections ( call SSID +=1 )
    via = []
    for el in rx_inp['via']:
        via.append([el[0], el[1], False])
    via.reverse()
    tmp.via = via
    ax_conn[conn_id] = tmp
    set_t3(conn_id)


#######################################################################


def UA_frm(rx_inp):
    # Answering Conn Req. or Disc Frame
    pac = get_tx_packet_item(rx_inp=rx_inp)
    pac['typ'] = ['UA', rx_inp['ctl']['pf']]
    pac['cmd'] = False
    return pac


def I_frm(conn_id, data=''):
    pac = get_tx_packet_item(conn_id=conn_id)
    # VR will be set again just before sending !!!
    if ax_conn[conn_id].noAck:
        vs = int((ax_conn[conn_id].noAck[-1] + 1) % 8)
    else:
        vs = int(ax_conn[conn_id].vs)
    ax_conn[conn_id].noAck.append(vs)
    pac['typ'] = ['I', False, ax_conn[conn_id].vr, vs]
    pac['cmd'] = True
    pac['pid'] = 6
    pac['out'] = data
    return pac


def DM_frm(rx_inp, f_bit=None):
    # Answering DISC
    if f_bit is None:
        f_bit = rx_inp['ctl']['pf']
    pac = get_tx_packet_item(rx_inp=rx_inp)
    pac['typ'] = ['DM', f_bit]
    pac['cmd'] = False
    return pac


def DISC_frm(conn_id):
    # DISC Frame
    pac = get_tx_packet_item(conn_id=conn_id)
    pac['typ'] = ['DISC', True]
    pac['cmd'] = True
    return pac


def RR_frm(conn_id):
    # RR Frame
    pac = get_tx_packet_item(conn_id=conn_id)
    pac['typ'] = ['RR', ax_conn[conn_id].ack[1], ax_conn[conn_id].vr]
    pac['cmd'] = ax_conn[conn_id].ack[2]
    print('')
    print('######## Send RR >')
    print(pac)
    print('')
    print('~~~~~~Send RR~~~~~~~~~~~~')
    print('')
    ax_conn[conn_id].ack = [False, False, False]
    return pac


def REJ_frm(conn_id, pf_bit=False, cmd=False):
    # REJ Frame
    pac = get_tx_packet_item(conn_id=conn_id)
    pac['typ'] = ['REJ', pf_bit, ax_conn[conn_id].vr]
    pac['cmd'] = cmd
    # ax_conn[conn_id].rej = [False, False]
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

    def send_Ack(id_in):
        if ax_conn[id_in].stat == 'RR':
            ######################################################
            # Send REJ
            if ax_conn[id_in].rej[0]:
                REJ_TX(id_in)
            ######################################################
            # Send Ack if not sendet with I Frame
            elif ax_conn[id_in].ack[0]:
                tx_buffer.append(RR_frm(id_in))

    #############################################
    # Check T0
    if time.time() > timer_T0 or timer_T0 == 0:
        for conn_id in ax_conn.keys():
            # print('### OUT > ' + str())
            #############################################
            # Check T2
            if time.time() > ax_conn[conn_id].t2 or ax_conn[conn_id].t2 == 0:
                if pac_c > parm_MaxBufferTX:
                    send_Ack(conn_id)
                    set_t2(conn_id)
                    break
                n2 = int(ax_conn[conn_id].n2)
                t1 = float(ax_conn[conn_id].t1)
                snd_tr = False

                ####################################################################
                # T3
                if (time.time() > ax_conn[conn_id].t3 or ax_conn[conn_id].snd_RRt3)\
                        and (not ax_conn[conn_id].tx_ctl and not ax_conn[conn_id].tx_ctl)\
                        and (time.time() > t1 or t1 == 0):
                    RR_TX_T3(conn_id)
                elif not ax_conn[conn_id].snd_RRt3:
                    ####################################################################
                    tx_data2tx_buffer(conn_id)  # Fill free TX "Slots" with data
                    ####################################################################
                ####################################################################
                # CTL Frames ( Not T1 controlled ) just T2
                tx_ctl = list(ax_conn[conn_id].tx_ctl)
                for el in tx_ctl:
                    tx_buffer.append(el)
                    ax_conn[conn_id].tx_ctl = ax_conn[conn_id].tx_ctl[1:]
                    pac_c += 1
                    if ax_conn[conn_id].snd_RRt3:
                        break
                #############################################
                # Timeout and N2 out
                if n2 > ax_conn[conn_id].ax25N2 and (time.time() > t1 != 0):
                    # DISC ???? TODO Testing
                    monitor.debug_out('#### Connection failure ..... ######' + conn_id)
                    print('#### Connection failure ..... ######' + conn_id)
                    ax_conn[conn_id].ack = [False, False, False]
                    ax_conn[conn_id].rej = [False, False]
                    disc_keys.append(conn_id)
                    snd_tr = True
                #############################################
                if not ax_conn[conn_id].snd_RRt3:
                    ind = 0
                    tmp = list(ax_conn[conn_id].tx)
                    for el in tmp:
                        if pac_c > parm_MaxBufferTX:
                            send_Ack(conn_id)
                            set_t2(conn_id)
                            break
                        if len(el['typ']) > 2:
                            el['typ'][2] = ax_conn[conn_id].vr
                        #############################################
                        # I Frames - T1 controlled and N2 counted
                        if time.time() > t1 or t1 == 0:
                            el = dict(el)
                            if el['typ'][0] == 'I' and max_i_frame_c_f_all_conns < parm_max_i_frame:
                                max_i_frame_c_f_all_conns += 1
                                #########################################
                                # Set P Bit = True if I-Frame is sendet
                                tm = el['typ']
                                ax_conn[conn_id].tx[ind]['typ'] = [tm[0], True, tm[2], tm[3]]
                                #########################################
                                if not ax_conn[conn_id].ack[1]:
                                    ax_conn[conn_id].ack = [False, False, False]
                            tx_buffer.append(el)
                            snd_tr = True
                            pac_c += 1

                            ######################################################
                            # On SABM Stat just send first element from TX-Buffer.
                            if ax_conn[conn_id].stat in ['SABM', 'DISC']:
                                break

                        ind += 1
                    send_Ack(conn_id)
                if snd_tr:
                    set_t1(conn_id)
                    set_t2(conn_id)
                    set_t3(conn_id)
                    # ax_conn[conn_id].t2 = 0
                    ax_conn[conn_id].n2 = n2 + 1

    ######################################################
    # Send Discs
    for dk in disc_keys:
        DISC_TX(dk)

#############################################################################


def read_kiss():
    #############################################################################
    # MAIN LOOP  / Thread
    #############################################################################
    global test_snd_packet, tx_buffer, timer_T0
    pack = b''
    ser = serial.Serial(ser_port, ser_baud, timeout=0.5)
    while not p_end:
        b = ser.read()
        pack += b
        if b:           # RX ###################################################################################
            set_t0()
            if ax.conv_hex(b[0]) == 'c0' and len(pack) > 2:
                monitor.debug_out("----------------Kiss Data IN ----------------------")
                dekiss_inp = ax.decode_ax25_frame(pack[2:-1])      # DEKISS
                if dekiss_inp:
                    handle_rx(dekiss_inp)
                    timer_T0 = 0
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
                    monitor.debug_out("ERROR Dec> " + str(dekiss_inp), True)
                monitor.debug_out("_________________________________________________")
                pack = b''

        handle_tx()          # TX #############################################################
        if tx_buffer:
            monitor.debug_out(ax_conn)
            c = 0
            while tx_buffer and c < parm_MaxBufferTX:
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


##################################################################################################################

##################################################################################################################
# INIT
##################################################################################################################
conf_stations()
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
    try:
        th = threading.Thread(target=read_kiss).start()
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
                      "C  = conncet\n\r"
                      "D  = Disconnect all Stations\n\r"
                      "DS = Disconnect selected Station\n\r"
                      "ST = Select Connected Stations\n\r"
                      "S  = Send Packet\n\r"
                      "SL = Send Packet Loop of 7 Pacs\n\r"
                      "\n\r> ")
            if i.upper() == 'Q':
                disc_all_stations()
                p_end = True
                break
            else:
                os.system('clear')

            if i.upper() == 'D':
                print('############  Disc send to : ' + str(ax_conn.keys()))
                disc_all_stations()
            elif i.upper() == 'ST':
                c = 1
                print('')
                for k in ax_conn.keys():
                    print(str(c) + ' > ' + str(k))
                    c += 1
                print('~~~~~~~~~~~~~~~~~~~~~~~~~')
                print('')
                inp = input('Select Station > ')
                if inp.isdigit():
                    sel_station = list(ax_conn.keys())[int(inp) - 1]
                    os.system('clear')
                    print('Ok ..')
                    print('Selected Connection > ' + sel_station)
                else:
                    os.system('clear')
                    print('Type in Number !!')
            elif i.upper() == 'C':
                SABM_TX()
            elif i.isdigit():
                test_snd_packet = int(i)
                send_tr = True
                while test_snd_packet != -1:
                    time.sleep(0.01)
                send_tr = False
                print("Ok ..")
            elif not sel_station:
                if list(ax_conn.keys()):
                    sel_station = list(ax_conn.keys())[0]
                else:
                    print('Please connect to a Station first !')
            #################################################################
            # Station Actions
            #################################################################

            elif i.upper() == 'TB':     # Test Beacon
                tx_buffer = ax_test_pac
                print("OK ..")

            elif i.upper() == 'S':
                inp2 = input('> ')
                inp2 += '\r'
                I_TX(sel_station, inp2)
            elif i.upper() == 'SL':
                for c in list(range(7)):
                    I_TX(sel_station, (str(c) + '\r'))
                print('Ok ..')

            elif i.upper() == 'DS':
                print('############  Disc send to : ' + str(sel_station))
                DISC_TX(sel_station)
            elif i.upper() == 'P':
                print('')
                print(str(sel_station))
                # for e in vars(ax_conn[sel_station]):
                    # print(str(e))
                print('\r\n'.join("%s: %s" % item for item in vars(ax_conn[sel_station]).items()))

                print('~~~~~~~~~~~~~~~~~~~~~~~~~')
                print('')
            elif i.upper() == 'L':
                print('')
                for k in ax_conn.keys():
                    print(str(k))
                print('~~~~~~~~~~~~~~~~~~~~~~~~~')
                print('')

            elif i.upper() == 'T':
                inp = input('How many Packets should be send ? > ')
                if inp.isdigit():
                    test_data = ''
                    for c in range(int(inp)):
                        for i in range(ax_conn[sel_station].ax25PacLen):
                            test_data += str(c % 10)

                    print(str(sel_station) + ' -- send > ' + str(len(test_data)) + ' Bytes !!!!')
                    ax_conn[sel_station].tx_data += test_data
                    print('~~~~~~~~~~~~~~~~~~~~~~~~~')
                    print('')
                else:
                    print('Please enter a DIGIT ..!')
            elif i.upper() == 'B':
                for k in ax_conn.keys():
                    print(str(k) + ' tx_ctl > ' + str(ax_conn[k].tx_ctl))
                    print(str(k) + ' tx > ' + str(ax_conn[k].tx))
                    print('~~~~~~~~~~~~~~~~~~~~~~~~~')
                    print('')
            elif i.upper() == 'R':
                print(str(sel_station) + ' RX > \r\n' + ax_conn[sel_station]['rx_data'])
                print('~~~~~~~~~~~~~~~~~~~~~~~~~')
                print('')
                print('Ok ...')
            elif i.upper() == 'RD':
                for k in ax_conn.keys():
                    ax_conn[k]['rx'] = []
                print('Ok ...')

    except KeyboardInterrupt:
        disc_all_stations()
        p_end = True
        print("Ende ..")
