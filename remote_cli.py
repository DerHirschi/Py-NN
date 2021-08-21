from config import *


def cli_node_init(conn_obj):
    pass


def init_cli(conn_obj):
    if conn_obj.cli_type:
        {
            1: cli_node_init,
            9: cli_test_init,
        }[conn_obj.cli_type](conn_obj)
    else:
        conn_obj.handle_cli_inp = handle_cli_inp_none

#################################################
# Test CLI


def cli_test_init(conn_obj):
    # Func
    conn_obj.handle_cli_inp = handle_cli_inp_test


def handle_cli_inp_test(slf):
    inp = slf.rx_data



def handle_cli_inp_none(slf):
    pass
