"""
AWS IoT policy helper functions.
"""
import os.path
from string import Template
from logging import getLogger
import json
import boto3
import botocore

from .pyaws_errors import PyawsError
from .aws_cloudformation import MCHP_SANDBOX_ENDPOINT
from .status_codes import STATUS_SUCCESS

ZT_POLICY_NAME = "zt_policy"
ZT_POLICY_TEMPLATE_FILE = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                                       "aws_iot_policies",
                                       ZT_POLICY_NAME + ".json")

def create_policy_mar(profile):
    """
    Creates policy for MAR in AWS cloud

    :param profile: AWS profile name
    :type profile: str
    """
    logger = getLogger(__name__)

    aws_policy_tool = Policy(aws_profile=profile)
    if aws_policy_tool.policy_exists(ZT_POLICY_NAME):
        logger.info("Using existing ZT policy")
    else:
        with open(ZT_POLICY_TEMPLATE_FILE) as template_file:
            aws_policy_tool.create_policy(ZT_POLICY_NAME, template_file.read())

class Policy():
    """
    AWS policy generator

    :param aws_profile: AWS profile to be used.
    :type aws_profile: str
    """
    def __init__(self, aws_profile="default"):
        self.logger = getLogger(__name__)
        try:
            self.aws_session = boto3.session.Session(profile_name=aws_profile)
            self.logger.info("Using AWS profile %s", aws_profile)
            self.aws_iot_client = self.aws_session.client("iot")
        except botocore.exceptions.ProfileNotFound:
            if aws_profile == 'default':
                raise PyawsError(
                    'AWS profile not found. Please make sure you have the AWS CLI installed and run'
                    ' "aws configure" to setup profile.')
            raise PyawsError(
                'AWS profile not found. Please make sure you have the AWS CLI installed and run'
                ' "aws configure --profile {}" to setup profile.'.format(aws_profile))

        self.account_id = boto3.client('sts').get_caller_identity().get('Account')
        self.region = self.aws_session.region_name

    def build_policy(self, policy_template):
        """
        Build a policy document from a template.

        Substitutes $(account_id) and $(region) in the policy template with the account ID and region from
        the AWS profile.

        :param policy_template: Template with placeholders for substituting AWS region and account ID
        :type policy_template: str
        :return: Policy document
        :rtype: str
        """

        policy_template = Template(policy_template)
        policy_document = policy_template.safe_substitute(account_id=self.account_id, region=self.region)
        # TODO need to check policy size. AWS allows minimum length of 1, with a maximum length
        # of 2048, excluding whitespace
        return policy_document

    def get_policy(self, policy_name):
        """
        Get policy ARN

        :param policy_name: Policy name
        :type policy_name: str
        """
        try:
            response = self.aws_iot_client.get_policy(policyName=policy_name)
            return response.get('policyArn')
        except botocore.exceptions.ClientError as myexception:
            if myexception.response['Error']['Code'] == 'ResourceNotFoundException':
                self.logger.info("Policy %s not found in AWS", policy_name)
            return None

    def create_policy(self, policy_name, policy_template):
        """Registers a policy in AWS

        :param policy_name: Name of the policy
        :type policy: str
        :param policy_template: Policy template
        :type policy_template: str
        """
        #Checking endpoint
        iot = boto3.client('iot')
        aws_endpoint = iot.describe_endpoint()["endpointAddress"]
        if aws_endpoint == MCHP_SANDBOX_ENDPOINT:
            raise PyawsError("Please don't use the Microchip Sandbox account for MAR setup")

        policy_document = self.build_policy(policy_template)
        policy_arn = self.get_policy(policy_name=policy_name)
        if policy_arn is None:
            response = self.aws_iot_client.create_policy(policyName=policy_name, policyDocument=policy_document)
            self.logger.info("Created new policy")
            self.logger.info("Policy name: %s", response['policyName'])
            self.logger.info("Policy ARN: %s", response['policyArn'])
            self.logger.info("Policy Version ID: %s", response['policyVersionId'])
            self.logger.info("Policy Document: %s", response['policyDocument'])
        else:
            self.logger.info("Policy %s already exists in AWS IoT", policy_name)

    def create_policy_version(self, policy_name, policy_template, make_default=True):
        """
        Create a new policy version

        :param policy_name: Name for he policy
        :type policy_name: str
        :param policy_template: Policy template
        :type policy_template: str
        :param make_default: True if the new policy version should be set as default/active version, otherwise false
        :type make_default: Boolean, optional
        """
        policy_document = self.build_policy(policy_template)
        try:
            response = self.aws_iot_client.create_policy_version(policyName=policy_name,
                                                                 policyDocument=policy_document,
                                                                 setAsDefault=make_default)
        except botocore.exceptions.ClientError as myexcept:
            self.logger.debug(json.dumps(response, indent=4, sort_keys=True))
            raise PyawsError("Failed to create new policy version, {}".format(myexcept))

        self.logger.info("Created new policy version")
        self.logger.info("Policy ARN: %s", response['policyArn'])
        self.logger.info("Policy Version ID: %s", response['policyVersionId'])
        self.logger.info("Policy is default: %s", response['isDefaultVersion'])
        self.logger.info("Policy Document: %s", response['policyDocument'])

    def policy_exists(self, policy_name):
        """
        Check if a policy exists in AWS account

        :param policy_name: Name of the policy
        :type policy_name: str
        """
        try:
            response = self.aws_iot_client.list_policies()
        except botocore.exceptions.ClientError as myexcept:
            self.logger.debug(json.dumps(response, indent=4, sort_keys=True))
            raise PyawsError("Failed to fetch available policies {}".format(myexcept))

        policy_exists = False
        for policy in response['policies']:
            if policy['policyName'] == policy_name:
                policy_exists = True
        return policy_exists


def policy_cli_handler(args):
    """
    Entry point for policy action of CLI
    """
    logger = getLogger(__name__)

    templatefile = args.policy_template    
    if args.policy_template is None:
        templatefile = ZT_POLICY_TEMPLATE_FILE
        logger.info("Using default template file %s", templatefile)

    with open(templatefile, "r") as myfile:
        policy_template = myfile.read()

    policy_tool = Policy(aws_profile=args.profile)
    logger.info("Creating policy %s with template %s",args.policy_name, templatefile)
    policy_tool.create_policy(args.policy_name, policy_template)

    return STATUS_SUCCESS
