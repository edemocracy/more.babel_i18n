# see setup.cfg for metadata and options
from setuptools import setup, find_namespace_packages

setup(
    package_dir={'': 'src'},
    packages=find_namespace_packages(where='src'),
    python_requires="~=3.7",
    include_package_data=True,
    install_requires = [
        "Babel >= 1.0",
        "morepath >= 0.18",
        "Jinja2 >= 2.10",
    ]
)
