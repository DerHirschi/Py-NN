import ax25enc as ax
import threading
import time
import os
import monitor
import serial

ser_port = "/tmp/ptyAX5"
ser_baud = 1200
MyCall = 'MD2SAW-8'

MyCall = ax.get_ssid(MyCall)
# TEST DATA
ax_test_pac = [{
    'call': ('MD2SAW', 8),
    'dest': ('APRS  ', 0),
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
    'call': ('MD2SAW', 8),
    'dest': ('DX0SAW', 0),
    'via': [('CB0SAW', 9, True), ('CB0SAW', 0, False)],
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
    'call': ('MD2SAW', 0),
    'dest': ('DX0SAW', 0),
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
# ax25T1 = 500
# ax25RET = 5
'''
if ax25RET > 3:
    ax25T1 = (ax25T1 * (ax25RET + 4)) / 100                     # TODO RTT
else:
    ax25T1 = (ax25T1 * ax25RET) / 100                           # TODO RTT
'''

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


def get_conn_item(dest_in=('', 0), via_in=None):
    if via_in is None:
        via_in = []
    return {
        'call': MyCall,
        'dest': dest_in,
        'via': via_in,
        'tx': [],
        'rx': [],
        'stat': 'SABM',
        't1': 0.0,
        'nr': 0,
        'ns': 0,
        'pf': True
    }


def conn():
    os.system('clear')
    dest = input('Enter Dest. Call\r\n> ').upper()
    addr_str = dest + ':' + ax.get_call_str(MyCall[0], MyCall[1])
    dest = ax.get_ssid(dest)
    print('')
    via = input('Enter via\r\n> ').upper()
    via = via.split(' ')
    via_list = []
    for el in via:
        addr_str += ':' + el
        via_list.append(ax.get_ssid(el))         # TODO ? ?? Digi Trigger ??
    print(addr_str)
    ax_conn[addr_str] = get_conn_item(dest)
    print(ax_conn)
    print("OK ..")


def read_kiss():
    global test_snd_packet, tx_buffer
    pack = b''
    ser = serial.Serial(ser_port, ser_baud, timeout=1)
    while not p_end:
        b = ser.read()
        pack += b
        if b:
            if ax.conv_hex(b[0]) == 'c0' and len(pack) > 2:
                monitor.debug_out("----------------Kiss Data IN ----------------------")
                try:
                    out = ax.decode_ax25_frame(pack[2:-1])
                    # if out[0] in
                    if out[0] in rx_buffer.keys():
                        rx_buffer[out[0]].append(out[1])
                    else:
                        rx_buffer[out[0]] = [out[1]]
                    monitor.monitor(out[1])
                    monitor.debug_out('################ DEC END ##############################')

                except ValueError as e:
                    monitor.debug_out("-------------- ERROR beim Decoden !! -------------", True)
                    monitor.debug_out(e, True)
                    monitor.debug_out(pack, True)
                    monitor.debug_out('', True)
                monitor.debug_out("_________________________________________________")
                pack = b''
        elif tx_buffer:
            c = 0
            while tx_buffer and c < ax25MaxBufferTX:
                ax.send_kiss(ser, ax.encode_ax25_frame(tx_buffer[0]))
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
    enc = ax.encode_ax25_frame(ax_test_pac[test_snd_packet])
    print(ax.decode_ax25_frame(bytes.fromhex(enc)))
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
            os.system('clear')
            if i.upper() == 'Q':
                p_end = True
            elif i.upper() == 'T':
                tx_buffer = ax_test_pac
                print("OK ..")
            elif i.upper() == 'C':
                conn()
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
