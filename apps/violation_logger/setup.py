from setuptools import setup

setup(
    name="violation_logger",
    version="0.1.0",
    packages=["violation_logger"],
    install_requires=["setuptools"],
    entry_points={
        "console_scripts": [
            "violation_logger = violation_logger.node:main",
        ],
    },
)
