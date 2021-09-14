import crcmod
import monitor
debug = monitor.debug
crc_x25 = crcmod.predefined.mkCrcFun('x-25')


def bytearray2hexstr(inp):
    return ''.join('{:02x}'.format(x) for x in inp)


def hexstr2bytearray(inp):
    return bytearray.fromhex(inp)


def conv_hex(inp):
    return hex(inp)[2:]


def get_ssid(inp):
    if inp.find('-') != -1:
        return [inp[:inp.find('-')].upper(), int(inp[inp.find('-') + 1:].upper())]
    else:
        return [inp, 0]


def get_call_str(call, ssid=0):
    if type(call) == list:
        ssid = call[1]
        call = call[0]
    if ssid:
        return call + '-' + str(ssid)
    else:
        return call


def reverse_addr_str(inp=''):
    inp = inp.split(':')
    addr, via, ret = inp[:2], inp[2:], ''
    addr.reverse()
    via.reverse()
    for el in addr:
        ret += el + ':'
    for el in via:
        ret += el + ':'
    return ret[:-1]


def format_hex(inp=''):
    fl = hex(int(inp, 2))[2:]
    if len(fl) == 1:
        return '0' + fl
    return fl


def decode_ax25_frame(data_in):
    ret = {
        'TO': (),
        'FROM': (),
        'via': [],
        'ctl': [],
        'pid': (),
        'data': ['', 0]
        # "DIGI1..8"
        # "data"
    }

    monitor.debug_out('################ DEC ##################################')

    def decode_address_char(in_byte):    # Convert to 7 Bit ASCII
        bin_char = bin(int(in_byte, 16))[2:].zfill(8)[:-1]      # TODO just Shift the Bit
        char = chr(int(bin_char, 2))

        return char.replace(' ', '')

    def decode_ssid(in_byte):       # Address > CRRSSID1    Digi > HRRSSID1
        bi = bin(int(in_byte, 16))[2:].zfill(8)
        s_bit = bool(int(bi[7], 2)) # Stop Bit      Bit 8
        c_bit = bool(int(bi[0], 2)) # C bzw H Bit   Bit 1
        ssid = int(bi[3:7], 2)      # SSID          Bit 4 - 7
        r_bits = bi[1:3]            # Bit 2 - 3 not used. Free to use for any application .?..
        return s_bit, c_bit, ssid, r_bits

    def decode_c_byte(in_byte):
        monitor.debug_out('C-Byte HEX: ' + str(hex(int(in_byte, 16))))
        ctl = {
            'ctl_str': '',          # P/F Bit
            'type': '',             # Control Field Type ( U, I, S )
            'flag': '',             # Control Field Flag ( RR, REJ, SABM ... )
            'pf': False,            # P/F Bit
            'cmd': False,           # Command or Report ( C Bits in Address Field )
            'nr': -1,               # N(R)
            'ns': -1,               # N(S)
            'pid': False,           # Next Byte PID Field Trigger
            'info': False,          # Info Field Trigger
            'hex': 0x00             # Input as Hex
        }

        def bl2str(inp):
            if inp:
                return '+'
            else:
                return '-'

        ctl_str = ''
        bi = bin(int(in_byte, 16))[2:].zfill(8)
        pf = bool(int(bi[3], 2))                                                          # P/F
        ctl['pf'] = pf
        ctl['hex'] = int(in_byte, 16)
        if bi[-1] == '0':                               # I-Block   Informationsübertragung
            nr = int(bi[:3], 2)
            ns = int(bi[4:7], 2)
            ctl_str = 'I' + str(nr) + str(ns) + bl2str(pf)
            ctl['type'], ctl['flag'] = 'I', 'I'
            ctl['nr'], ctl['ns'] = nr, ns
            ctl['pid'], ctl['info'] = True, True
            ctl['ctl_str'] = ctl_str
        elif bi[-2:] == '01':                           # S-Block
            nr = int(bi[:3], 2)
            ss_bits = bi[4:6]
            if ss_bits == '00':                                         # Empfangsbereit RR
                ctl_str = 'RR' + str(nr) + bl2str(pf)                   # P/F Bit add +/-
                ctl['flag'] = 'RR'
            elif ss_bits == '01':                                       # Nicht empfangsbereit RNRR
                ctl_str = 'RNRR' + bl2str(pf)                           # P/F Bit add +/-
                ctl['flag'] = 'RNRR'
            elif ss_bits == '10':                                       # Wiederholungsaufforderung REJ
                ctl_str = 'REJ' + str(nr) + bl2str(pf)                  # P/F Bit add +/-
                ctl['flag'] = 'REJ'
            elif ss_bits == '11':                                       # Selective Reject SREJ
                ctl_str = 'SREJ' + str(nr) + bl2str(pf)                 # P/F Bit add +/-
                ctl['flag'] = 'SREJ'
            else:
                monitor.debug_out('C-Byte Error S Frame!! ' + str(bi) + ' ' + str(in_byte), True)
                monitor.debug_out('!!!!!!!!! C-Byte Error S Frame !!!!!!!!! ' + str(bi) + ' ' + str(in_byte))
                return False
            ctl['type'] = 'S'
            ctl['nr'] = nr
            ctl['ctl_str'] = ctl_str

        elif bi[-2:] == '11':                           # U-Block
            mmm = bi[0:3]
            mm = bi[4:6]
            if mmm == '001' and mm == '11':
                ctl_str = "SABM" + bl2str(pf)   # Verbindungsanforderung
                ctl['flag'] = 'SABM'
            elif mmm == '011' and mm == '11':
                ctl_str = "SABME" + bl2str(pf)  # Verbindungsanforderung EAX25 (Modulo 128 C Field)
                ctl['flag'] = 'SABME'
            elif mmm == '010' and mm == '00':
                ctl_str = "DISC" + bl2str(pf)   # Verbindungsabbruch
                ctl['flag'] = 'DISC'
            elif mmm == '000' and mm == '11':
                ctl_str = "DM" + bl2str(pf)     # Verbindungsrückweisung
                ctl['flag'] = 'DM'
            elif mmm == '011' and mm == '00':
                ctl_str = "UA" + bl2str(pf)     # Unnummerierte Bestätigung
                ctl['flag'] = 'UA'
            elif mmm == '100' and mm == '01':
                ctl_str = "FRMR" + bl2str(pf)   # Rückweisung eines Blocks
                ctl['flag'] = 'FRMR'
                ctl['info'] = True
            elif mmm == '000' and mm == '00':
                ctl_str = "UI" + bl2str(pf)     # Unnummerierte Information UI
                ctl['flag'] = 'UI'
                ctl['pid'], ctl['info'] = True, True
            elif mmm == '111' and mm == '00':
                ctl_str = 'TEST' + bl2str(pf)     # TEST Frame
                ctl['flag'] = 'TEST'
                ctl['info'] = True
            elif mmm == '101' and mm == '11':
                ctl_str = 'XID' + bl2str(pf)     # XID Frame
                ctl['flag'] = 'XID'
            else:
                monitor.debug_out('C-Byte Error U Frame!! ' + str(bi) + ' ' + str(in_byte), True)
                monitor.debug_out('!!!!!!!!! C-Byte Error U Frame !!!!!!!!! ' + str(bi) + ' ' + str(in_byte))
                return False

            ctl['type'] = 'U'
            ctl['ctl_str'] = ctl_str

        return ctl

    def decode_pid_byte(in_byte):
        in_byte = int(in_byte, 16)
        bi = bin(in_byte)[2:].zfill(8)
        if bi[2:5] == '01':
            flag = 'AX.25 (L3)'
        elif bi[2:5] == '10':
            flag = 'AX.25 (L3)'
        elif in_byte == 0xF0:
            flag = 'Text (NO L3)'
        elif in_byte == 0xCF:
            flag = 'NET/ROM (L3/4)'
        elif in_byte == 0xCC:
            flag = 'IP (L3)'
        elif in_byte == 0xCD:
            flag = 'ARPA Address res(L3)'
        elif in_byte == 0xCE:
            flag = 'FlexNet'
        ######################
        elif in_byte == 0x01:
            flag = 'X.25 PLP'
        elif in_byte == 0x06:
            flag = 'Compressed TCP/IP'
        elif in_byte == 0x07:
            flag = 'Uncompressed TCP/IP'
        elif in_byte == 0x08:
            flag = 'Segmentation fragment'
        elif in_byte == 0xC3:
            flag = 'TEXTNET datagram'
        elif in_byte == 0xC4:
            flag = 'Link Quality Protocol'
        elif in_byte == 0xCA:
            flag = 'Appletalk'
        elif in_byte == 0xCB:
            flag = 'Appletalk ARP'
        elif in_byte == 0xFF:               # Escape. Next Byte has more L3 Infos
            flag = False
        else:
            monitor.debug_out('PID-Byte Error' + str(bi) + ' ' + str(in_byte), True)
            monitor.debug_out('!!!!!!!!! PID-Byte Error !!!!!!!!! ' + str(bi) + ' ' + str(in_byte))
            return False

        return flag, hex(in_byte)

    #################################################################

    tmp_str, tmp_str2, address_str, end = "", bytearray(0), "", False
    address_field_count, byte_count = 0, 0
    keys = ['TO', 'FROM']
    via = []
    monitor.debug_out('Dec IN: ' + str(data_in))
    for i in data_in:
        byte_count += 1
        if not end:                                         # decode Address fields
            if byte_count != 7:                             # 7 Byte Address Chars
                tmp = decode_address_char(conv_hex(i))
                address_str += tmp
                tmp_str += tmp
            else:                                           # 7 th Byte SSID (CRRSSID1)
                tmp = decode_ssid(conv_hex(i))
                address_field_count += 1
                byte_count = 0
                if tmp[2] != 0:
                    address_str += '-'
                    address_str += str(tmp[2])              # SSID
                if address_field_count > 2:                 # DIGI
                    '''CALL, int(SSID), H-BIT, R-BITs'''
                    via.append([tmp_str, tmp[2], tmp[1], tmp[3]])
                    if tmp[1]:                              # H Bit
                        address_str += '*'
                else:
                    '''CALL, int(SSID), H-BIT, R-BITs'''
                    ret[keys[address_field_count - 1]] = tmp_str, tmp[2], tmp[1], tmp[3]
                if tmp[0]:                                  # S Bit ( Stop Bit )
                    end = True                              # End Address fields
                else:
                    address_str += ':'

                tmp_str = ''

        else:
            if byte_count == 1:     # Control Byte
                if ret['FROM'] and ret['TO']:
                    ret['ctl'] = decode_c_byte(conv_hex(i))
            elif byte_count == 2:   # PID Byte in UI and I Frames
                if ret['ctl']:
                    if ret['ctl']['pid']:
                        ret['pid'] = decode_pid_byte(conv_hex(i))
                    else:
                        tmp_str2.append(i)                          # TODO chr() ?
            else:
                tmp_str2.append(i)                                  # TODO chr() ?

    text = str(tmp_str2.decode(errors='ignore'))                    # TODO chr() ?
    monitor.debug_out('RES: ' + address_str)
    monitor.debug_out(text)
    if ret['ctl']:
        if ret['ctl']['info']:
            ret['data'] = [tmp_str2, len(tmp_str2)]                 # TODO chr() ?
    ret['via'] = via
    # print('## DATA IN > ' + str(bytearray2hexstr(data_in)) + ' --- HEX> ' + str(bytearray2hexstr(tmp_str2[-2:])))
    for ke in ['TO', 'FROM', 'ctl']:         # Little Check Frame is plausible TODO better check
        if not ret[ke]:
            monitor.debug_out('"-------------- ERROR beim Decoden !! -------------"', True)
            monitor.debug_out(ret, True)
            return False
    if not ret['pid'] and ret['ctl']['pid']:
        monitor.debug_out('"-------------- ERROR beim Decoden !! No PID ---------"', True)
        monitor.debug_out(ret, True)
        return False
    if ret['TO'][2] and not ret['FROM'][2]:
        ret['ctl']['cmd'] = True
    elif not ret['TO'][2] and ret['FROM'][2]:
        ret['ctl']['cmd'] = False

    if debug:
        for k in ret.keys():
            monitor.debug_out(ret[k])
    return address_str.replace('*', ''), ret, len(data_in)


def encode_ax25_frame(con_data):
    monitor.debug_out('################ ENC ##################################')
    out_str = ''
    temp = (con_data['call'], con_data['dest'])
    call, call_ssid, dest, dest_ssid = temp[0][0], temp[0][1], temp[1][0], temp[1][1]
    via = con_data['via']

    typ = con_data['typ']
    pid = con_data['pid']
    if con_data['cmd']:
        dest_c, call_c = True, False
    else:
        dest_c, call_c = False, True

    data_out = con_data['out']
    monitor.debug_out(str(con_data))

    def encode_address_char(in_ascii_str=''):
        in_ascii_str = "{:<6}".format(in_ascii_str)
        t = bytearray(in_ascii_str.encode('ASCII'))
        out = ''
        for i in t:
            out += conv_hex(i << 1)
        return out

    def encode_ssid(ssid_in=0, c_h_bit=False, stop_bit=False):
        ssid_in = bin(ssid_in << 1)[2:].zfill(8)
        if c_h_bit:
            ssid_in = '1' + ssid_in[1:]               # Set C or H Bit. H Bit if msg was geDigit
        if stop_bit:
            ssid_in = ssid_in[:-1] + '1'              # Set Stop Bit on last DIGI
        ssid_in = ssid_in[:1] + '11' + ssid_in[3:]    # Set R R Bits True.
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
        elif flag in ['RR', 'RNR', 'REJ', 'SREJ']:
            nr = type_list[2]
            ret = ret[:-2] + '01'
            ret = bin(max(min(nr, 7), 0))[2:].zfill(3) + ret[3:]
            if flag == 'RR':
                ret = ret[:4] + '00' + ret[-2:]
            elif flag == 'RNR':
                ret = ret[:4] + '01' + ret[-2:]
            elif flag == 'REJ':
                ret = ret[:4] + '10' + ret[-2:]
            elif flag == 'SREJ':
                ret = ret[:4] + '11' + ret[-2:]
        # U Block
        elif flag in ['SABM', 'DISC', 'DM', 'UA', 'FRMR', 'UI', 'TEST', 'XID']:
            ret = ret[:-2] + '11'
            if flag == 'SABM':
                ret = '001' + ret[3] + '11' + ret[-2:]
            elif flag == 'DISC':
                ret = '010' + ret[3] + '00' + ret[-2:]
            elif flag == 'DM':
                ret = '000' + ret[3] + '11' + ret[-2:]
            elif flag == 'UA':
                ret = '011' + ret[3] + '00' + ret[-2:]
            elif flag == 'UI':
                ret = '000' + ret[3] + '00' + ret[-2:]
                pid_tr, info_f_tr = True, True
            elif flag == 'FRMR':                        # TODO Not completely implemented yet
                ret = '100' + ret[3] + '01' + ret[-2:]
                info_f_tr = True
            elif flag == 'TEST':                        # TODO Not completely implemented yet
                ret = '111' + ret[3] + '00' + ret[-2:]
                info_f_tr = True
            elif flag == 'XID':                         # TODO Not implemented yet
                ret = '101' + ret[3] + '11' + ret[-2:]
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
        ###################
        # NET/ROM (L3/4)
        elif pid_in == 5 or pid_in == 0xCF:
            ret = '11001111'
        ###################
        # Text (NO L3)
        elif pid_in == 6 or pid_in == 0xF0:
            ret = '11110000'
        elif pid_in == 7:
            ret = '11111111'
        return format_hex(ret)

    out_str += encode_address_char(dest)
    out_str += encode_ssid(dest_ssid, dest_c)
    out_str += encode_address_char(call)
    if via:                                             # Set Stop Bit
        out_str += encode_ssid(call_ssid, call_c)
        c = 1
        for i in via:
            out_str += encode_address_char(i[0])
            if c == len(via):                           # Set Stop Bit
                out_str += encode_ssid(i[1], i[2], True)
                # monitor.debug_out('via Stop Bit set.. ' + i[0])
            else:
                out_str += encode_ssid(i[1], i[2])
            c += 1

    else:
        out_str += encode_ssid(call_ssid, call_c, True)

    c_byte = encode_c_byte(typ)                         # Control Byte
    out_str += c_byte[0]
    if c_byte[1]:                                       # PID Byte
        out_str += encode_pid_byte(pid)
    if c_byte[2]:                                       # Info Field
        if type(data_out) is str:
            for i in data_out:
                # out_str += format(ord(i.encode()), "x")
                out_str += ''.join('{:02x}'.format(ord(i.encode()), "x"))
        elif type(data_out) is bytearray:
            # Digi
            out_str += bytearray2hexstr(data_out)
    monitor.debug_out(out_str)
    monitor.debug_out('############### ENC END ###############################')
    return out_str


def send_kiss(ser, data_in):
    monitor.debug_out("Send-Kiss: " + str(data_in))
    ser.write(bytes.fromhex('c000' + data_in + 'c0'))

