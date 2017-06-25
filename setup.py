from setuptools import setup

setup(name='SoaR',
      version='0.7.0',
      description='Snakes on a Robot: Python robotics framework',
      long_description='An extensible Python framework for simulating and interacting with robots',
      author='Andrew Antonitis',
      author_email='andrewan@mit.edu',
      packages=['soar', 'soar.brain', 'soar.gui', 'soar.main', 'soar.robot', 'soar.sim', 'soar.world'],
      package_data={'': ['*.gif']},
      entry_points={'console_scripts': ['SoaR = soar.main.client:main',]}
      )
