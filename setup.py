import os
import setuptools


def parse_requirements(filename):
    """ load requirements from a pip requirements file """
    lineiter = (line.strip() for line in open(filename))
    return [line for line in lineiter if line and not line.startswith("#")]


with open("README.md", "r") as fh:
    long_description = fh.read()

requirements = parse_requirements(
    os.path.join(os.path.dirname(__file__), 'requirements.txt')
)

setuptools.setup(
    name='thunder-board-terry-geng',
    version='0.3',
    url='https://github.com/TerryGeng/ThunderBoard',
    license='MIT License',
    author='Terry Geng',
    author_email='terry@terriex.com',
    description='Web-based real-time data display platform designed for experiment monitoring.',
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=setuptools.find_packages(),
    python_requires='>=3.6',
    install_requires=requirements,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    entry_points={
        'console_scripts': [
            'thunderboard=thunder_board.app:serve'
        ]
    },
    include_package_data=True,
)
