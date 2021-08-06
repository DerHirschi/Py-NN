import time
from datetime import datetime
# Gibt Monitor Daten in Datei aus. Datei mit "tail -f" im tmux aufrufen und gut..
mon_f = 'mon.txt'
debug_f = 'debug.txt'
error_f = 'error.txt'
debug = True


def monitor(data):
    db_c = 0
    if debug:
        db_c = 1

    f = open(mon_f, 'a')
    out = ''
    now = datetime.now()  # current date and time
    out += now.strftime("%d/%m/%Y %H:%M:%S> ")
    if len(data['FROM']) != 0:
        out += data['FROM'][0].replace(' ', '')
        if data['FROM'][1]:
            out += '-' + str(data['FROM'][1])
        out += '>' + data['TO'][0].replace(' ', '')
        if data['TO'][1]:
            out += '-' + str(data['TO'][1])
        if 'DIGI1'in data.keys():
            out += ' via '
        n = 1
        for k in data.keys():
            if 'DIGI' in str(k):
                dig = 'DIGI' + str(n)
                out += data[dig][0].replace(' ', '')
                if data[dig][1]:
                    out += '-' + str(data[dig][1])
                    if data[dig][2]:
                        out += '*'
                out += ' '
                n += 1

        if data['pid']:
            out += ' [' + data['pid'][0] + ']'
        out += ' ('

        out += data['ctl']['type']
        out += ' ' + str(data['ctl']['pf'])
        if data['ctl']['nr'] != -1:
            out += ' ' + str(data['ctl']['nr'])
        if data['ctl']['ns'] != -1:
            out += ' ' + str(data['ctl']['ns'])
        if data['ctl']['cmd']:
            out += ' ' + 'cmd'
        else:
            out += ' ' + 'res'
        if debug:
            out += ' ' + str(data['ctl']['hex'])
        out += ') ' + data['ctl']['ctl_str']
        if data['data'][1]:
            out += ' (len:' + str(data['data'][1]) + ')'
            out = out.replace('  ', ' ')
            out += '\r\n'
            d = b''
            if b'\r\n' not in data['data']:
                d = data['data'][0].replace(b'\r', b'\r\n').decode('UTF-8', errors='ignore')
            else:
                d = data['data'][0].decode('UTF-8', errors='ignore')
            if d[-2:] == '\r\n':
                out += d[:-2]
            else:
                out += d

        f.write(out + '\r\n')
        f.close()


def debug_out(in_str, error=False):
    if debug:
        f = ''
        if error:
            f = open(error_f, 'a')
        else:
            f = open(debug_f, 'a')
        out = ''
        now = datetime.now()  # current date and time
        out += now.strftime("%d/%m/%Y %H:%M:%S> ") + str(in_str) + '\r\n'
        f.write(out)
        f.close()
