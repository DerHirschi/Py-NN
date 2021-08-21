import ax25enc as ax
import threading
import time
import os
import serial
import monitor

ser_port = "/tmp/ptyAX5"
ser_baud = 9600
# Globals
Stations = {}
digi_calls = []


class AX25Connection(object):
    dest = ['', 0]
    via = []
    tx = []                         # TX Buffer (T1)
    tx_ctl = []                     # CTL TX Buffer (T2)
    rx_data = ''                    # RX Data Buffer
    tx_data = ''                    # TX Data Buffer
    stat = ''                       # State ( SABM, RR, DISC )
    vs = 0
    vr = 0
    noAck = []                     # No Ack Packets
    ack = [False, False, False]     # Send on next time, PF-Bit, CMD
    rej = [False, False]
    t1 = 0
    t2 = 0
    t3 = 0                          # TODO
    n2 = 1


class DefaultParam(AX25Connection):
    def __init__(self):
        self.call = [self.call, self.ssid]
    #################################################################
    # Station Default Parameters / Also outgoing connections
    call = 'MD3SAW'
    ssid = 0                                                        # 0 = all
    ctext = 'Diese Station dient nur zu Testzwecken !\r' \
            'This Station is just for Testing purposes !\r'
    prompt = '> '
    digi = True     # Digipeating
    ###################################################################################################################
    # AX25 Parameters                   ###############################################################################
    ax25PacLen = 128                    # Max Pac len
    ax25MaxFrame = 3                    # Max (I) Frames
    ax25TXD = 50                        # TX Delay for RTT Calculation
    ax25T2 = 4000                       # T2 (Response Delay Timer) Default: 2888 / (parm_baud / 100)
    ax25T3 = 180000                     # TODO T3 (Inactive Link Timer)
    parm_MaxBufferTX = 20               # Max Frames to send from Buffer
    parm_max_i_frame = 14               # Max I-Frame (all connections) per Cycle
    parm_N2 = 5                         # Max Try   Default 20
    parm_baud = 1200                    # Baud for RTT Calculation
    parm_T0 = 400                       # T0 (Response Delay Timer) activated if data come in to prev resp. to early
    # parm_T1 = ax25T1                    # T0 (Response Delay Timer) activated if data come in to prev resp. to early
    parm_T2 = ax25T2 / (parm_baud / 100)
    # parm_IRTT = 550                   # Initial-Round-Trip-Time
    parm_IRTT = (parm_T2 + ax25TXD) * 2 # Initial-Round-Trip-Time (Auto Parm) (bei DAMA wird T2*2 genommen)/NO DAMA YET


class MD3SAW10(DefaultParam):
    call = 'MD3SAW'
    ssid = 10                                                       # 0 = all
    ctext = 'MD3SAW-10\r' \
            'Diese Station dient nur zu Testzwecken !\r' \
            'This Station is just for Testing purposes !\r'
    prompt = 'MD3SAW-10> '


class MD3SAW11(DefaultParam):
    call = 'MD3SAW'
    ssid = 11                                                       # 0 = all
    ctext = 'MD3SAW-11\r' \
            'Diese Station dient nur zu Testzwecken !\r' \
            'This Station is just for Testing purposes !\r'
    prompt = 'MD3SAW-11> '


class MD4SAW(DefaultParam):
    call = 'MD4SAW'
    ssid = 0                                                       # 0 = all
    ctext = 'MD4SAW\r' \
            'Diese Station dient nur zu Testzwecken !\r' \
            'This Station is just for Testing purposes !\r'
    prompt = 'MD4SAW> '
    digi = True                         # Digipeating
    ax25PacLen = 128                    # Max Pac len
    ax25MaxFrame = 3                    # Max (I) Frames
    ax25TXD = 50                        # TX Delay for RTT Calculation
    ax25T2 = 4000                       # T2 (Response Delay Timer) Default: 2888 / (parm_baud / 100)
    ax25T3 = 180000                     # TODO T3 (Inactive Link Timer)


########################################
# AX25 Parameters
parm_max_i_frame = int(DefaultParam().parm_max_i_frame)     # Max I-Frame (all connections) per Cycle
parm_T0 = int(DefaultParam().parm_T0)   # T0 (Response Delay Timer) activated if data come in to prev resp. to early
parm_MaxBufferTX = int(DefaultParam().parm_MaxBufferTX)     # Max Frames to send from Buffer

stat_list = [DefaultParam, MD3SAW10, MD3SAW11, MD3SAW11]


def conf_stations():
    #################################################
    # INIT Vars
    """
    Stations = {
        'MD3SAW-10': MD3SAW10(),
        'MD3SAW-11': MD3SAW11(),
        'MD4SAW': MD4SAW(),
    }
    """
    for obj in stat_list:
        if obj.ssid:
            call_str = ax.get_call_str(obj.call, obj.ssid)
            Stations[call_str] = obj
            if obj.digi:
                digi_calls.append([obj.call, obj.ssid])
        else:
            #########################################
            # If no SSID make all SSIDs connectable
            for ssid in range(16):
                call_str = ax.get_call_str(obj.call, ssid)
                Stations[call_str] = obj
                if obj.digi:
                    digi_calls.append([obj.call, ssid])



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

if __name__ == '__main__':
    conf_stations()
    # a = StationParam()
    # print(a.prompt)
    print(vars(Stations['MD3SAW-11']))
    # print(Stations['MD3SAW-11'].call)
    # print(a.prompt)
    # conf_stations()
