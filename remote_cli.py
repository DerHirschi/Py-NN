from config import *
from ax25PacHandl import ax_conn


class CliNode:
    pass


class CliTest:
    pass


def init_cli(conn_obj):
    if conn_obj.cli_type:
        conn_obj.cli_inz = {
            1: CliNode,
            9: CliTest,
        }[conn_obj.cli_type]()


def handle_cli_inp():

    for obj in ax_conn:
        if obj.cli_type:
            if not obj.cli_inz:
                {
                    1: cli_node,
                    9: cli_test,
                }[obj.cli_type]()
