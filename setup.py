from setuptools import setup, find_packages

setup(
    name = "twisteddicom",
    version = "0.0.1",
    packages = find_packages(),
    test_suite = "twisteddicom.test",
    author = "Bo Eric Rickard Holmberg",
    author_email = "rickard@holmberg.info",
    description = "A pure python twisted protocol for building DICOM network clients and servers",
    license = "MIT license",
    classifiers = ["License :: OSI Approved :: MIT License",
                   "Intended Audience :: Developers",
                   "Intended Audience :: Healthcare Industry",
                   "Intended Audience :: Science/Research",
                   "Programming Language :: Python",
                   "Programming Language :: Python :: 2.7",
                   "Operating System :: OS Independent",
                   "Topic :: Scientific/Engineering :: Medical Science Apps.",
                   "Topic :: System :: Networking",
                   "Topic :: Software Development :: Libraries",
                   "Development Status :: 3 - Alpha"],
    keywords = "DICOM networking DIMSE twisted python",
    long_description = """
    twisteddicom is a pure python package for building DICOM compliant
    network clients and servers.  It is based on the Twisted network
    engine and the pydicom DICOM parsing library. For general help on
    using the network engine framework, please see the `Twisted
    network engine <http://twistedmatrix.com/trac/>` and for help on
    using pydicom, please see the `Pydicom User Guide
    <http://code.google.com/p/pydicom/wiki/PydicomUserGuide>`.
    """
)
