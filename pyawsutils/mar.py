"""
AWS multi account registration (MAR)
"""

import binascii
from logging import getLogger
import boto3
import botocore
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from pytrustplatform.cert_get_data import cert_get_skid, create_cert_fingerprint, cert_get_common_name
from .policy import Policy
from .pyaws_errors import PyawsError
from .status_codes import STATUS_SUCCESS, STATUS_FAILURE

class aws_mar():
    """
    AWS Multi Account Registration

    :param aws_profile: AWS profile to be used.
    :type aws_profile: str
    """
    def __init__(self, aws_profile="default"):
        self.logger = getLogger(__name__)
        try:
            aws_session = boto3.session.Session(profile_name=aws_profile)
        except botocore.exceptions.ProfileNotFound:
            if aws_profile == 'default':
                raise Exception(
                    'AWS profile not found. Please make sure you have the AWS CLI installed and run'
                    ' "aws configure" to setup profile.')
            raise Exception(
                'AWS profile not found. Please make sure you have the AWS CLI installed and run'
                ' "aws configure --profile {}" to setup profile.'.format(aws_profile))
        self.aws_iot = aws_session.client("iot")

    def register_certificate(self, certificate, status='ACTIVE'):
        """
        Registers a device certificate in AWS by using MAR.

        :param certificate: Device certificate in PEM format.
        :type certificate: str
        :param status: Certificate status that should be set e.g. ACTIVE, INACTIVE ...
        :type status: str, optional
        """
        try:
            response = self.aws_iot.register_certificate_without_ca(
                certificatePem=certificate, status=status)
            certificate_arn = response['certificateArn']
            self.logger.info("Registered certificate")
        except botocore.exceptions.ClientError as myexcept:
            if myexcept.response["Error"]["Code"] == "ResourceAlreadyExistsException":
                self.logger.info("Certificate already registered")
                certificate_id = self.create_cert_fingerprint(certificate)
                response = self.aws_iot.describe_certificate(certificateId=certificate_id)
                certificate_arn = response['certificateDescription']['certificateArn']
            else:
                raise myexcept

        return certificate_arn

    def create_cert_fingerprint(self, certificate):
        """
        Create a fingerprint of a certificate.

        :param certificate: Certificate in PEM format
        :type certificate: str
        :return: Certificate fingerprint (SHA256 of DER encoded certificate).
                 ASCII encoded hex string with 40 lower case characters
        :rtype: str
        """
        cert = x509.load_pem_x509_certificate(data=certificate.encode(encoding="utf-8"), backend=default_backend())
        fingerprint = cert.fingerprint(hashes.SHA256())

        return binascii.b2a_hex(fingerprint).decode('ascii')

    def create_thing(self, thing_name, thing_type=None):
        """
        Create a thing in AWS IoT

        :param thing_name: Name for the thing
        :type thing_name: str
        :param thing_type: Thing type to assign the thing to. Will create the type if it does not exist.
        :type thing_type: str
        """
        try:
            if thing_type is not None:
                # Try to create the thing type. Will not throw and error if the type already exists
                self.aws_iot.create_thing_type(thingTypeName=thing_type)
                response = self.aws_iot.create_thing(thingName=thing_name, thingTypeName=thing_type)
            else:
                # Will not throw an exception if an existing thing has the exact configuration
                response = self.aws_iot.create_thing(thingName=thing_name)
            self.logger.debug("Created thing %s. ARN %s", thing_name, response["thingArn"])
        except botocore.exceptions.BotoCoreError as myexcept:
            raise PyawsError("Failed to create thing {}".format(myexcept))

    def combine_everything(self, thing_name, policy_name, certificate_arn):
        """
        Attach policy to certificate and certificate to thing.

        :param thing_name: Name of the thing where the certificate should be attached to
        :type thing_name: str
        :param policy_name: Name of the policy that should be attached to the certificate
        :type policy_name: str
        :param certificate_arn: Amazon Resource Name (ARN) of the certificate
        :type certificate_arn: str
        """
        self.aws_iot.attach_policy(
            policyName=policy_name, target=certificate_arn)
        self.logger.info("Attached policy %s to certificate %s", policy_name, certificate_arn)
        self.aws_iot.attach_thing_principal(
            thingName=thing_name, principal=certificate_arn)
        self.logger.info("Attached certificate to thing.")

    def activate_certificate(self, certificate_arn):
        """
        Activate a certificate in AWS

        :param certificate_arn: AWS ARN for the certificate
        :type certificate_arn: str
        """
        certificate_id = certificate_arn.rsplit(":")[1]
        self.aws_iot.update_certificate(
            certificateId=certificate_id, newStatus='ACTIVE')

    def create_device(self, certificate_file, policy_name="zt_policy", thing_type=None, thing_name_source="ski"):
        """
        Register a device in AWS IoT by using multi account registration (MAR)

        :param certificate_file: Certificate file name including path
        :type certificate_file: str
        :param policy_name: Name of the policy that should be attached
        :type policy_name: str, optional
        :param thing_type: Thing type that should be attached
        :type thing_name: str, optional
        :param thing_name_source: What to use as thing name in AWS from the certificate
                                ski=Subject Key identifier or scn=Subject Common Name
        :type thing_name_source: str, optional
        """
        with open(certificate_file, "r") as myfile:
            client_certificate = myfile.read()

        if thing_name_source == "ski":
            thing_name = cert_get_skid(certificate_file)
            self.logger.debug("Thing name from subject key identifier is %s", thing_name)
        else:
            thing_name = cert_get_common_name(certificate_file)
            self.logger.debug("Thing name from subject common name is %s", thing_name)

        aws_certificate_arn = self.register_certificate(client_certificate)
        self.logger.debug("Certificate ARN: %s", aws_certificate_arn)
        self.create_thing(thing_name, thing_type)
        self.combine_everything(thing_name, policy_name, aws_certificate_arn)

def mar_cli_handler(args):
    """
    Entry point for MAR command of CLI
    """
    logger = getLogger(__name__)
    certificates = []

    if args.certificate is None and args.file is None:
        logger.info("No certificate(s) to register. Use argument -c or -f to list certificate(s). See help with argument --help.")    
        return STATUS_FAILURE

    if args.certificate is not None:
        certificates.append(args.certificate)

    if args.file is not None:
        with open(args.file, "r") as myfile:
            certificates += myfile.read().splitlines()

    aws_mar_tool = aws_mar(args.profile)

    if args.policy_template is not None:
        with open(args.policy_template, "r") as policy_template_file:
            policy_template = policy_template_file.read()
        aws_policy_tool = Policy(aws_profile=args.profile)
        aws_policy_tool.create_policy(args.policy_name, policy_template)

    logger.info("Registering MAR certificates to AWS...")
    for certificate in certificates:
        logger.info("Registering device from certificate %s", certificate)
        aws_mar_tool.create_device(certificate, policy_name=args.policy_name, thing_type=args.thing_type,
                                   thing_name_source=args.thing_name_source)

    return STATUS_SUCCESS
