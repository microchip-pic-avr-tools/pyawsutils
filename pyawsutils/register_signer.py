"""
This module enables registering a signer in the AWS cloud
"""
from logging import getLogger
import re
import boto3
import botocore
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

from pytrustplatform.verification_cert_builder import build_verification_cert


_crypto_be = default_backend()

def _datetime_to_iso8601(datetime_value):
    timezone_value = datetime_value.strftime('%z')
    if timezone_value:
        # Add colon between timezone minutes and seconds
        timezone_value = timezone_value[0:3] + ':' + timezone_value[3:6]
    return datetime_value.strftime("%Y-%m-%dT%H:%M:%S") + timezone_value


def _all_datetime_to_iso8601(datetime_value):
    """Traverse a dict or list and convert all datetime objects to ISO8601 strings."""
    if isinstance(datetime_value, dict):
        for key, value in datetime_value.items():
            if hasattr(value, 'strftime'):
                datetime_value[key] = _datetime_to_iso8601(value)
            if isinstance(value, (dict, list)):
                datetime_value[key] = _all_datetime_to_iso8601(value)
    elif isinstance(datetime_value, list):
        for i in range(len(datetime_value)):
            if hasattr(datetime_value[i], 'strftime'):
                datetime_value[i] = _datetime_to_iso8601(datetime_value[i])
            if isinstance(datetime_value[i], (dict, list)):
                datetime_value[i] = _all_datetime_to_iso8601(datetime_value[i])
    return datetime_value


def register_signer(signer_ca_key_path, signer_ca_cert_path, signer_ca_ver_cert_path, aws_profile='default'):
    """
    Register signer in the AWS cloud

    :param signer_ca_key_path: Signer CA key file (full path)
    :type signer_ca_key_path: str
    :param signer_ca_cert_path: Signer CA certificate file (full path)
    :type signer_ca_cert_path: str
    :param signer_ca_ver_cert_path: Signer CA verification certificate (full path)
    :type signer_ca_ver_cert_path: str
    :param aws_profile: AWS profile to use, defaults to 'default'
    :type aws_profile: str, optional
    """
    logger = getLogger(__name__)
    # Read the signer CA certificate to be registered with AWS IoT
    logger.info('Reading signer CA certificate file, %s', signer_ca_cert_path)
    with open(signer_ca_cert_path, 'rb') as certfile:
        signer_ca_cert = x509.load_pem_x509_certificate(certfile.read(), _crypto_be)

    # Create an AWS session with the credentials from the specified profile
    logger.info('Initializing AWS IoT client')
    try:
        aws_session = boto3.session.Session(profile_name=aws_profile)
    except botocore.exceptions.ProfileNotFound as error:
        if aws_profile == 'default':
            raise RuntimeError('AWS profile not found. '
                               'Please make sure you have the AWS CLI installed and '
                               'run "aws configure" to setup profile.')

        raise RuntimeError('AWS profile not found. '
                           'Please make sure you have the AWS CLI installed and '
                           'run "aws configure --profile {}" to setup profile.'.format(aws_profile))

    # Create a client to the AWS IoT service
    aws_iot = aws_session.client('iot')
    logger.info('    Profile:  %s', aws_session.profile_name)
    logger.info('    Region:   %s', aws_session.region_name)
    logger.info('    Endpoint: %s', aws_iot._endpoint)

    # Request a registration code required for registering a CA certificate (signer)
    logger.info('Getting CA registration code from AWS IoT')
    reg_code = aws_iot.get_registration_code()['registrationCode']
    logger.info('    Code: %s', reg_code)

    # Generate a verification certificate around the registration code (subject common name)
    logger.info('Generating signer CA AWS verification certificate')
    signer_ca_ver_cert = build_verification_cert(signer_ca_cert_path,
                                                 signer_ca_key_path,
                                                 reg_code,
                                                 signer_ca_ver_cert_path)

    logger.info('Registering signer CA with AWS IoT')
    try:
        # TODO: Provide options when this fails (already exists, too many CAs with same name, etc...)
        response = aws_iot.register_ca_certificate(
            caCertificate=signer_ca_cert.public_bytes(encoding=serialization.Encoding.PEM).decode('ascii'),
            verificationCertificate=signer_ca_ver_cert.public_bytes(encoding=serialization.Encoding.PEM).decode('ascii'),
            setAsActive=True,
            allowAutoRegistration=True)
        ca_id = response['certificateId']
    except botocore.exceptions.ClientError as error:
        if error.response['Error']['Code'] == 'ResourceAlreadyExistsException':
            logger.info('    This CA certificate already exists in AWS IoT')
            ca_id = re.search('ID:([0-9a-zA-Z]+)', error.response['Error']['Message']).group(1)
        else:
            raise
    logger.info('    ID: %s', ca_id)

    logger.info('Getting AWS IoT device endpoint')
    response = aws_iot.describe_ca_certificate(certificateId=ca_id)
    # Replace the response datetime objects with an ISO8601 string so the dict is json serializable
    _all_datetime_to_iso8601(response)
