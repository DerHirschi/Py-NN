#data_in = "9a88648484a660ac8462849eb0f2ac8462"
#test_data_in = "9a88648484a6e09a8864a682ae60868460a682aee140f0620d" # Rest 40f0620d
# 9a88648484a6e09a8864a682ae60868460a682aee1 Rest 40f0620d
#data_in = "9a88648484a6e0868460a682ae6151"    # MD2SAW to MD2BBS via CB0SAW* CB0SAW* ctl RR2-
test_data_in = "ae 8aa8 a88a a4e0 8684 60a6 82ae 7c86 8460 a682 ae67 03f0 3c20 5765 7474 6572 2053 616c 7a77 6564 656c 204a 4f35 324e 5520 3e0d 0a20 5465 6d70 2e3a 2020 3231 2e30 2020 430d 0a20 4c75 6674 6472 7563 6b3a 2020 3130 3136 2e36 3731 3220 2068 5061 0d0a 204c 7566 7466 6575 6368 7469 676b 6569 743a 2020 3534 2e38 2020 25"
# CB0SAW-14 to WETTER via CB0SAW-3 ctl UI^ pid=F0(Text) len 103
test_data_in.replace(" ", "")


def decode_ax25_header(data_in):
    ret = {}

    def decode_adress_char(in_byte):    # Convert to 7 Bit ASCII
        bin_char = bin(int(in_byte, 16))[2:].zfill(8)[:-1]
        he = hex(int(bin_char, 2))
        return bytes.fromhex(he[2:]).decode()

    def decode_ssid(in_byte):   # Address > CRRSSID1    Digi > HRRSSID1
        bi = bin(int(in_byte, 16))[2:].zfill(8)
        s_bit = bi[-1]          # Stop Bit      Bit 8
        c_bit = bi[0]           # C bzw H Bit   Bit 1
        ssid_bit = bi[3:-1]     # SSID          Bit 4 - 7
        r_bits = bi[1:3]        # Bit 2 - 3 not used. Free to use for any application .?..
        ssid = int(ssid_bit, 2)
        print("")
        print("----SSID-----: " + in_byte)
        print("Stop_Bit: " + s_bit)
        print("C/H_Bit: " + c_bit)
        print("R_Bit: " + r_bits)
        print("SSID: " + str(ssid))
        return s_bit, c_bit, ssid, r_bits

    def conv_hex(inp):
        return hex(inp)[2:]

    address_str = ""
    tmp_str = ""
    byte_count = 0
    address_field_count = 0
    keys = ["TO", "FROM"]
    end = False
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
                    if tmp[1] == '1':                       # H Bit
                        address_str += "*"
                if tmp[0] == '1':
                    print("Ende Adressbereich")
                    end = True
                '''CALL, int(SSID), H-BIT, R-BITs'''
                ret[keys[address_field_count - 1]] = tmp_str, tmp[2], tmp[1], tmp[3]
                tmp_str = ""
                address_str += " "

        else:
            if byte_count == 1:
                address_str += "  Control: " + str(hex(i)) + " C-Bits: " + str(bin(int(conv_hex(i)))[2:].zfill(8)) + " "
            address_str += str(conv_hex(i))

    print("RES: " + address_str)
    return ret


print(decode_ax25_header(test_data_in))


