import logging
import argparse

from .server import DashboardServer
from .objects import register_object_types

parser = argparse.ArgumentParser(
    prog='ThunderBoard',
    description='Web-based real-time data display platform designed for experiment monitoring.',
    add_help=True
)

parser.add_argument(
    '-v', '--verbose',
    dest='verbose',
    action='store_true',
    help='Increase verbosity of log message.'
)

parser.add_argument(
    '-q', '--quiet',
    dest='quiet',
    action='store_true',
    help='Suppress non-error messages.'
)

parser.add_argument(
    '-di', '--dashboard-ip',
    dest='web_ip',
    type=str,
    default='0.0.0.0',
    help='IP address or hostname the dashboard server will listen on. Default: 0.0.0.0 (All addresses)'
)

parser.add_argument(
    '-dp', '--dashboard-port',
    dest='web_port',
    type=int,
    default=2334,
    help='Port the dashboard server will listen on. Default: 2334'
)

parser.add_argument(
    '-ri', '--receive-ip',
    dest='recv_ip',
    type=str,
    default='0.0.0.0',
    help='IP address or hostname the data receiving server will listen on. Default: 0.0.0.0 (All addresses)'
)

parser.add_argument(
    '-rp', '--receive-port',
    dest='recv_port',
    type=int,
    default=2333,
    help='Port the data receiving server will listen on. Default: 2333'
)

args = parser.parse_args()

def serve():
    logger = logging.getLogger()
    formatter = logging.Formatter('[%(asctime)s %(levelname)s %(threadName)s] %(message)s', "%b %d %H:%M:%S")

    logger.setLevel(logging.INFO)
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    elif args.quiet:
        logger.setLevel(logging.ERROR)

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    server = DashboardServer(args.recv_ip, args.recv_port, args.web_ip, args.web_port)
    register_object_types(server)
    server.serve()
