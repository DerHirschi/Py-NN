import ax25enc as ax
import threading
import time

# TEST DATA
ax_conn = [{
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
# TESTING and DEBUGGING
# TEST DATA

i = input("T = Test\n\rEnter = Go\n\r> ")
if i == 't' or i == 'T':
    enc = ax.encode_ax25_frame(ax_conn[ax.test_snd_packet])
    print(ax.decode_ax25_frame(bytes.fromhex(enc)))
else:
    try:
        th = threading.Thread(target=ax.read_kiss).start()
        while not ax.p_end:
            print("_______________________________________________")
            i = input("Q = Quit\n\r0-5 = Send Packet\n\rT = Fill TX Buffer with Testdata\n\r> ")
            if i.upper() == 'Q':
                ax.p_end = True
            elif i.upper() == 'T':
                ax.tx_buffer = ax_conn
                print("OK ..")
            elif i.isdigit():
                ax.test_snd_packet = int(i)
                ax.send_tr = True
                while ax.test_snd_packet != -1:
                    time.sleep(0.01)
                ax.send_tr = False
                print("Ok ..")

    except KeyboardInterrupt:
        ax.p_end = True
        print("Ende ..")
