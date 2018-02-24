# Copyright (c) 2017 David Preece, All rights reserved.
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.


from setuptools import setup

setup(name='awsornot',
      version='1.1.0',
      author='David Preece',
      author_email='davep@20ft.nz',
      url='https://20ft.nz',
      license='BSD',
      packages=['awsornot'],
      install_requires=['requests', 'boto3'],
      description='Classes for logging and key/value that work identically whether running on AWS or not',
      long_description="Classes for logging and client/server key value storage that do the same thing " +
                       "regardless of whether or not the code is running on AWS. The logger creates CloudWatch " +
                       "logs asynchronously or logs to stdout; and the KV store replicates put_parameter and " +
                       "get_parameter from the SSM API.",
      keywords='AWS EC2 logging log logger CloudWatch SSM KV Key/Value',
      classifiers=[
            'Development Status :: 5 - Production/Stable',
            'Intended Audience :: Developers',
            'Intended Audience :: Information Technology',
            'Intended Audience :: System Administrators',
            'License :: OSI Approved :: BSD License',
            'Topic :: System :: Boot',
            'Topic :: System :: Boot :: Init',
            'Topic :: System :: Clustering',
            'Topic :: System :: Distributed Computing',
            'Topic :: System :: Software Distribution',
            'Topic :: System :: Systems Administration',
            'Topic :: Utilities',
            'Programming Language :: Python :: 3.4',
            'Programming Language :: Python :: 3.5',
            'Programming Language :: Python :: 3.6'
      ]
      )
