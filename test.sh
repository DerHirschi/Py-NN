#!/bin/bash
sudo socat -d -d pty,link=/tmp/ptyAX5,raw,echo=0 pty,link=/tmp/ptyAX5-Dummy,raw,echo=0 &
sleep 2
sudo kissattach /tmp/ptyAX5-Dummy ax5
sleep 2
sudo rxecho


#rm /tmp/ptyAX5*
#pkill rxecho
