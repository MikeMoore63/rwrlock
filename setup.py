import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
     name='rwrlock',
     version='0.0.4',
     scripts=[] ,
     author="Mike Moore",
     author_email="z_z_zebra@yahoo.com",
     description="A limited re-entrant readwrite lock",
     long_description_content_type='text/markdown',
     long_description=long_description,
     url="https://github.com/Mikemoore63/rwrlock",
     packages=setuptools.find_packages(),
     test_suite='nose.collector',
     use_2to3=True,
     tests_require=['nose'],
     include_package_data=True,
     install_requires=[

      ],
     classifiers=[
         "Programming Language :: Python :: 2",
         "License :: OSI Approved :: MIT License",
         "Operating System :: OS Independent",
     ],

 )
