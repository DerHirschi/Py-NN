import serial
import time
import threading
import monitor

ser_port = "/tmp/ptyAX5"
ser_baud = 1200
# TEST DATA

ax_conn = [{    # For Testmode
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
debug = monitor.debug
test_snd_packet = -1
# Globals
ax25MaxBufferTX = 20                    # Max Frames to send from Buffer
# ax25MaxFrame = 3
# ax25MaxTXtime = 30
# ax25T1 = 500
# ax25RET = 5

tx_buffer = []
p_end, send_tr = False, False

'''
if ax25RET > 3:
    ax25T1 = (ax25T1 * (ax25RET + 4)) / 100                     # TODO RTT
else:
    ax25T1 = (ax25T1 * ax25RET) / 100                           # TODO RTT
'''


def bin2bl(inp):
    return bool(int(inp))


def bytearray2hexstr(inp):
    return ''.join('{:02x}'.format(x) for x in inp)


def hexstr2bytearray(inp):
    return bytearray.fromhex(inp)


def conv_hex(inp):
    return hex(inp)[2:]


def get_ssid(inp):
    if inp.find('-') != -1:
        return inp[:inp.find('-')].upper(), inp[inp.find('-') + 1:].upper()
    else:
        return inp, ''


def format_hex(inp=''):
    fl = hex(int(inp, 2))[2:]
    if len(fl) == 1:
        return '0' + fl
    return fl


def decode_ax25_frame(data_in):
    ret = {
        "TO": '',
        "FROM": '',
        "ctl": [],
        "pid": ()
        # "DIGI1..8"
        # "data"
    }

    monitor.debug_out('################ DEC ##################################')

    def decode_address_char(in_byte):    # Convert to 7 Bit ASCII
        bin_char = bin(int(in_byte, 16))[2:].zfill(8)[:-1]
        he = hex(int(bin_char, 2))
        try:
            return bytes.fromhex(he[2:]).decode()
        except ValueError as e:
            raise e

    def decode_ssid(in_byte):       # Address > CRRSSID1    Digi > HRRSSID1
        bi = bin(int(in_byte, 16))[2:].zfill(8)
        s_bit = bin2bl(bi[7])       # Stop Bit      Bit 8
        c_bit = bin2bl(bi[0])       # C bzw H Bit   Bit 1
        ssid = int(bi[3:7], 2)      # SSID          Bit 4 - 7
        r_bits = bi[1:3]            # Bit 2 - 3 not used. Free to use for any application .?..
        return s_bit, c_bit, ssid, r_bits

    def decode_c_byte(in_byte):
        def bl2str(inp):
            if inp:
                return '-'
            else:
                return '+'

        res, ctl_str, pid = [], '', False
        bi = bin(int(in_byte, 16))[2:].zfill(8)
        pf = bin2bl(bi[3])                                                          # P/F
        if not bin2bl(bi[-1]):                              # I-Block   Informationsübertragung
            res.append("I")
            nr = int(bi[:3], 2)
            ns = int(bi[4:7], 2)
            res.append(pf)                                                       # P
            res.append(nr)                                                       # N(R)
            res.append(ns)                                                       # N(S)
            ctl_str = "I" + str(nr) + str(ns) + bl2str(pf)
            pid = True
        elif not bin2bl(bi[-2]) and bin2bl(bi[-1]):         # S-Block
            res.append("S")
            nr = int(bi[:3], 2)
            ss_bits = bi[4:6]
            res.append(pf)                                                       # P/F
            res.append(nr)                                                       # N(R)
            # res[1].append(ss_bits)                                                  # S S Bits
            if ss_bits == '00':                                         # Empfangsbereit RR
                ctl_str = "RR" + str(nr) + bl2str(pf)                               # P/F Bit add +/-
            elif ss_bits == '01':                                       # Nicht empfangsbereit RNRR
                ctl_str = "RNRR" + bl2str(pf)                                       # P/F Bit add +/-
            elif ss_bits == '10':                                       # Wiederholungsaufforderung REJ
                ctl_str = "REJ" + str(nr) + bl2str(pf)                              # P/F Bit add +/-
            else:
                ctl_str = "S-UNKNOW"

        elif bin2bl(bi[-2]) and bin2bl(bi[-1]):             # U-Block
            res.append("U")
            mmm = bi[0:3]
            mm = bi[4:6]
            # res[1].append(mmm)                                                      # M M M
            res.append(pf)                                                       # P/F
            # res[1].append(mm)                                                       # M M
            pf = not pf
            if mmm == '001' and mm == '11':
                ctl_str = "SABM" + bl2str(pf)   # Verbindungsanforderung
            elif mmm == '010' and mm == '00':
                ctl_str = "DISC" + bl2str(pf)   # Verbindungsabbruch
            elif mmm == '000' and mm == '11':
                ctl_str = "DM" + bl2str(pf)     # Verbindungsrückweisung
            elif mmm == '011' and mm == '00':
                ctl_str = "UA" + bl2str(pf)     # Unnummerierte Bestätigung
            elif mmm == '100' and mm == '01':
                ctl_str = "FRMR" + bl2str(pf)   # Rückweisung eines Blocks
                pid = True
            elif mmm == '000' and mm == '00':
                ctl_str = "UI" + bl2str(pf)     # Unnummerierte Information UI
                pid = True

        res.append(pid)
        res.append(ctl_str)
        return res

    def decode_pid_byte(in_byte):
        flag = ""
        bi = bin(int(in_byte, 16))[2:].zfill(8)
        if bi[2:5] == '01':
            flag = 'AX.25 (L3)'
        elif bi[2:5] == '10':
            flag = 'AX.25 (L3)'
        elif bi == '11001100':
            flag = 'IP (L3)'
        elif bi == '11001101':
            flag = 'ARP (L3)'
        elif bi == '11001111':
            flag = 'NET/ROM (L3/4)'
        elif bi == '11110000':
            flag = 'Text (NO L3)'
        elif bi == '11111111':          # Escape. Next Byte has more L3 Infos
            flag = False
        return flag, bi

    tmp_str, tmp_str2, address_str, end = "", bytearray(0), "", False
    address_field_count, byte_count = 0, 0
    keys = ["TO", "FROM"]
    monitor.debug_out("Dec IN: " + str(data_in))
    for i in data_in:
        byte_count += 1
        if not end:                                         # decode Address fields
            if byte_count != 7:                             # 7 Byte Address Chars
                try:
                    tmp = decode_address_char(conv_hex(i))
                except ValueError as e:
                    raise e
                address_str += tmp
                tmp_str += tmp
            else:                                           # 7 th Byte SSID (CRRSSID1)
                tmp = decode_ssid(conv_hex(i))
                address_field_count += 1
                byte_count = 0
                if tmp[2] != 0:
                    address_str += "-"
                    address_str += str(tmp[2])              # SSID
                if address_field_count > 2:                 # DIGI
                    keys.append("DIGI" + str(address_field_count - 2))
                    if tmp[1]:                              # H Bit
                        address_str += "*"
                if tmp[0]:                                  # S Bit ( Stop Bit )
                    end = True                              # End Address fields
                    monitor.debug_out('via Stop Bit found .. ' + address_str)
                else:
                    address_str += ":"
                '''CALL, int(SSID), H-BIT, R-BITs'''
                ret[keys[address_field_count - 1]] = tmp_str, tmp[2], tmp[1], tmp[3]
                tmp_str = ""

        else:
            if byte_count == 1:     # Control Byte
                ret['ctl'] = decode_c_byte(conv_hex(i))
            elif byte_count == 2:   # PID Byte in UI and I Frames
                if ret['ctl'][-2]:
                    ret['pid'] = decode_pid_byte(conv_hex(i))
                else:
                    tmp_str2.append(i)
            else:
                tmp_str2.append(i)

    text = str(tmp_str2.decode(errors="ignore"))
    monitor.debug_out("RES: " + address_str)
    monitor.debug_out(text)
    ret["data"] = (tmp_str2, len(tmp_str2))
    if debug:
        for k in ret.keys():
            monitor.debug_out(ret[k])
    return address_str, ret


def encode_ax25_frame(con_data):
    monitor.debug_out('################ ENC ##################################')
    out_str = ''
    temp = con_data['call'], con_data['dest']
    call, call_ssid, dest, dest_ssid = temp[0][0], temp[0][1], temp[1][0], temp[1][1]
    via = con_data['via']

    typ = con_data['typ']
    pid = con_data['pid']
    data_out = con_data['out']
    monitor.debug_out(str(con_data))

    def encode_address_char(in_ascii_str=''):   # TODO Adressbereich auffüllen wenn weniger als 6 chars
        t = bytearray(in_ascii_str.encode('ASCII'))
        out = ''
        for i in t:
            out += conv_hex(i << 1)
        return out

    def encode_ssid(ssid_in=0, c_h_bit=False, stop_bit= False):
        ssid_in = bin(ssid_in << 1)[2:].zfill(8)
        if c_h_bit:
            ssid_in = '1' + ssid_in[1:]               # Set C or H Bit. H Bit if msg was geDigit
        if stop_bit:
            ssid_in = ssid_in[:-1] + '1'              # Set Stop Bit on last DIGI
        ssid_in = ssid_in[:1] + '11' + ssid_in[3:]       # Set R R Bits True.
        return format_hex(ssid_in)

    def encode_c_byte(type_list):
        flag, p_f_bit = type_list[0], type_list[1]
        pid_tr, info_f_tr = False, False
        ret = ''.zfill(8)
        if p_f_bit:
            ret = ret[:3] + '1' + ret[4:]
        # I Block
        if flag == 'I':
            nr, ns = type_list[2], type_list[3]
            pid_tr, info_f_tr = True, True
            ret = bin(max(min(nr, 7), 0))[2:].zfill(3) + ret[3:]        # N(R)
            ret = ret[:4] + bin(max(min(ns, 7), 0))[2:].zfill(3) + '0'  # N(S)
        # S Block
        elif flag in ['RR', 'RNR', 'REJ']:
            nr = type_list[2]
            ret = ret[:-2] + '01'
            ret = bin(max(min(nr, 7), 0))[2:].zfill(3) + ret[3:]
            if flag == 'RR':
                ret = ret[:4] + '00' + ret[-2:]
            elif flag == 'RNR':
                ret = ret[:4] + '01' + ret[-2:]
            elif flag == 'REJ':
                ret = ret[:4] + '10' + ret[-2:]
        # U Block
        elif flag in ["SABM", "DISC", "DM", "UA", "FRMR", "UI"]:
            ret = ret[:-2] + '11'
            if flag == 'SABM':
                ret = '001' + ret[3] + '11' + ret[-2:]
            elif flag == 'DISC':
                ret = '010' + ret[3] + '00' + ret[-2:]
            elif flag == 'DM':
                ret = '000' + ret[3] + '11' + ret[-2:]
            elif flag == 'UA':
                ret = '011' + ret[3] + '11' + ret[-2:]
            elif flag == 'UI':
                ret = '000' + ret[3] + '00' + ret[-2:]
                pid_tr, info_f_tr = True, True
            elif flag == 'FRMR':
                ret = '100' + ret[3] + '01' + ret[-2:]
                info_f_tr = True
        return format_hex(ret), pid_tr, info_f_tr

    def encode_pid_byte(pid_in=6):
        ret = ''.zfill(8)
        if pid_in == 1:
            ret = '00010000'
        elif pid_in == 2:
            ret = '00100000'
        elif pid_in == 3:
            ret = '11001100'
        elif pid_in == 4:
            ret = '11001101'
        elif pid_in == 5:
            ret = '11001111'
        elif pid_in == 6:
            ret = '11110000'
        elif pid_in == 7:
            ret = '11111111'
        return format_hex(ret)

    out_str += encode_address_char(dest)
    out_str += encode_ssid(dest_ssid, True)             # TODO c/h Bit = Version
    out_str += encode_address_char(call)
    if via:                                             # Set Stop Bit
        out_str += encode_ssid(call_ssid)
        for i in via:
            out_str += encode_address_char(i[0])
            if i == via[-1]:                           # Set Stop Bit
                out_str += encode_ssid(i[1], i[2], True)
                monitor.debug_out('via Stop Bit set.. ' + i[0])
            else:
                out_str += encode_ssid(i[1], i[2])
    else:
        out_str += encode_ssid(call_ssid, False, True)  # TODO c/h Bit = Version

    c_byte = encode_c_byte(typ)               # Control Byte
    out_str += c_byte[0]
    if c_byte[1]:                                       # PID Byte
        out_str += encode_pid_byte(pid)
    if c_byte[2]:                                       # Info Field
        for i in data_out:                              # TODO Max Paclen
            out_str += format(ord(i.encode()), "x")

    monitor.debug_out(out_str)
    monitor.debug_out('############### ENC END ###############################')
    return out_str


def send_kiss(ser, data_in):
    monitor.debug_out("Send-Kiss: " + str(data_in))
    ser.write(bytes.fromhex('c000' + data_in + 'c0'))


def read_kiss():
    global test_snd_packet, tx_buffer
    pack = b''
    ser = serial.Serial(ser_port, ser_baud, timeout=1)
    while not p_end:
        b = ser.read()
        pack += b
        if b:
            if conv_hex(b[0]) == 'c0' and len(pack) > 2:
                monitor.debug_out("----------------Kiss Data IN ----------------------")
                try:
                    out = decode_ax25_frame(pack[2:-1])
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
                send_kiss(ser, encode_ax25_frame(tx_buffer[0]))
                tx_buffer = tx_buffer[1:]
                c += 1

        # TESTING
        if test_snd_packet != -1 and send_tr:
            send_kiss(ser, encode_ax25_frame(ax_conn[test_snd_packet]))
            test_snd_packet = -1
            while send_tr:
                time.sleep(0.01)


##################################################################################################################



'''

    try:
        print(decode_ax25_frame(b'r\x0c\xbd:1\xa6\xcf\r\xefVtPI\xfd\xe1\xa8\xa6\t\xa2\xa2U\x91!D\xffjV\x0b\x97N'))

'''
'''
i = input("T = Test\n\rEnter = Go\n\r> ")
if i == 't' or i == 'T':
    enc = encode_ax25_frame(ax_conn[test_snd_packet])
    print(decode_ax25_frame(bytes.fromhex(enc)))
else:
    try:
        th = threading.Thread(target=read_kiss).start()
        while not p_end:
            print("_______________________________________________")
            i = input("Q = Quit\n\r0-5 = Send Packet\n\rT = Fill TX Buffer with Testdata\n\r> ")
            if i.upper() == 'Q':
                p_end = True
            elif i.upper() == 'T':
                tx_buffer = ax_conn
                print("OK ..")
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
'''

