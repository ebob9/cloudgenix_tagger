from setuptools import setup

with open('README.md') as f:
    long_description = f.read()

setup(name='cloudgenix_tagger',
      version='1.0.0',
      description='Utility to manage tags across a large number of CloudGenix sites, elements, interfaces, '
                  'and Circuit Catagories.',
      long_description=long_description,
      long_description_content_type='text/markdown',
      url='https://github.com/ebob9/cloudgenix_tagger',
      author='Aaron Edwards',
      author_email='cloudgenix_tagger@ebob9.com',
      license='MIT',
      install_requires=[
            'cloudgenix >= 5.1.1b1, < 5.2.1b1',
            'progressbar2 >= 3.34.3',
            'tabulate >= 0.8.3'
      ],
      packages=['cloudgenix_tagger'],
      entry_points={
            'console_scripts': [
                  'do_tags = cloudgenix_tagger:go'
                  ]
      },
      classifiers=[
            "Development Status :: 4 - Beta",
            "Intended Audience :: Developers",
            "License :: OSI Approved :: MIT License",
            "Programming Language :: Python :: 2.7",
            "Programming Language :: Python :: 3",
      ]
      )
