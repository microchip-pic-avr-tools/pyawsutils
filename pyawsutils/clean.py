"""
AWS Cleaner utility
"""

from logging import getLogger
import boto3
import botocore

from .pyaws_errors import PyawsError
from .status_codes import STATUS_SUCCESS, STATUS_FAILURE

class AccountCleaner():
    """
    AWS account cleanup helper tool

    :param aws_profile: AWS profile to be used
    :type aws_profile: str
    """
    def __init__(self, aws_profile="default"):
        self.logger = getLogger(__name__)
        try:
            aws_session = boto3.session.Session(profile_name=aws_profile)
            self.logger.info("Using AWS profile %s", aws_profile)
        except botocore.exceptions.ProfileNotFound:
            if aws_profile == 'default':
                raise PyawsError(
                    'AWS profile not found. Please make sure you have the AWS CLI installed and run'
                    ' "aws configure" to setup profile.')
            raise PyawsError(
                'AWS profile not found. Please make sure you have the AWS CLI installed and run'
                ' "aws configure --profile {}" to setup profile.'.format(aws_profile))

        self.aws_iot = aws_session.client("iot")
        self.account_id = boto3.client('sts').get_caller_identity().get('Account')
        self.region = aws_session.region_name

    def detach_principals_from_thing(self, thingName):
        """
        Detaches the specified principal from the specified thing

        :param thingName: Name for the thing
        :type thingName: str
        """
        response = self.aws_iot.list_thing_principals(thingName=thingName)
        for principal in response['principals']:
            self.aws_iot.detach_thing_principal(thingName=thingName, principal=principal)

    def cleanup(self):
        """
        Delete things, certificates and policies
        """
        self.logger.info("Cleaning...")
        self.delete_things()
        self.delete_certificates()
        self.delete_policies()

    def fast_cleanup(self):
        """
        Detach policy from certificates. Delete things and certificates
        """
        self.detach_policy_from_certificates()
        self.delete_things()
        self.delete_certificates()

    def delete_things(self, bulk_delete_size=20):
        """
        Deleta all the things

        :param bulk_delete_size: bulk size, defaults to 20
        :type bulk_delete_size: int, optional
        """
        marker = ""
        while True:
            response = self.aws_iot.list_things(maxResults=bulk_delete_size, nextToken=marker)

            for thing in response['things']:
                self.detach_principals_from_thing(thing['thingName'])
                self.aws_iot.delete_thing(thingName=thing['thingName'])
                self.logger.info(("Deleted thing %s", thing['thingArn']))

            if not hasattr(response, 'nextToken'):
                break
            marker = response['nextToken']

    def detach_policy_from_certificates(self, policyName="zt_policy"):
        """
        Detach policy from all certificates

        :param policyName: optional; default is "zt_policy"
        :type policyName: str
        """
        arn = "arn:aws:iot:{}:{}:cert/*".format(self.region, self.account_id)
        self.logger.info(arn)
        self.aws_iot.detach_policy(policyName=policyName, target=arn)

    def delete_certificates(self, bulk_delete_size=20):
        """
        Delete all certificates from current AWS account

        A certificate cannot be deleted if it has a policy or IoT thing attached to it or if its status
        is set to ACTIVE.

        :param bulk_delete_size: bulk size, defaults to 20
        :type bulk_delete_size: int, optional
        """
        marker = ""
        while True:
            response = self.aws_iot.list_certificates(pageSize=bulk_delete_size, marker=marker)
            for certificate in response['certificates']:
                self.detach_policies_from_certificate(certificate['certificateArn'])
                self.aws_iot.update_certificate(certificateId=certificate['certificateId'], newStatus='INACTIVE')
                self.aws_iot.delete_certificate(certificateId=certificate['certificateId'])
                self.logger.info(("Deleted certificate %s", certificate['certificateArn']))
            if not hasattr(response, "nextMarker"):
                break
            marker = response['nextMarker']

    def delete_policies(self, bulk_delete_size=20):
        """
        Delete all iot policies from current AWS account
        
        :param bulk_delete_size: bulk size, defaults to 20
        :type bulk_delete_size: int, optional
        """

        marker = ""
        while True:
            response = self.aws_iot.list_policies(pageSize=bulk_delete_size, marker=marker)
            for mypolicy in response['policies']:
                self.aws_iot.delete_policy(policyName=mypolicy['policyName'])
                self.logger.info("Deleted policy %s", mypolicy['policyName'])
            if not hasattr(response, "nextMarker"):
                break
            marker = response['nextMarker']

    def detach_policies_from_certificate(self, certificateArn, bulk_detach_size=20):
        """
        Detach all policies from a certificate

        :param certificateArn: Arn for the certificate
        :type certificateArn: str
        :param bulk_detach_size: bulk size, defaults to 20
        :type bulk_delete_size: int, optional
        """
        marker = ""
        while True:
            response = self.aws_iot.list_attached_policies(target=certificateArn,
                                                           pageSize=bulk_detach_size, marker=marker)
            for policy in response['policies']:
                self.aws_iot.detach_policy(policyName=policy['policyName'], target=certificateArn)
                self.logger.info(("Detached policy %s from certificate %s", policy['policyName'], certificateArn))
            if not hasattr(response, "nextMarker"):
                break
            marker = response['nextMarker']

def clean_cli_handler(args):
    """
    Entry point for clean command of CLI
    """

    cleaner = AccountCleaner(aws_profile=args.profile)
    cleaner.cleanup()

    return STATUS_SUCCESS
