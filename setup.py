from setuptools import setup

setup(name='Soar',
      version='1.0.0.dev0',
      description='Snakes on a robot: A Python robotics framework',
      long_description='An extensible Python framework for simulating and interacting with robots',
      author='Andrew Antonitis',
      author_email='andrewan@mit.edu',
      packages=['soar', 'soar.client', 'soar.gui', 'soar.robot', 'soar.sim', 'soar.worlds'],
      package_data={'': ['*.gif']},
      entry_points={'console_scripts': ['soar = soar.__main__:main',]},
      install_requires=['pyserial>=3.0'],
      )
