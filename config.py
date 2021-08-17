import ax25enc as ax
import monitor

ser_port = "/tmp/ptyAX5"
ser_baud = 9600
MyCallStr1 = 'MD3SAW-11'            # Call for outgoing connects
MyCallStr2 = ['MD3SAW-8', 'MD3SAW-9', 'MD3SAW-10']          # Calls for requests
MyCall = ax.get_ssid(MyCallStr1)
Calls = [MyCallStr1] + MyCallStr2
# TESTING and DEBUGGING
debug = monitor.debug
test_snd_packet = -1
# rx_buffer = {}

# AX25 Parameters
ax25MaxBufferTX = 20                    # Max Frames to send from Buffer
ax25PacLen = 128                        # Max Pac len
ax25MaxFrame = 3                        # Max (I) Frames
ax25TXD = 50                            # TX Delay for RTT Calculation
parm_max_i_frame = 14                   # Max I-Frame (all connections) per Cycle
parm_N2 = 5                             # Max Try    Default 20
parm_baud = 1200                        # Baud for RTT Calculation
parm_T2 = 4000 / (parm_baud / 100)      # T2 (Response Delay Timer) Default: 2888 / (parm_baud / 100)
parm_T0 = 600                           # T0 (Response Delay Timer) activated if data come in to prev resp. to early
# parm_IRTT = 550                       # Initial-Round-Trip-Time
parm_IRTT = (parm_T2 + ax25TXD) * 2     # Initial-Round-Trip-Time (Auto Parm) (bei DAMA wird T2*2 genommen)/NO DAMA YET
# ax25MaxRetry = 20

ax_MyCalls = {
    'MD3SAW-1': {         # W/O SSID = all SSIDs
        'CTEXT': 'MD3SAW-1\r\n'
                 'Diese Station dient nur zu Testzwecken !\r\n'
                 'This Station is just for Testing purposes !\r\n',
        'PROMPT': 'MD3SAW-1> ',
    },
    'MD3SAW-2': {         # W/O SSID = all SSIDs
        'CTEXT': 'MD3SAW--2\r\n'
                 'Diese Station dient nur zu Testzwecken !\r\n'
                 'This Station is just for Testing purposes !\r\n',
        'PROMPT': 'MD3SAW-2> ',
    }
}

################################
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
