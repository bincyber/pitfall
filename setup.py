from pathlib import Path
from setuptools import setup
import toml


version = Path('VERSION').read_text()
readme  = Path('README.md').read_text()

pipfile = toml.loads(Path('Pipfile').read_text())

requirements = []

for k, v in pipfile["packages"].items():
    package = k
    if v.startswith('==') or v.startswith('>='):
        package = f"{k}{v}"
    requirements.append(package)


setup(name='pitfall',
    version=version,
    description='An integration testing framework for Pulumi Infrastructure as Code',
    long_description=readme,
    long_description_content_type="text/markdown",
    url='http://github.com/bincyber/pitfall',
    author='@bincyber',
    license='Apache',
    keywords="infrastructure-as-code testing devops pulumi",
    packages=['pitfall'],
    python_requires='>=3.7',
    platforms=['any'],
    install_requires=requirements,
    zip_safe=False,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Natural Language :: English',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: MacOS',
        'Operating System :: POSIX',
        'Operating System :: Unix',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: Implementation :: CPython',
        'Topic :: Software Development :: Testing',
        'Topic :: Software Development :: Quality Assurance',
        'Topic :: System :: Systems Administration'
    ],
    test_suite='nose2.collector.collector',
    tests_require=['nose2']
)
