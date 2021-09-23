import remote_cli
from remote_cli import init_cli
from ax25Statistics import MH
from Clients_cfg import *

ser_port = "/tmp/ptyAX5"
ser_baud = 9600
# Globals
ax_ports = {
    # 0: PortObj
}
# Stations = {}
digi_calls = {
    # 'callstr': AxPort
}
bcast_calls = {
    # 'callstr': AxPort
}
cron_pacs = {
    #  'callstr': [[pac, to, next_send, axip]]
}
#################################
# Init MH
print('# Init MH')
mh = MH()
##################
# Init Client DB
print('# Init Client DB')
db = ClientDB()


#######################################
# Connection Class
class DefaultParam(object):
    def __init__(self):
        self.call = [self.call, self.ssid]
        self.dest = ['', 0]
        self.via = []
        self.port = None            # Port Obj
        self.conn_id = ''           # Conn ID Str
        self.tx = []                # TX Buffer (T1)
        self.tx_ctl = []            # CTL TX Buffer (T2)
        self.rx_data = []           # RX Data Buffer
        self.tx_data = ''           # TX Data Buffer
        self.tx_bin = bytearray(0)  # TX Data Buffer (Binary) Has TX Priority
        self.stat = ''              # State ( SABM, RR, DISC )
        self.vs = 0
        self.vr = 0
        self.noAck = []             # No Ack Packets
        self.ack = [False, False, False]  # Send trigger, PF-Bit, CMD
        self.rej = [False, False]   # Send trigger, PF-Bit
        self.snd_RRt3 = False       # Await respond from RR cmd
        self.t1 = 0
        self.t2 = 0
        self.t3 = 0
        self.n2 = 1
        self.parm_T2 = self.ax25T2 / (self.parm_baud / 100)
        self.parm_IRTT = (self.parm_T2 + self.ax25TXD) * 2  # Initial-Round-Trip-Time (Auto Parm) (bei DAMA wird T2*2 genommen)/NO DAMA YET
        self.parm_RTT = self.parm_IRTT
        self.rtt = {
            # vs: time.time()
        }
        self.station_ctexte_var = {}
        ###################################
        # Debug !!!
        self.deb_calc_t1 = 0
        ###################################
        # AXIP
        self.axip_client = ()       # UDP Client data   ('192.168.178.153', 8099)
        ###################################
        # Link 2 other Station (NODE Link)
        self.node_links = {
            # 'conn_id': node_link_Obj
        }
        ###################################
        # MH Obj
        self.mh = mh
        ######################
        # Client DB entry
        self.db_entry = None
        ###################################
        # CLI Obj
        self.cli = None
        if self.cli_type:
            self.cli = remote_cli.CLIDefault(self)
            init_cli(self)
            self.promptvar = '\r' + self.prompt
            self.ctextvar = self.ctext + self.prompt
            for k in self.station_ctexte.keys():
                self.station_ctexte_var[k] = self.station_ctexte[k] + self.prompt
        else:
            self.ctextvar = self.ctext
            self.promtvar = self.prompt

    #################################################################
    # Station Default Parameters / Also outgoing connections
    call = 'MD3SAW'
    ssid = 0                                                        # 0 = all
    ctext = 'Diese Station dient nur zu Testzwecken !\r' \
            'This Station is just for Testing purposes !\r'
    qtext = '\r73 de {}\r'
    station_ctexte = {
        'MD2SAW': 'C Text for MD2SAW\r',
    }
    prompt = '> '
    digi = True                         # Digipeating
    cli_type = []                       # Remote CLI Type ( 1=NODE, 2=TERM, 3=BBS)
    cli_msg_tag = '<{}>'
    cli_sufix = '//'
    bcast_srv = False
    ###################################################################################################################
    # AX25 Parameters                   ###############################################################################
    ax25PacLen = 115                    # Max Pac len
    ax25MaxFrame = 5                    # Max (I) Frames
    ax25TXD = 50                        # TX Delay for RTT Calculation
    ax25T2 = 2888                       # T2 (Response Delay Timer) Default: 2888 / (parm_baud / 100)
    ax25T3 = 18000                      # T3 (Inactive Link Timer) Default: 18000
    ax25N2 = 20                         # Max Try   Default 20
    parm_MaxBufferTX = 20               # Max Frames to send from Buffer
    parm_max_i_frame = 14               # Max I-Frame (all connections) per Cycle
    parm_baud = 1200                    # Baud for RTT Calculation
    parm_T0 = 1200                      # T0 (Response Delay Timer) activated if data come in to prev resp. to early
    # parm_T1 = ax25T1                    # T0 (Response Delay Timer) activated if data come in to prev resp. to early
    parm_T2 = ax25T2 / (parm_baud / 100)
    # parm_IRTT = 550                   # Initial-Round-Trip-Time
    parm_IRTT = (parm_T2 + ax25TXD) * 2 # Initial-Round-Trip-Time (Auto Parm) (bei DAMA wird T2*2 genommen)/NO DAMA YET
    port_conf_id = 0                    # conf_ax_ports

    def handle_cli(self):
        if self.cli:
            self.cli.main()


class MD3SAW10(DefaultParam):
    # AXIP
    call = 'MD3SAW'
    ssid = 10
    ax25PacLen = 250    # Max Pac len
    ax25MaxFrame = 7    # Max (I) Frames
    ax25TXD = 500       # TX Delay for RTT Calculation  !! Need to be high on AXIP for T1 calculation
    ax25T2 = 3          # T2 (Response Delay Timer) Default: 2888 / (parm_baud / 100)
    ax25T3 = 180000     # T3 (Inactive Link Timer)
    ax25N2 = 20
    parm_baud = 1200    # Baud for RTT Calculation  !! Need to be low on AXIP for T1 calculation
    parm_T0 = 1         # T0 (Response Delay Timer) activated if data come in to prev resp. to early
    cli_type = [1]
    cli_sufix = '//'
    ctext = 'MD3SAW-10\r' \
            'Diese Station dient nur zu Testzwecken !\r' \
            'This Station is just for Testing purposes !\r'
    prompt = 'MD3SAW-10> '
    parm_T2 = ax25T2 / (parm_baud / 100)
    parm_IRTT = (parm_T2 + ax25TXD) * 2 # Initial-Round-Trip-Time (Auto Parm) (bei DAMA wird T2*2 genommen)/NO DAMA YET


class MD3SAW11(DefaultParam):
    call = 'MD3SAW'
    ssid = 11                                                       # 0 = all
    digi = True                                                     # Digipeating
    cli_type = [1, 3, 4, 9]                                         # Remote CLI Type ( 1=NODE, 2=TERM, 3=BBS, 9=Test)
    cli_sufix = ''
    ax25PacLen = 128    # Max Pac len
    ax25MaxFrame = 5    # Max (I) Frames
    ax25TXD = 30        # TX Delay for RTT Calculation  !! Need to be high on AXIP for T1 calculation
    ax25T2 = 2888       # T2 (Response Delay Timer) Default: 2888 / (parm_baud / 100)
    ax25T3 = 18000      # T3 (Inactive Link Timer)
    ax25N2 = 5

    ctext = 'MD3SAW-11\r' \
            'Diese Station dient nur zu Testzwecken !\r' \
            'This Station is just for Testing purposes !\r'
    prompt = 'MD3SAW-11> '
    parm_baud = DefaultParam.parm_baud
    parm_T2 = ax25T2 / (parm_baud / 100)
    parm_IRTT = (parm_T2 + ax25TXD) * 2 # Initial-Round-Trip-Time (Auto Parm) (bei DAMA wird T2*2 genommen)/NO DAMA YET


class MD3SAW12(DefaultParam):
    call = 'MD3SAW'
    ssid = 12                                                       # 0 = all
    digi = True                                                     # Digipeating
    cli_type = [1, 4]                                                    # Remote CLI Type ( 1=NODE, 2=TERM, 3=BBS, 9=Test)
    cli_sufix = ''
    bcast_srv = True
    ax25PacLen = 250    # Max Pac len
    ax25MaxFrame = 7    # Max (I) Frames
    ax25TXD = 500        # TX Delay for RTT Calculation  !! Need to be high on AXIP for T1 calculation
    ax25T2 = 3       # T2 (Response Delay Timer) Default: 2888 / (parm_baud / 100)
    ax25T3 = 180000      # T3 (Inactive Link Timer)
    ax25N2 = 15
    parm_T0 = 1         # T0 (Response Delay Timer) activated if data come in to prev resp. to early

    ctext = 'MD3SAW-12\r' \
            'Diese Station dient nur zu Testzwecken !\r' \
            'This Station is just for Testing purposes !\r'
    prompt = 'MD3SAW-12> '
    parm_baud = DefaultParam.parm_baud
    parm_T2 = ax25T2 / (parm_baud / 100)
    parm_IRTT = (parm_T2 + ax25TXD) * 2 # Initial-Round-Trip-Time (Auto Parm) (bei DAMA wird T2*2 genommen)/NO DAMA YET


class MD3SAW14(DefaultParam):
    call = 'MD3SAW'
    ssid = 14                                                       # 0 = all
    digi = True                                                     # Digipeating
    cli_type = [1, 9]                                                    # Remote CLI Type ( 1=NODE, 2=TERM, 3=BBS, 9=Test)
    cli_sufix = ''
    bcast_srv = False
    ax25PacLen = 128    # Max Pac len
    ax25MaxFrame = 5    # Max (I) Frames
    ax25TXD = 30        # TX Delay for RTT Calculation  !! Need to be high on AXIP for T1 calculation
    ax25T2 = 2888       # T2 (Response Delay Timer) Default: 2888 / (parm_baud / 100)
    ax25T3 = 18000      # T3 (Inactive Link Timer)
    ax25N2 = 15

    ctext = 'MD3SAW-14\r' \
            'Diese Station dient nur zu Testzwecken !\r' \
            'This Station is just for Testing purposes !\r'
    prompt = 'MD3SAW-14> '
    parm_baud = DefaultParam.parm_baud
    parm_T2 = ax25T2 / (parm_baud / 100)
    parm_IRTT = (parm_T2 + ax25TXD) * 2 # Initial-Round-Trip-Time (Auto Parm) (bei DAMA wird T2*2 genommen)/NO DAMA YET


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
    ax25T3 = 180000                     # T3 (Inactive Link Timer)
    ax25N2 = 5                          # Max Try   Default 20
    parm_baud = DefaultParam.parm_baud
    parm_T2 = ax25T2 / (parm_baud / 100)
    parm_IRTT = (parm_T2 + ax25TXD) * 2 # Initial-Round-Trip-Time (Auto Parm) (bei DAMA wird T2*2 genommen)/NO DAMA YET


# stat_list = [DefaultParam, MD3SAW10, MD3SAW11]


conf_ax_ports = {
    0: {
        'typ': 'KISS',
        'add': "/tmp/ptyAX5",
        'baud': 1200,
        'name': 'Port 0 KISS',
        # 'stat_list': [DefaultParam, MD3SAW11]
        'stat_list': [MD3SAW11]
    },
    1: {
        'typ': 'AXIP',
        'add': '192.168.178.150',     # Own Address
        'port': 8099,                  #
        'baud': 1200,                  # TODO Just a Dummy
        'name': 'Port 1 AXIP',
        'bcast': True,                  # AXIP Broadcast Server (Send icomming Traffic out to all other AXIP Clients)
        'stat_list': [MD3SAW10, MD3SAW12]
    },
    2: {
        'typ': 'DW',                    # TCIP to Direwolf
        'add': '127.0.0.1',           # DW Adress
        'port': 8001,                  # DW Port
        'baud': 1200,                  # DW Baud
        'name': 'Port 2 DWolf',
        # 'bcast': False,                 # AXIP Broadcast Server (Send icomming Traffic out to all other AXIP Clients)
        'stat_list': [MD3SAW14]
    },
}


class NodeLink(object):
    def __init__(self, connection, caller_id):
        self.link = connection      # Other Connection
        self.stat = 'SABM'
        self.caller_id = caller_id

    def disc_tx(self):
        self.link.port.DISC_TX(self.link.conn_id)
        self.link = None
        self.stat = 'DISC'

    def disc_rx(self):
        # del self.link
        self.link = None
        self.stat = 'DISC'


################################
# TEST DATA
ax_test_pac = [{
    'call': ['MD2SAW', 8],
    'dest': ['APRS', 0],
    'via': [['DX0SAW', 0, False]],
    'out': '< TEST BESTANDEN !! >',
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

