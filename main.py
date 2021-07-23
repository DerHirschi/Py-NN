#data_in = "9a88648484a660ac8462849eb0f2ac8462"
#data_in = "9a88648484a6e09a8864a682ae60868460a682aee140f0620d" # Rest 40f0620d
# 9a88648484a6e09a8864a682ae60868460a682aee1 Rest 40f0620d
#data_in = "9a88648484a6e0868460a682ae6151"    # MD2SAW to MD2BBS via CB0SAW* CB0SAW* ctl RR2-
test_data_in = "ae 8aa8 a88a a4e0 8684 60a6 82ae 7c86 8460 a682 ae67 03f0 3c20 5765 7474 6572 2053 616c 7a77 6564 656c 204a 4f35 324e 5520 3e0d 0a20 5465 6d70 2e3a 2020 3231 2e30 2020 430d 0a20 4c75 6674 6472 7563 6b3a 2020 3130 3136 2e36 3731 3220 2068 5061 0d0a 204c 7566 7466 6575 6368 7469 676b 6569 743a 2020 3534 2e38 2020 25"
# CB0SAW-14 to WETTER via CB0SAW-3 ctl UI^ pid=F0(Text) len 103
test_data_in.replace(" ", "")


def decode_ax25(data_in):

    def decode_adress_char(in_byte):
        bi = bin(int(in_byte, 16))[2:].zfill(8)
        bin_char = bi[:-1]
        he = hex(int(bin_char, 2))
        asc = bytes.fromhex(he[2:]).decode()
        print("")
        print("----CALL-----: " + in_byte)
        print("Bin: " + bin_char)
        print("Hex: " + he)
        print("Char: " + asc)
        print("")

        return asc

    def decode_ssid(in_byte):
        bi = bin(int(in_byte, 16))[2:].zfill(8)
        s_bit = bi[-1]          # Stop Bit
        c_bit = bi[0]           # C bzw H Bit
        ssid_bit = bi[3:-1]
        ssid = int(ssid_bit, 2)
        print("")
        print("----SSID-----: " + in_byte)
        print("Stop_Bit: " + s_bit)
        print("C/H_Bit: " + c_bit)
        print("SSID_Bit: " + ssid_bit)
        print("SSID: " + str(ssid))
        print("")
        return s_bit, c_bit, ssid

    out = ""
    c = 1
    d = 1
    for i in bytes.fromhex(data_in):
        # print(hex(i)[2:])

        if c != 7:
            out += decode_adress_char(hex(i)[2:])
        else:
            tmp = decode_ssid(hex(i)[2:])
            c = 0
            out += "-"
            out += str(tmp[2])
            if d > 2 and tmp[1] == '1':     # H Bit (DIGIpeated)
                out += "*"
            if tmp[0] == '1':
                print("Ende Adressbereich")
                break
            d += 1
            out += " "
        c += 1

    print("RES: " + out)

decode_ax25(test_data_in)
