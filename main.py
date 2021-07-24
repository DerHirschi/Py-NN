import crcmod.predefined
from binascii import unhexlify
#data_in = "9a88648484a660ac8462849eb0f2ac8462"
#test_data_in = "9a88648484a6e09a8864a682ae60868460a682aee140f0620d" # Rest 40f0620d  ### I Frame
# 9a88648484a6e09a8864a682ae60868460a682aee1 Rest 40f0620d
#test_data_in = "9a88648484a6e0868460a682ae6151"    # MD2SAW to MD2BBS via CB0SAW* CB0SAW* ctl RR2-
test_data_in = "ae 8aa8 a88a a4e0 8684 60a6 82ae 7c86 8460 a682 ae67 03f0 3c20 5765 7474 6572 2053 616c 7a77 6564 656c 204a 4f35 324e 5520 3e0d 0a20 5465 6d70 2e3a 2020 3231 2e30 2020 430d 0a20 4c75 6674 6472 7563 6b3a 2020 3130 3136 2e36 3731 3220 2068 5061 0d0a 204c 7566 7466 6575 6368 7469 676b 6569 743a 2020 3534 2e38 2020 25"
test_data_in_b = b"ae8aa8a88aa4e0868460a682ae7c868460a682ae6703f03c205765747465722053616c7a776564656c204a4f35324e55203e0d0a2054656d702e3a202032312e302020430d0a204c756674647275636b3a2020313031362e3637313220206850610d0a204c75667466657563687469676b6569743a202035342e38202025"
# CB0SAW-14 to WETTER via CB0SAW-3 ctl UI^ pid=F0(Text) len 103
test_data_in = test_data_in.replace(" ", "")


def decode_ax25_header(data_in):
    ret = {
        "TO": '',
        "FROM": '',
        "ctl": (),
        "pid": ()
        # DIGI1..8
    }

    def bin2bl(inp):
        return bool(int(inp))

    def conv_hex(inp):
        return hex(inp)[2:]

    def decode_adress_char(in_byte):    # Convert to 7 Bit ASCII
        bin_char = bin(int(in_byte, 16))[2:].zfill(8)[:-1]
        he = hex(int(bin_char, 2))
        return bytes.fromhex(he[2:]).decode()

    def decode_ssid(in_byte):       # Address > CRRSSID1    Digi > HRRSSID1
        bi = bin(int(in_byte, 16))[2:].zfill(8)
        s_bit = bin2bl(bi[7])       # Stop Bit      Bit 8
        c_bit = bin2bl(bi[0])       # C bzw H Bit   Bit 1
        ssid = int(bi[3:7], 2)      # SSID          Bit 4 - 7
        r_bits = bi[1:3]            # Bit 2 - 3 not used. Free to use for any application .?..
        '''
        print("")
        print("----SSID-----: " + in_byte)
        print("Stop_Bit: " + s_bit)
        print("C/H_Bit: " + c_bit)
        print("R_Bit: " + r_bits)
        print("SSID: " + str(ssid))
        '''
        return s_bit, c_bit, ssid, r_bits

    def decode_c_byte(in_byte):
        def bl2str(inp):
            if inp:
                return '-'
            else:
                return '+'

        res = []
        ctl_str = ""
        pid = False
        bi = bin(int(in_byte, 16))[2:].zfill(8)
        pf = bin2bl(bi[3])                                                          # P/F
        if not bin2bl(bi[-1]):                              # I-Block   Informationsübertragung
            res.append("I")
            res.append([])
            nr = int(bi[:3], 2)
            ns = int(bi[4:7], 2)
            res[1].append(nr)                                                       # N(R)
            res[1].append(pf)                                                       # P
            res[1].append(ns)                                                       # N(S)
            ctl_str = "I" + str(nr) + bl2str(pf)
            pid = True
        elif not bin2bl(bi[-2]) and bin2bl(bi[-1]):         # S-Block
            res.append("S")
            res.append([])
            nr = int(bi[:3], 2)
            ss_bits = bi[4:6]
            res[1].append(nr)                                                       # N(R)
            res[1].append(pf)                                                       # P/F
            res[1].append(ss_bits)                                                  # S S Bits
            if ss_bits == '00':                                         # Empfangsbereit RR
                ctl_str = "RR" + str(nr) + bl2str(pf)                               # P/F Bit add +/-
            elif ss_bits == '01':                                       # Nicht empfangsbereit RNRR
                ctl_str = "RNRR" + bl2str(pf)                                       # P/F Bit add +/-
            elif ss_bits == '10':                                       # Wiederholungsaufforderung REJ
                ctl_str = "REJ" + bl2str(pf)                                        # P/F Bit add +/-
            else:
                ctl_str = "S-UNKNOW"

        elif bin2bl(bi[-2]) and bin2bl(bi[-1]):             # U-Block
            res.append("U")
            res.append([])
            mmm = bi[0:3]
            mm = bi[4:6]
            res[1].append(mmm)                                                      # M M M
            res[1].append(pf)                                                       # P/F
            res[1].append(mm)                                                       # M M
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

    def calc_fcs(fcs):
        # Source:
        def crc16(data: bytes, poly=0x1021):
            '''
            CRC-16-CCITT Algorithm
            '''
            data = bytearray(data)
            crc = 0xFFFF
            # crc = 0x2025
            for b in data:
                cur_byte = 0xFF & b
                for _ in range(0, 8):
                    if (crc & 0x0001) ^ (cur_byte & 0x0001):
                        crc = (crc >> 1) ^ poly
                    else:
                        crc >>= 1
                    cur_byte >>= 1
            crc = (~crc & 0xFFFF)
            crc = (crc << 8) | ((crc >> 8) & 0xFF)

            return crc & 0xFFFF



        # data = data_in[:-2]
        crc_clc = crc16(test_data_in[:-4].encode())
        # crc = crc16("123456789".encode())
        print(crc_clc)
        print(str(hex(crc_clc)))

        print("CRC Bytes in: " + str(fcs))
        print("CRC len in: " + str(len(fcs)))
        print("CRC Int in: " + str(int(fcs.encode(), 16)))
        print("CRC: " + str(bin(int(fcs[0:2], 32))[2:]) + str(bin(int(fcs[2:], 32))[2:]))
        print(bin(crc_clc)[2:])
        # print("CRC: " + str(int(fcs, 32)))
        print(test_data_in.encode())
        #crc = crcmod.Crc(test_data_in)
        #print(str(crc))

    address_str = ""
    tmp_str = ""
    byte_count = 0
    address_field_count = 0
    keys = ["TO", "FROM"]
    end = False
    ctl = ()
    fcs = ""

    for i in bytes.fromhex(data_in):
        byte_count += 1
        if not end:                                         # decode Address fields
            if byte_count != 7:                             # 7 Byte Address Chars
                tmp = decode_adress_char(conv_hex(i))
                address_str += tmp
                tmp_str += tmp
            else:                                           # 8 th Byte SSID (CRRSSID1)
                tmp = decode_ssid(conv_hex(i))
                address_field_count += 1
                byte_count = 0
                address_str += "-"
                address_str += str(tmp[2])
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
                ctl = decode_c_byte(conv_hex(i))
                ret['ctl'] = ctl
                tmp_str += "  Control: " + str(hex(i)) + " C-Bits: " + str(bin(int(conv_hex(i)))[2:].zfill(8)) + " "
            # tmp_str += str(conv_hex(i))
            elif byte_count == 2:   # PID Byte in UI and I Frames
                if ctl[1][-2]:
                    ret["pid"] = decode_pid_byte(conv_hex(i))

    calc_fcs(data_in[-4:])
    '''
    elif byte_count in [3, 4] and not ctl[1][-2]:   # FCS in not UI or I Frame
        fcs += conv_hex(i)
        if byte_count == 4:
            calc_fcs(fcs)
    '''

    print("RES: " + address_str + tmp_str)
    return address_str, ret


print(decode_ax25_header(test_data_in))


