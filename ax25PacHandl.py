import ax25enc as ax
import threading
import time
import os
import monitor
import serial

ser_port = "/tmp/ptyAX5"
ser_baud = 1200
MyCallStr = 'MD2SAW-12'

MyCall = ax.get_ssid(MyCallStr)
# TEST DATA
ax_test_pac = [{
    'call': ('MD2SAW', 8, False),
    'dest': ('APRS  ', 0, True),
    'via': [('DX0SAW', 0, False)],
    'out': '< TEST fm MD2SAW ( JO52NU ) >',
    'typ': ('UI', True),
    'pid': 6
},
{   # 1
    'call': ('MD2SAW', 8),
    'dest': ('DX0SAW', 0),
    'via': [('CB0SAW', 0, False)],
    'out': '',
    'typ': ('SABM', True),
    'pid': 6
},
{   # 2
    'call': ('MD2SAW', 8),
    'dest': ('DX0SAW', 0),
    'via': [('CB0SAW', 9, True), ('CB0SAW', 0, False)],
    'out': '',
    'typ': ('SABM', True),
    'pid': 6
},
{   # 3
    'call': ('MD2SAW', 0, False),
    'dest': ('MD2SAW', 12, True),
    'via': [('CB0SAW', 0, True), ('DX0SAW', 0, False)],
    'out': '',
    'typ': ('DISC', True),
    'pid': 6
},
{   # 4
    'call': ('MD2SAW', 8),
    'dest': ('DX0SAW', 0),
    'via': [('CB0SAW', 0, False), ('DNX527', 0, False)],
    'out': '',
    'typ': ('SABM', True),
    'pid': 6
},
{   # 5
    'call': ('MD2SAW', 8),
    'dest': ('DX0SAW', 0),
    'via': [('CB0SAW', 0, False), ('DNX527', 0, False)],
    'out': '',
    'typ': ('DISC', True),
    'pid': 6
},
{   # 6
    'call': ('DNX527', 0),
    'dest': ('DX0SAW', 0),
    'via': [],
    'out': '',
    'typ': ('SABM', True),
    'pid': 6
},
{   # 7
    'call': ('MD2SAW', 0),
    'dest': ('DX0SAW', 0),
    'via': [('CB0SAW', 0, True)],
    'out': 'TEST',
    'typ': ('I', True, 5, 4),   # Type, P/F, N(R), N(S)
    'pid': 6
},
{   # 8
    'call': ('MD2SAW', 0, False),
    'dest': ('DX0SAW', 0, True),
    'via': [('CB0SAW', 0, True)],
    'out': '',
    'typ': ('RR', True, 0),   # Type, P/F, N(R), N(S)
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
# ax25MaxFrame = 3
# ax25MaxTXtime = 30
ax25T1 = 500
# ax25MaxRetry = 20


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
        'call': (MyCall[0], MyCall[1], False),
        'dest': ('', 0, True),
        'via': [],
        'tx': [],
        'rx': [],
        'stat': 'SABM',
        'pf': True,
        'nr': 0,
        'ns': 0,
        't1': 0.0,
        'ret': 0

    }


def get_tx_packet_item(conn_id):
    return {
        'call': ax_conn[conn_id]['call'],
        'dest': ax_conn[conn_id]['dest'],
        'via': ax_conn[conn_id]['via'],
        'out': '',
        'typ': ('SABM', True, 0),   # Type, P/F, N(R), N(S)
        'pid': 6,
        'nr': 0,
        'ns': 0,
        't1': 0.0,
    }


def set_t1(conn_key):
    retry = ax_conn[conn_key]['ret']
    if retry > 3:
        ax_conn[conn_key]['t1'] = ((ax25T1 * (retry + 4)) / 100) + time.time()     # TODO RTT
    else:
        ax_conn[conn_key]['t1'] = ((ax25T1 * retry) / 100) + time.time()           # TODO RTT


def handle_rx(inp):
    monitor.monitor(inp[1])
    conn_id = ax.reverse_addr_str(inp[0])
    if conn_id in ax_conn.keys():
        monitor.debug_out('')
        monitor.debug_out('###### Conn Data In ########')
        monitor.debug_out(conn_id)
        print('Conn incoming... ' + conn_id)
        print(inp[1])
        tmp = ax_conn[conn_id]['rx']
        tmp.append(inp[1])
        ax_conn[conn_id]['rx'] = tmp
        ax_conn[conn_id]['t1'], ax_conn[conn_id]['ret'] = 0, 0

        monitor.debug_out(ax_conn[conn_id])
        monitor.debug_out('#### Conn Data In END ######')
        monitor.debug_out('')
    elif inp[1]['ctl'][-1] in [0x3f, 0x7f] and inp[0].split(':')[0] in [MyCallStr]:       # Incoming connection SABM or SABME
        monitor.debug_out('')
        monitor.debug_out('#### Connect Request ..... ######')
        monitor.debug_out(conn_id)
        print('#### Connect Request fm ' + inp[1]['FROM'][0])
        print(conn_id)
        conn_in(conn_id, inp=inp[1])                                                    #TODO Ver request

        monitor.debug_out(ax_conn[conn_id])
        monitor.debug_out('#### Incoming Conn Data In END ######')
        monitor.debug_out('')


def conn_out():
    os.system('clear')
    dest = input('Enter Dest. Call\r\n> ').upper()
    conn_id = dest + ':' + ax.get_call_str(MyCall[0], MyCall[1])
    dest = ax.get_ssid(dest)
    print('')
    via = input('Enter via\r\n> ').upper()
    via = via.split(' ')
    via_list = []
    if via == ['']:
        via = []
    for el in via:
        conn_id += ':' + el
        via_list.append(ax.get_ssid(el))         # TODO ? ?? Digi Trigger ??
    print(conn_id)
    print(via)
    print(via_list)
    if conn_id not in ax_conn.keys():
        ax_conn[conn_id] = get_conn_item()
        ax_conn[conn_id]['dest'] = (dest[0], dest[1], True)
        call = ax_conn[conn_id]['call']
        ax_conn[conn_id]['call'] = (call[0], call[1], False)
        ax_conn[conn_id]['via'] = via_list
        tx_pack = get_tx_packet_item(conn_id)
        tx_pack['typ'] = ('SABM', True)
        ax_conn[conn_id]['tx'] = [tx_pack]
        print(ax_conn)
        print("OK ..")
    else:
        print('Connection schon vorhanden !!')
        print('')


def conn_in(conn_id, inp):
    print(inp)
    ax_conn[conn_id] = get_conn_item()
    dest = inp['FROM']
    ax_conn[conn_id]['dest'] = (dest[0], dest[1], not dest[2])          # Vers Command !!!!!!!!!!!!!!! Testen
    call = ax_conn[conn_id]['call']
    ax_conn[conn_id]['call'] = (call[0], call[1], not inp['TO'][2])     # Vers Command  !!!!!!!!!!!!!!! Testen
    via = conn_id.split(':')[2:]
    for el in via:
        ax_conn[conn_id]['via'].append((ax.get_ssid(el)[0], ax.get_ssid(el)[1], False))
    ax_conn[conn_id]['rx'] = [inp]
    tx_pack = get_tx_packet_item(conn_id)
    tx_pack['typ'] = ('UA', inp['ctl'][1])                              # P/F Bit uebernehmen  !!!!!!!!!!!!!!! Testen
    ax_conn[conn_id]['tx'] = [tx_pack]
    set_t1(conn_id)

    tx_pack['typ'] = ('I', ax_conn[conn_id]['nr'], ax_conn[conn_id]['ns'], )
    tx_pack['out'] = '############# TEST ###############'
    ax_conn[conn_id]['tx'] = [tx_pack]


def put_txbuffer():
    for k in ax_conn.keys():
        tmp = ax_conn[k]['tx']
        for el in tmp:
            tx_buffer.append(el)
            ax_conn[k]['tx'] = ax_conn[k]['tx'][1:]

##################################################################################################################


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
                try:
                    out = ax.decode_ax25_frame(pack[2:-1])      # DEKISS
                    handle_rx(out)

                    ############ TEST ##############
                    if out[0] in rx_buffer.keys():
                        rx_buffer[out[0]].append(out[1])
                    else:
                        rx_buffer[out[0]] = [out[1]]
                    ########## TEST ENDE ###########

                    monitor.debug_out('################ DEC END ##############################')

                except ValueError as e:
                    monitor.debug_out("-------------- ERROR beim Decoden !! -------------", True)
                    monitor.debug_out(e, True)
                    monitor.debug_out(pack, True)
                    monitor.debug_out('', True)
                monitor.debug_out("_________________________________________________")
                pack = b''

        put_txbuffer()          # TX #############################################################
        if tx_buffer:
            monitor.debug_out(ax_conn)
            monitor.debug_out(tx_buffer)
            c = 0
            while tx_buffer and c < ax25MaxBufferTX:
                enc = ax.encode_ax25_frame(tx_buffer[0])
                ax.send_kiss(ser, enc)
                print("Out> " + str(ax.decode_ax25_frame(bytes.fromhex(enc))))
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
    print(ax.decode_ax25_frame(b'\xc0\x00\xa8\x8a\xa6\xa8@@\xe0\x9a\x88d\xa6\x82\xae`\x86\x84`\xa6\x82\xae\xe0\x88\xb0`\xa6\x82\xae\xe1?\xc0'[2:-1]))
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
                      "P = Print RX-Buffer\n\r"
                      "C = conncet"
                      "\n\r> ")
            if i.upper() == 'Q':
                p_end = True
                break
            else:
                os.system('clear')

            if i.upper() == 'T':
                tx_buffer = ax_test_pac
                print("OK ..")
            elif i.upper() == 'C':
                conn_out()
            elif i.upper() == 'P':
                for k in rx_buffer.keys():
                    print('')
                    print(str(k))
                    for e in rx_buffer[k]:
                        for kk in e.keys():
                            print(e[kk])
                        print('_________________________')
                    print('~~~~~~~~~~~~~~~~~~~~~~~~~')
                    print('')
            elif i.isdigit():
                test_snd_packet = int(i)
                send_tr = True
                while test_snd_packet != -1:
                    time.sleep(0.01)
                send_tr = False
                print("Ok ..")

    except KeyboardInterrupt:
        p_end = True
        print("Ende ..")
