"""
Get the Amazon root CA certificate (bundle)
The file "aws_ca_bundle" is the bundle of CA certs recommended by Amazon
for TLS server authentication. The individual certificates are also
available as separate files.
"""
import os

def aws_get_root_ca_cert_filename(name="aws_ca_bundle"):
    """
    Get root CA certificate (bundle) filename
    :param name: Name of certificate (bundle). The default is the Amazon recommended bundle.
    :returns: Certificate file absolute pathname
    """
    installdir = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(installdir, "ca_certs", f"{name}.pem")


def aws_get_root_ca_cert(name="aws_ca_bundle"):
    """
    Get the AWS root CA certificate (bundle)
    :param name: Name of certificate (bundle) The default is the Amazon recommended bundle.
    :returns: Certificate as a string in PEM format
    """
    with open(aws_get_root_ca_cert_filename(name), "r") as cert:
        return cert.read()
