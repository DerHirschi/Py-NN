import serial
import time
import monitor
#data_in = "9a88648484a660ac8462849eb0f2ac8462"
#test_data_in = "9a88648484a6e09a8864a682ae60868460a682aee140f0620d" # Rest 40f0620d  ### I Frame
# 9a88648484a6e09a8864a682ae60868460a682aee1 Rest 40f0620d
test_data_in = "9a88648484a6e0868460a682ae6151"    # MD2SAW to MD2BBS via CB0SAW* CB0SAW* ctl RR2-
#test_data_in = "ae 8aa8 a88a a4e0 8684 60a6 82ae 7c86 8460 a682 ae67 03f0 3c20 5765 7474 6572 2053 616c 7a77 6564 656c 204a 4f35 324e 5520 3e0d 0a20 5465 6d70 2e3a 2020 3231 2e30 2020 430d 0a20 4c75 6674 6472 7563 6b3a 2020 3130 3136 2e36 3731 3220 2068 5061 0d0a 204c 7566 7466 6575 6368 7469 676b 6569 743a 2020 3534 2e38 2020 25"
#test_data_in = "ae8aa8a88aa4e0868460a682ae7c868460a682ae6703f03c205765747465722053616c7a776564656c204a4f35324e55203e0d0a2054656d702e3a202032312e302020430d0a204c756674647275636b3a2020313031362e3637313220206850610d0a204c75667466657563687469676b6569743a202035342e38202025"
# CB0SAW-14 to WETTER via CB0SAW-3 ctl UI^ pid=F0(Text) len 103
#test_data_in = b'\xc0\x00\x86\x84`\xa6\x82\xae`\x9a\x88d\x84\x84\xa6\xe1Q\xc0'
#test_data_in = "9a8864a682aee088b060a682ae60868460a682ae61" #cf0445830534157202831313a3530293e"
#test_data_in = "9a8864a682aee088b060a682ae60868460a682ae61e8" #cf0445830534157202831313a3530293e"
#test_data_in = "8864a682aee0b060a682ae608460a682aee13f0626c6120303030303030303030303030205445535420544553542044444444444444444444" #cf0445830534157202831313a3530293e"
#test_data_in = test_data_in.replace(" ", "")

ser_port = "/tmp/ptyAX5"
ser_baud = 9600
ax_conn = []
ax_conn.append({
    'call': 'MD2SAW-8',
    'dest': 'TEST11',
    'via': ('CB0SAW', False),
    'out': '< TEST fm MD2SAW ( JO52NU ) >',
    'typ': ('UI', False),
    'pid': 6
})
ax_conn.append({
    'call': 'MD2SAW-8',
    'dest': 'DX0SAW',
    'via': ('CB0SAW', True),
    'out': '',
    'typ': ('SABM', True),
    'pid': 6
})
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
        "ctl": (),
        "pid": ()
        # "DIGI1..8"
        # "data"
    }

    def decode_address_char(in_byte):    # Convert to 7 Bit ASCII
        bin_char = bin(int(in_byte, 16))[2:].zfill(8)[:-1]
        he = hex(int(bin_char, 2))
        return bytes.fromhex(he[2:]).decode()

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
            res.append([])
            nr = int(bi[:3], 2)
            ns = int(bi[4:7], 2)
            res[1].append(pf)                                                       # P
            res[1].append(nr)                                                       # N(R)
            res[1].append(ns)                                                       # N(S)
            ctl_str = "I" + str(nr) + str(ns) + bl2str(pf)
            pid = True
        elif not bin2bl(bi[-2]) and bin2bl(bi[-1]):         # S-Block
            res.append("S")
            res.append([])
            nr = int(bi[:3], 2)
            ss_bits = bi[4:6]
            res[1].append(pf)                                                       # P/F
            res[1].append(nr)                                                       # N(R)
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
            res.append([])
            mmm = bi[0:3]
            mm = bi[4:6]
            # res[1].append(mmm)                                                      # M M M
            res[1].append(pf)                                                       # P/F
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

        res[1].append(pid)
        res[1].append(ctl_str)
        return ctl_str, res, bi

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
    print("Dec IN: " + str(data_in))
    for i in data_in:
        byte_count += 1
        if not end:                                         # decode Address fields
            if byte_count != 7:                             # 7 Byte Address Chars
                tmp = decode_address_char(conv_hex(i))
                address_str += tmp
                tmp_str += tmp
            else:                                           # 8 th Byte SSID (CRRSSID1)
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
                else:
                    address_str += ":"
                '''CALL, int(SSID), H-BIT, R-BITs'''
                ret[keys[address_field_count - 1]] = tmp_str, tmp[2], tmp[1], tmp[3]
                tmp_str = ""

        else:
            if byte_count == 1:     # Control Byte
                ret['ctl'] = decode_c_byte(conv_hex(i))
            elif byte_count == 2:   # PID Byte in UI and I Frames
                if ret['ctl'][1][-2]:
                    ret['pid'] = decode_pid_byte(conv_hex(i))
                else:
                    tmp_str2.append(i)
            else:
                tmp_str2.append(i)

    # calc_fcs(data_in[-2:])
    text = str(tmp_str2.decode(errors="ignore"))
    print("RES: " + address_str + "\r\n> " + text)
    ret["data"] = (tmp_str2, len(tmp_str2))
    if debug:
        for k in ret.keys():
            print(ret[k])
    monitor.monitor(ret)
    return address_str, ret


def encode_ax25_frame(con_data):
    out_str = ''
    c, d = get_ssid(con_data['call']), get_ssid(con_data['dest'])
    call, call_ssid = c[0], c[1]
    dest, dest_ssid = d[0], d[1]
    via = con_data['via'][0].split(' ')
    i = 0
    for n in via:
        t = get_ssid(n)
        via[i] = (t[0], t[1])
        i += 1

    typ = con_data['typ']
    pid = con_data['pid']
    data_out = con_data['out']
    print(call + call_ssid)
    print(dest + dest_ssid)
    print(via)

    def encode_address_char(in_ascii_str=''):   # TODO Adressbereich auffüllen wenn weniger als 6 chars
        t = bytearray(in_ascii_str.encode('ASCII'))
        out = ''
        for i in t:
            out += conv_hex(i << 1)
        return out

    def encode_ssid(in_ascii_str='', c_h_bit=False, stop_bit= False):
        if in_ascii_str == '':
            in_ascii_str = '0'
        ssid = int(in_ascii_str)
        ssid = bin(ssid << 1)[2:].zfill(8)
        if c_h_bit:
            ssid = '1' + ssid[1:]               # Set C or H Bit. H Bit if msg was geDigit
        if stop_bit:
            ssid = ssid[:-1] + '1'              # Set Stop Bit on last DIGI
        ssid = ssid[:1] + '11' + ssid[3:]       # Set R R Bits True.
        # print(ssid)
        # print(hex(int(ssid, 2))[2:])
        # return hex(int(ssid, 2))[2:]
        return format_hex(ssid)

    def encode_c_byte(type_str, p_f_bit=False):
        ret = ''.zfill(8)
        pid_tr = False
        if p_f_bit:
            ret = ret[:3] + '1' + ret[4:]
        # U Block
        if type_str in ["SABM", "DISC", "DM", "UA", "FRMR", "UI"]:
            ret = ret[:-2] + '11'
            if type_str == 'UI':
                pid_tr = True
                return format_hex(ret), pid_tr
            elif type_str == 'SABM':
                ret = '001' + ret[3] + '11' + ret[-2:]
                return format_hex(ret), pid_tr
        return format_hex(ret), pid_tr

    def encode_pid_byte(pid_in=6):
        ret = ''.zfill(8)
        if pid_in == 1:
            return format_hex(ret[:2] + '01' + ret[4:])
        elif pid_in == 2:
            return format_hex(ret[:2] + '10' + ret[4:])
        elif pid_in == 3:
            return format_hex('11001100')
        elif pid_in == 4:
            return format_hex('11001101')
        elif pid_in == 5:
            return format_hex('11001111')
        elif pid_in == 6:
            return format_hex('11110000')
        elif pid_in == 7:
            return format_hex('11111111')

    out_str += encode_address_char(dest)
    out_str += encode_ssid(dest_ssid, True)
    out_str += encode_address_char(call)
    if via:                                             # Set Stop Bit
        out_str += encode_ssid(call_ssid)
    else:
        out_str += encode_ssid(call_ssid, False, True)
    c = 0
    for i in via:
        out_str += encode_address_char(i[0])
        if c + 1 == len(via):                           # Set Stop Bit
            out_str += encode_ssid(i[1], con_data['via'][0], True)
            #out_str += encode_ssid(i[1], True, True)
        else:
            out_str += encode_ssid(i[1])
    c_byte = encode_c_byte(typ[0],typ[1])               # Control Byte
    out_str += c_byte[0]
    if c_byte[1]:                                       # PID Byte
        out_str += encode_pid_byte(pid)
        for i in data_out:
            pass
            out_str += format(ord(i.encode()), "x")

    print(out_str)
    return out_str


def send_kiss(ser, data_in):
    # c0009a8864a682aee088b060a682ae60868460a682ae6104f00d445830534157202830323a3030293ec0
    # 9a8864a682aee088b060a682ae60868460a682ae6104f00d445830534157202830323a3030293e
    # 9a8864a682aee088b060a682ae61868460a682ae61
    # 9a8864a682ae88b060a682ae
    # 9a8864a682ae6488b060a682ae0
    # DX0SAW>MD2SAW,CB0SAW:(I cmd, n(s)=2, n(r)=0, p=0, pid=0xf0)<0x0d>DX0SAW (02:00)>
    # fm DX0SAW to MD2SAW via CB0SAW ctl I02^ pid=F0(Text) len 16 02:44:07
    #
    # DX0SAW (02:00)>
    # data_in = '9a8864a682aee088b060a682ae60868460a682ae6104f00d445830534157202830323a3030293e'
    print("S-Kiss: " + str(data_in))
    ser.write(bytes.fromhex('c000' + data_in + 'c0'))
    #print(decode_ax25_frame(data_in.encode()))


def read_kiss():
    pack = b''
    ser = serial.Serial(ser_port, ser_baud, timeout=1)
    t = time.time() -40
    while True:
        b = ser.read()
        pack += b
        if b:
            if conv_hex(b[0]) == 'c0' and len(pack) > 2:
                print("-------------------------------------------------")
                decode_ax25_frame(pack[2:-1])
                print("_________________________________________________")
                pack = b''
        if time.time() - t > 60 and send:
            print('#######################################################')
            send_kiss(ser, encode_ax25_frame(ax_conn[1]))
            print('#######################################################')
            t = time.time()


debug = True
send = False
#print(decode_ax25_frame(bytearray.fromhex("9a8864a682aee088b060a682ae60868460a682aee103f0626c6120303030303030303030303030205445535420544553542044444444444444444444")))
#print("_-------------------------------_")
# print(encode_ax25_frame(ax_conn))

#enc = encode_ax25_frame(ax_conn[1])
#print(decode_ax25_frame(bytes.fromhex(enc)))

#print(decode_ax25_frame(test_data_in))
#print(decode_ax25_frame(bytes.fromhex('a88aa6a8e09a8864a682ae70868460a682aee103f03c205445535420666d204d44325341572028204a4f35324e552029203e')))
#9a8864a682aee088b060a682ae60868460a682aee130xf0626c6120303030303030303030303030205445535420544553542044444444444444444444
#\xc0\x00\xa6\xa8\x82\xa8\xaa\xa6\xe0\x88\xb0`\xa6\x82\xaea\x13\xf0


try:
    read_kiss()
except KeyboardInterrupt:
    print("Ende ..")


