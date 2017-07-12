from setuptools import setup

setup(name='Soar',
      version='0.9.0',
      description='Snakes on a Robot: Python robotics framework',
      long_description='An extensible Python framework for simulating and interacting with robots',
      author='Andrew Antonitis',
      author_email='andrewan@mit.edu',
      packages=['soar', 'soar.brains', 'soar.gui', 'soar.robot', 'soar.sim', 'soar.worlds'],
      package_data={'': ['*.gif']},
      entry_points={'console_scripts': ['soar = soar.client:main',]},
      install_requires=['numpy',],
      )
