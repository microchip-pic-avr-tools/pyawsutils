# pyawsutils
pyawsutils is a collection of utilities for interacting with Amazon Web Services.

![PyPI - Format](https://img.shields.io/pypi/format/pyawsutils)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/pyawsutils)
![PyPI - License](https://img.shields.io/pypi/l/pyawsutils)

## Overview
pyawsutils is available:

* install using pip from pypi: https://pypi.org/project/pyawsutils
* browse source code on github: https://github.com/microchip-pic-avr-tools/pyawsutils
* read API documentation on github: https://microchip-pic-avr-tools.github.io/pyawsutils
* read the changelog on github: https://github.com/microchip-pic-avr-tools/pyawsutils/blob/main/CHANGELOG.md

## Usage
pyawsutils is intended as a library but could also be used stand-alone as a CLI. Its primary consumer is iotprovision.
Make sure you have the AWS CLI installed and run aws configure first to setup your profile.

## Command-line interface
pyawsutils has 4 actions with different options. See help and examples below for more details.

Getting help:
```bash
pyawsutils --help
```

#### register-mar action
The register-mar action supports AWS Multi account registration(MAR) of your device certificate(s) with your AWS profile.

Example:
```bash
pyawsutils register-mar -c mycertificate.pem --policy-name mypolicy
```

#### register-jitr action
The register-jitr action setup an AWS account for Just in time registration(JITR) with your AWS profile. A cloudformation stack(MCHPStack) is created including a lambda function that registers the device when it connects for the first time.

Example:
```bash
pyawsutils register-jitr
```

#### create-policy action
The create-policy action lets you create policies that can be used with your MAR setup and AWS IoT account.

Example:
```bash
pyawsutils create-policy --policy mypolicy.json --policy-name mypolicy
```

#### Clean action
The clean action let you delete all device certificates, things and policies in an AWS IoT account with your AWS profile. Note: CA certificates are not deleted. Other services like cloudformation stacks are also not deleted.

Example:
```bash
pyawsutils clean
```


## Library
pyawsutils can be used as a library by instantiating any of the contained classes.


### Register device for custom provisioning with MAR
The `mar` module enables registering a device in AWS by using multi account registration(MAR). The `policy` module contains policy helper functions. For example:

```python
from pyawsutils.mar import aws_mar
from pyawsutils.policy import Policy

device_cert_file = "my_device.crt"
my_policy = "my_policy"
templatefile = "my_policytemplate.json"

# Read policy template file
with open(templatefile, "r") as myfile:
    policy_template = myfile.read()

# Create AWS policy
aws_policy_tool = Policy()
aws_policy_tool.create_policy(my_policy, policy_template)

# Register device certificate without CA for custom provisioning with MAR.
aws_mar_tool = aws_mar()
aws_mar_tool.create_device(certificate_file=device_cert_file,
                           policy_name=my_policy,
                           thing_type=None)
```

### Register signer with AWS for custom provisioning
The `register_signer` module enables registering a signer in the AWS cloud.

```python
from pyawsutils.register_signer import register_signer

# Register signer with AWS. For custom provisioning only.
register_signer(signer_ca_key_path=signer_ca_key_file,
                signer_ca_cert_path=signer_ca_cert_file,
                signer_ca_ver_cert_path=signer_ca_ver_cert_file,
                aws_profile="default")
```

### Setup an AWS Just-in-Time Registration(JITR) account
The `aws_cloudformation` module contains functions using AWS Cloudformation to setup a JITR account. Example setting up a lambda function with JITR code.

```python
from pyawsutils.aws_cloudformation import setup_aws_jitr_account
# Setup AWS account for JITR, using Cloudformation and uploading Lambda pack with JITR code
setup_aws_jitr_account(force=force_setup)
```

### Cleaner utility
The `clean` module contains functions to delete certificates, things and policies from your account.

```python
from pyawsutils.clean import AccountCleaner
clean_tool = AccountCleaner(profile_name)
clean_tool.cleanup()
```

## Versioning
pyawsutils version can be determined by:
```python
from pyawsutils import __version__ as pyawsutils_version
print(f"pyawsutils version {pyawsutils_version}")
```