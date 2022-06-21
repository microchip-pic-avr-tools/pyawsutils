"""
pyawsutils - Python AWS utilities
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

pyawsutils is a collection of utilities for interacting with Amazon Web Services.
It can be used as a library by instantiating any of the contained classes.

Supported kits are:
    * AVR-IOT (all variants)
    * PIC-IOT (all variants)

Overview
~~~~~~~~

pyawsutils is available:
    * install using pip from pypi: https://pypi.org/project/pyawsutils
    * browse source code on github: https://github.com/microchip-pic-avr-tools/pyawsutils
    * read API documentation on github: https://microchip-pic-avr-tools.github.io/pyawsutils
    * read the changelog on github: https://github.com/microchip-pic-avr-tools/pyawsutils/blob/main/CHANGELOG.md

Usage example 1: Multi-Account Registration (MAR)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. code-block:: python

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

Usage example 2: Register Signer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. code-block:: python

    from pyawsutils.register_signer import register_signer

    # Register signer with AWS. For custom provisioning only.
    register_signer(signer_ca_key_path=signer_ca_key_file,
                    signer_ca_cert_path=signer_ca_cert_file,
                    signer_ca_ver_cert_path=signer_ca_ver_cert_file,
                    aws_profile="default")

Usage example 3: Just-in-Time Registration (JITR)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. code-block:: python

    from pyawsutils.aws_cloudformation import setup_aws_jitr_account
    # Setup AWS account for JITR, using Cloudformation and uploading Lambda pack with JITR code
    setup_aws_jitr_account(force=force_setup)

Usage example 4: Clean account
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. code-block:: python

    from pyawsutils.clean import AccountCleaner
    clean_tool = AccountCleaner(profile_name)
    clean_tool.cleanup()


Logging
~~~~~~~
This package uses the Python logging module for publishing log messages to library users.
A basic configuration can be used (see example), but for best results a more thorough configuration is
recommended in order to control the verbosity of output from dependencies in the stack which also use logging.

.. code-block:: python

    import logging
    logging.getLogger(__name__).addHandler(logging.NullHandler())
"""
