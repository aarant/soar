from setuptools import setup

with open('README.rst', 'r') as f:
    long_description = f.read()

setup(name='Soar',
      version='1.2.2',
      description='An extensible Python framework for simulating and interacting with robots',
      long_description=long_description,
      author='Andrew Antonitis',
      author_email='andrewan@mit.edu',
      url='https://github.com/arantonitis/soar',
      packages=['soar', 'soar.brains', 'soar.gui', 'soar.robot', 'soar.sim', 'soar.worlds'],
      package_data={'': ['*.gif']},
      entry_points={'console_scripts': ['soar = soar.__main__:main',]},
      install_requires=['pyserial>=3.0', 'matplotlib>=2.0'],
      python_requires='>=3',
      license='LGPLv3',
      classifiers=[
          'License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)',
          ]
      )
