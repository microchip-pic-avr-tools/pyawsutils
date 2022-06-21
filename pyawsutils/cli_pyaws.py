"""
pyaws CLI: "pyaws"
"""
import sys
import logging
import argparse
import os
import textwrap

from logging.config import dictConfig
from appdirs import user_log_dir
import yaml
from yaml.scanner import ScannerError

from .mar import mar_cli_handler
from .clean import clean_cli_handler
from .policy import policy_cli_handler
from .aws_cloudformation import jitr_cli_handler

from .status_codes import STATUS_SUCCESS, STATUS_FAILURE

try:
    #pylint: disable=no-name-in-module
    from .version import VERSION, BUILD_DATE, COMMIT_ID
except ImportError:
    print("Version info not found!")
    VERSION = "0.0.0"
    COMMIT_ID = "N/A"
    BUILD_DATE = "N/A"

# Actions requiring signer CA certificate and signer CA key file arguments
ACTIONS_REQUIRING_MAR = ['register-mar']

def setup_logging(user_requested_level=logging.WARNING, default_path='logging.yaml',
                  env_key='MICROCHIP_PYTHONTOOLS_CONFIG'):
    """
    Setup logging configuration for this CLI
    """
 # Logging config YAML file can be specified via environment variable
    value = os.getenv(env_key, None)
    if value:
        path = value
    else:
        # Otherwise use the one shipped with this application
        path = os.path.join(os.path.dirname(__file__), default_path)
    # Load the YAML if possible
    if os.path.exists(path):
        try:
            with open(path, 'rt') as file:
                # Load logging configfile from yaml
                configfile = yaml.safe_load(file)
                # File logging goes to user log directory under Microchip/modulename
                logdir = user_log_dir(__name__, "Microchip")
                # Look through all handlers, and prepend log directory to redirect all file loggers
                num_file_handlers = 0
                for handler in configfile['handlers'].keys():
                    # A filename key
                    if 'filename' in configfile['handlers'][handler].keys():
                        configfile['handlers'][handler]['filename'] = os.path.join(
                            logdir, configfile['handlers'][handler]['filename'])
                        num_file_handlers += 1
                # If file logging is enabled, it needs a folder
                if num_file_handlers > 0:
                    # Create it if it does not exist
                    os.makedirs(logdir, exist_ok=True)
                # Console logging takes granularity argument from CLI user
                configfile['handlers']['console']['level'] = user_requested_level
                # Root logger must be the most verbose of the ALL YAML configurations and the CLI user argument
                most_verbose_logging = min(user_requested_level, getattr(logging, configfile['root']['level']))
                for handler in configfile['handlers'].keys():
                    # A filename key
                    if 'filename' in configfile['handlers'][handler].keys():
                        level = getattr(logging, configfile['handlers'][handler]['level'])
                        most_verbose_logging = min(most_verbose_logging, level)
                configfile['root']['level'] = most_verbose_logging
            dictConfig(configfile)
            return
        except ScannerError:
            # Error while parsing YAML
            print("Error parsing logging config file '{}'".format(path))
        except KeyError as keyerror:
            # Error looking for custom fields in YAML
            print("Key {} not found in logging config file".format(keyerror))
    else:
        # Config specified by environment variable not found
        print("Unable to open logging config file '{}'".format(path))

    # If all else fails, revert to basic logging at specified level for this application
    print("Reverting to basic logging.")
    logging.basicConfig(level=user_requested_level)


def main():
    """
    Entrypoint for installable CLI
    Configures the top-level CLI and parses the arguments
    """

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent('''\
    pyawsutils: a command line interface for Microchip pyawsutils utility

    Basic usage:
        - pyawsutils <action> [-switches]

    Basic actions:
        - create-policy
        - register-mar
        - register-jitr
        - clean 
        '''),
        epilog=textwrap.dedent('''\
    Usage examples:
        Policy example
        - pyawsutils create-policy --policy mypolicy.json --policy-name mypolicy

        MAR example
        - pyawsutils register-mar -c mycertificate.pem --policy-name mypolicy

        MAR example 2
        - pyawsutils register-mar -c mycertificate.pem --policy-name mypolicy --thing-type mythingfolder

        JITR example, registering account
        - pyawsutils register-jitr

        Cleaner example
        - pyawsutils clean 
        '''))


    parser.add_argument("action",
                        help="action to perform",
                        # This makes the action argument optional
                        # only if -V/--version or -R/release_info argument is given
                        nargs="?" if "-V" in sys.argv or "--version" in sys.argv \
                        or "-R"  in sys.argv or "--release-info" in sys.argv else None,
                        default="clean",
                        # nargs='?', # this makes ... the default, and -h the only way to get usage()
                        choices=['register-mar', 'register-jitr', 'create-policy', 'clean'])

    parser.add_argument("-v", "--verbose",
                        default="info", choices=['debug', 'info', 'warning', 'error', 'critical'],
                        help="Logging verbosity level")

    parser.add_argument("-V", "--version",
                        help="Print version number and exit",
                        action="store_true")

    parser.add_argument("-R", "--release-info", action="store_true",
                        help="Print release details and exit")

    parser.add_argument("-P", "--profile", type=str, default="default",
                        help="AWS profile to use")

    # MAR and policy arguments
    parser.add_argument("-p", "--policy-name", type=str, default="zt_policy",
                        help="Policy that should be created or attached to the device certificate."
                        "The policy must exist in AWS or be created by passing a template with --policy-template."
                        "(default: zt_policy)")
    parser.add_argument("--pt", "--policy-template", dest="policy_template", type=str, default=None,
                        help="Policy template file to create and register the policy in AWS."
                        "(default: None)")

    # MAR arguments
    parser.add_argument("--tns", "--thing-name-source", dest="thing_name_source", choices=["ski", "scn"], default="ski",
                        help="Defines what should be used as thing name."
                        "Either Subject Key Identifier (ski) or Subject Common Name (scn)"
                        "(default: ski)")
    parser.add_argument("-t", "--thing-type", type=str, default=None,
                        help="Thing type to use when creating the thing."
                        "If the type does not exist it will be created "
                        "(default: None)")
    parser.add_argument("-c", "--certificate", type=str,
                        help="Certificate in PEM format")
    parser.add_argument("-f", "--file", type=str, default=None,
                        help="File with list of certificates. One certificate per line in the file"
                        "(default: None)")

    # Parse
    args = parser.parse_args()

    # Setup logging
    setup_logging(user_requested_level=getattr(logging, args.verbose.upper()))

    # Dispatch
    if args.version or args.release_info:
        print("pyawsutils version {}".format(VERSION))
        if args.release_info:
            print("Build date:  {}".format(BUILD_DATE))
            print("Commit ID:   {}".format(COMMIT_ID))
            print("Installed in {}".format(os.path.abspath(os.path.dirname(__file__))))
        return STATUS_SUCCESS

    if args.action == "register-mar":
        return mar_cli_handler(args)
    if args.action == "clean":
        return clean_cli_handler(args)
    if args.action == "register-jitr":
        return jitr_cli_handler()
    if args.action == "create-policy":
        return policy_cli_handler(args)

    return STATUS_FAILURE

if __name__ == "__main__":
    sys.exit(main())
